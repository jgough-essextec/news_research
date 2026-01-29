output "service_url" {
  value = var.is_job ? "" : google_cloud_run_v2_service.main[0].uri
}

output "service_name" {
  value = var.service_name
}
