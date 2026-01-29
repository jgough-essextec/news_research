output "backend_url" {
  description = "Backend Cloud Run URL"
  value       = module.backend.service_url
}

output "frontend_url" {
  description = "Frontend Cloud Run URL"
  value       = module.frontend.service_url
}

output "database_connection_name" {
  description = "Cloud SQL connection name"
  value       = module.cloud_sql.connection_name
}

output "redis_host" {
  description = "Redis host"
  value       = module.redis.host
}
