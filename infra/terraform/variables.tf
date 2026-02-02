variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
}

variable "database_name" {
  description = "Database name"
  type        = string
  default     = "ai_news"
}

variable "database_user" {
  description = "Database user"
  type        = string
  default     = "ai_news_user"
}

variable "database_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "django_secret_key" {
  description = "Django secret key"
  type        = string
  sensitive   = true
}

variable "encryption_key" {
  description = "Encryption key for OAuth tokens"
  type        = string
  sensitive   = true
}

variable "google_oauth_client_id" {
  description = "Google OAuth client ID"
  type        = string
}

variable "google_oauth_secret" {
  description = "Google OAuth client secret"
  type        = string
  sensitive   = true
}

variable "google_api_key" {
  description = "Google API key for Gemini AI"
  type        = string
  sensitive   = true
  default     = ""
}

variable "nextauth_secret" {
  description = "NextAuth secret for session encryption"
  type        = string
  sensitive   = true
  default     = ""
}

variable "backend_image" {
  description = "Backend Docker image"
  type        = string
}

variable "worker_image" {
  description = "Worker Docker image"
  type        = string
}

variable "frontend_image" {
  description = "Frontend Docker image"
  type        = string
}

variable "backend_domain" {
  description = "Backend domain name"
  type        = string
}

variable "frontend_domain" {
  description = "Frontend domain name"
  type        = string
}

variable "cloud_sql_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}
