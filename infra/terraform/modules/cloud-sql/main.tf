resource "google_sql_database_instance" "main" {
  name             = "ai-news-db-${random_id.db_suffix.hex}"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = var.tier
    availability_type = var.availability_type

    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.vpc_network_id
    }

    backup_configuration {
      enabled            = var.backup_enabled
      start_time         = "03:00"
      binary_log_enabled = false

      backup_retention_settings {
        retained_backups = 7
      }
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
  }

  deletion_protection = var.deletion_protection
}

resource "random_id" "db_suffix" {
  byte_length = 4
}

resource "google_sql_database" "main" {
  name     = var.database_name
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "main" {
  name     = var.database_user
  instance = google_sql_database_instance.main.name
  password = var.database_password
}

# Enable pgvector extension
resource "null_resource" "enable_pgvector" {
  provisioner "local-exec" {
    command = <<-EOT
      gcloud sql connect ${google_sql_database_instance.main.name} \
        --database=${var.database_name} \
        --user=${var.database_user} \
        --quiet \
        << EOF
CREATE EXTENSION IF NOT EXISTS vector;
EOF
    EOT
  }

  depends_on = [google_sql_database.main, google_sql_user.main]
}
