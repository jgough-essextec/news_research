output "host" {
  value = google_redis_instance.main.host
}

output "port" {
  value = google_redis_instance.main.port
}

output "current_location_id" {
  value = google_redis_instance.main.current_location_id
}
