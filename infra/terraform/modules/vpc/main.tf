resource "google_compute_network" "main" {
  name                    = "ai-news-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  name          = "ai-news-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.main.id

  private_ip_google_access = true
}

resource "google_compute_global_address" "private_ip" {
  name          = "ai-news-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main.id
}

resource "google_service_networking_connection" "private_vpc" {
  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip.name]
}

resource "google_vpc_access_connector" "connector" {
  name          = "ai-news-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.main.name

  min_instances = 2
  max_instances = 3
}
