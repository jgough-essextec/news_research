output "connection_name" {
  value = google_sql_database_instance.main.connection_name
}

output "database_url" {
  value     = "postgresql://${var.database_user}:${var.database_password}@/${var.database_name}?host=/cloudsql/${google_sql_database_instance.main.connection_name}"
  sensitive = true
}

output "instance_name" {
  value = google_sql_database_instance.main.name
}
