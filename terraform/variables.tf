variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "container_image" {
  description = "Full GCR image path (e.g. gcr.io/my-project/resumerank-backend:sha)"
  type        = string
}

variable "domain" {
  description = "Custom domain for the load balancer SSL cert"
  type        = string
}

variable "api_key_salt" {
  description = "Salt for API key hashing (treat as secret)"
  type        = string
  sensitive   = true
}

variable "clamav_host" {
  description = "ClamAV daemon hostname (internal VPC)"
  type        = string
  default     = "clamav.internal"
}

variable "otlp_endpoint" {
  description = "OpenTelemetry OTLP gRPC endpoint (e.g. http://otel-collector:4317)"
  type        = string
  default     = ""
}
