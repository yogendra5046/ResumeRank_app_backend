output "cloud_run_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.backend.uri
}

output "load_balancer_ip" {
  description = "Global load balancer IP (point your DNS A record here)"
  value       = google_compute_global_address.lb_ip.address
}

output "redis_host" {
  description = "Memorystore Redis host (private VPC)"
  value       = google_redis_instance.cache.host
  sensitive   = true
}
