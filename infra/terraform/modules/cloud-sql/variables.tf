variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "database_name" {
  type = string
}

variable "database_user" {
  type = string
}

variable "database_password" {
  type      = string
  sensitive = true
}

variable "vpc_network_id" {
  type = string
}

variable "tier" {
  type    = string
  default = "db-f1-micro"
}

variable "availability_type" {
  type    = string
  default = "ZONAL"
}

variable "backup_enabled" {
  type    = bool
  default = false
}

variable "deletion_protection" {
  type    = bool
  default = true
}
