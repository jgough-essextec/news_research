output "network_id" {
  value = google_compute_network.main.id
}

output "subnet_id" {
  value = google_compute_subnetwork.main.id
}

output "connector_id" {
  value = google_vpc_access_connector.connector.id
}

output "private_vpc_connection" {
  value = google_service_networking_connection.private_vpc.id
}
