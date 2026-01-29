variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "service_name" {
  type = string
}

variable "image" {
  type = string
}

variable "vpc_connector" {
  type    = string
  default = ""
}

variable "cloud_sql_connection" {
  type    = string
  default = ""
}

variable "service_account_email" {
  type = string
}

variable "min_instances" {
  type    = number
  default = 0
}

variable "max_instances" {
  type    = number
  default = 10
}

variable "memory" {
  type    = string
  default = "512Mi"
}

variable "cpu" {
  type    = string
  default = "1"
}

variable "env_vars" {
  type    = map(string)
  default = {}
}

variable "secrets" {
  type    = map(string)
  default = {}
}

variable "is_job" {
  type    = bool
  default = false
}

variable "allow_unauthenticated" {
  type    = bool
  default = true
}
