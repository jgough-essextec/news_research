resource "google_sql_database_instance" "main" {
  name             = "ai-news-db-${random_id.db_suffix.hex}"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = var.tier
    availability_type = var.availability_type

    # pgvector extension is enabled after database creation
    # via SQL command: CREATE EXTENSION IF NOT EXISTS vector;

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

# Note: pgvector extension should be enabled via Django migrations
# or manually via Cloud SQL console. The local-exec provisioner
# has been removed due to gcloud PATH and connectivity requirements.
#
# To enable pgvector manually:
# 1. Go to Cloud SQL console
# 2. Connect to the database
# 3. Run: CREATE EXTENSION IF NOT EXISTS vector;
