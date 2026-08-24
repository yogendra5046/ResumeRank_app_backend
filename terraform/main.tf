terraform {
  required_version = ">= 1.7.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.25"
    }
  }
  backend "gcs" {
    bucket = "resumerank-tfstate"
    prefix = "prod"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── VPC for private Redis ─────────────────────────────────────────────────────
resource "google_compute_network" "vpc" {
  name                    = "resumerank-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "resumerank-subnet"
  ip_cidr_range = "10.10.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
}

# ── Cloud Memorystore (Redis) ─────────────────────────────────────────────────
resource "google_redis_instance" "cache" {
  name           = "resumerank-redis"
  tier           = "STANDARD_HA"
  memory_size_gb = 2
  region         = var.region
  redis_version  = "REDIS_7_0"

  authorized_network = google_compute_network.vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  transit_encryption_mode = "SERVER_AUTHENTICATION"

  labels = {
    env     = "production"
    service = "resumerank"
  }
}

# ── Secret Manager: Redis URL ────────────────────────────────────────────────
resource "google_secret_manager_secret" "redis_url" {
  secret_id = "resumerank-redis-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "redis_url" {
  secret      = google_secret_manager_secret.redis_url.id
  secret_data = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
}

# ── Secret Manager: API Key Salt ─────────────────────────────────────────────
resource "google_secret_manager_secret" "api_key_salt" {
  secret_id = "resumerank-api-key-salt"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "api_key_salt" {
  secret      = google_secret_manager_secret.api_key_salt.id
  secret_data = var.api_key_salt
}

# ── Cloud Run Service ─────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "backend" {
  name     = "resumerank-backend"
  location = var.region

  template {
    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    containers {
      image = var.container_image

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        cpu_idle          = false  # Always-on CPU for <800ms p95
        startup_cpu_boost = true
      }

      ports {
        container_port = 8080
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "CLAMAV_HOST"
        value = var.clamav_host
      }

      env {
        name  = "CLAMAV_PORT"
        value = "3310"
      }

      env {
        name  = "OTLP_ENDPOINT"
        value = var.otlp_endpoint
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.redis_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "API_KEY_SALT"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.api_key_salt.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/ready"
        }
        initial_delay_seconds = 30
        period_seconds        = 10
        failure_threshold     = 6
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        period_seconds    = 30
        failure_threshold = 3
      }
    }

    vpc_access {
      network_interfaces {
        network    = google_compute_network.vpc.id
        subnetwork = google_compute_subnetwork.subnet.id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
}

# ── Cloud Run IAM: public invocation (authenticated via X-API-Key) ───────────
resource "google_cloud_run_v2_service_iam_member" "public" {
  location = google_cloud_run_v2_service.backend.location
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Cloud Load Balancer ───────────────────────────────────────────────────────
resource "google_compute_global_address" "lb_ip" {
  name = "resumerank-lb-ip"
}

resource "google_compute_managed_ssl_certificate" "ssl" {
  name = "resumerank-ssl"
  managed {
    domains = [var.domain]
  }
}

resource "google_compute_region_network_endpoint_group" "cloudrun_neg" {
  name                  = "resumerank-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_v2_service.backend.name
  }
}

resource "google_compute_backend_service" "backend" {
  name                  = "resumerank-backend-service"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTPS"

  backend {
    group = google_compute_region_network_endpoint_group.cloudrun_neg.id
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

resource "google_compute_url_map" "lb" {
  name            = "resumerank-lb"
  default_service = google_compute_backend_service.backend.id
}

resource "google_compute_target_https_proxy" "lb" {
  name             = "resumerank-https-proxy"
  url_map          = google_compute_url_map.lb.id
  ssl_certificates = [google_compute_managed_ssl_certificate.ssl.id]
}

resource "google_compute_global_forwarding_rule" "lb" {
  name                  = "resumerank-forwarding-rule"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.lb.id
  ip_address            = google_compute_global_address.lb_ip.address
}

# HTTP → HTTPS redirect
resource "google_compute_url_map" "http_redirect" {
  name = "resumerank-http-redirect"
  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "redirect" {
  name    = "resumerank-http-proxy"
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_global_forwarding_rule" "http_redirect" {
  name                  = "resumerank-http-redirect"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.redirect.id
  ip_address            = google_compute_global_address.lb_ip.address
}
