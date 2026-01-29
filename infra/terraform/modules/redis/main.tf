resource "google_redis_instance" "main" {
  name               = var.name
  tier               = var.tier
  memory_size_gb     = var.memory_size_gb
  region             = var.region
  authorized_network = var.authorized_network

  transit_encryption_mode = var.transit_encryption_mode

  redis_version = "REDIS_7_0"

  display_name = "AI News Redis"

  labels = {
    environment = var.environment
  }
}
