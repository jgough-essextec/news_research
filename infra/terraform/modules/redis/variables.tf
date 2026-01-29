variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "name" {
  type = string
}

variable "tier" {
  type    = string
  default = "BASIC"
}

variable "memory_size_gb" {
  type    = number
  default = 1
}

variable "authorized_network" {
  type = string
}

variable "transit_encryption_mode" {
  type    = string
  default = "DISABLED"
}

variable "environment" {
  type    = string
  default = "production"
}
