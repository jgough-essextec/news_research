variable "project_id" {
  type = string
}

variable "django_secret_key" {
  type      = string
  sensitive = true
}

variable "encryption_key" {
  type      = string
  sensitive = true
}

variable "google_oauth_client_id" {
  type = string
}

variable "google_oauth_secret" {
  type      = string
  sensitive = true
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "nextauth_secret" {
  type      = string
  sensitive = true
  default   = ""
}
