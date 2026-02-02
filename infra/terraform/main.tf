terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "prj-cts-lab-vertex-sandbox-tfstate"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sql-component.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "compute.googleapis.com",
    "vpcaccess.googleapis.com",
    "gmail.googleapis.com",
    "iamcredentials.googleapis.com",
    "artifactregistry.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

# Local values for handling optional custom domains
locals {
  # Use Cloud Run default URL if no custom domain is provided
  backend_url = var.backend_domain != "" ? "https://${var.backend_domain}" : module.backend.service_url
  frontend_url = var.frontend_domain != "" ? "https://${var.frontend_domain}" : module.frontend.service_url

  # For ALLOWED_HOSTS, allow both custom domain and Cloud Run URL
  backend_allowed_hosts = var.backend_domain != "" ? var.backend_domain : "*"
}

# VPC for Cloud Run -> Cloud SQL connectivity
module "vpc" {
  source     = "./modules/vpc"
  project_id = var.project_id
  region     = var.region
}

# Cloud SQL with pgvector
module "cloud_sql" {
  source                 = "./modules/cloud-sql"
  project_id             = var.project_id
  region                 = var.region
  database_name          = var.database_name
  database_user          = var.database_user
  database_password      = var.database_password
  vpc_network_id         = module.vpc.network_id
  tier                   = var.cloud_sql_tier
  availability_type      = var.environment == "production" ? "REGIONAL" : "ZONAL"
  backup_enabled         = var.environment == "production"

  # Must wait for VPC private services connection before creating Cloud SQL
  depends_on = [google_project_service.apis, module.vpc]
}

# Secrets Manager
# Note: The secrets module handles core secrets (Django, encryption, OAuth).
# Additional secrets (NextAuth, Google API key) are created directly below.
module "secrets" {
  source                   = "./modules/secrets"
  project_id               = var.project_id
  django_secret_key        = var.django_secret_key
  encryption_key           = var.encryption_key
  google_oauth_client_id   = var.google_oauth_client_id
  google_oauth_secret      = var.google_oauth_secret
  database_url             = module.cloud_sql.database_url

  depends_on = [google_project_service.apis]
}

# Reference existing secrets (created by deploy script or manually)
# Using hardcoded secret IDs since secrets already exist in Secret Manager
locals {
  google_api_key_secret_id = "google-api-key"
  nextauth_secret_id       = "nextauth-secret"
}

# Cloud Run services
module "backend" {
  source                     = "./modules/cloud-run"
  project_id                 = var.project_id
  region                     = var.region
  service_name               = "ai-news-backend"
  image                      = var.backend_image
  vpc_connector              = module.vpc.connector_id
  cloud_sql_connection       = module.cloud_sql.connection_name
  service_account_email      = google_service_account.backend.email
  min_instances              = var.environment == "production" ? 1 : 0
  max_instances              = var.environment == "production" ? 10 : 2
  memory                     = "1Gi"
  cpu                        = "1"

  env_vars = {
    DJANGO_SETTINGS_MODULE    = "config.settings.production"
    GOOGLE_CLOUD_PROJECT      = var.project_id
    VERTEX_AI_LOCATION        = var.region
    USE_SECRET_MANAGER        = "true"
    USE_CLOUD_SQL_AUTH_PROXY  = "true"
    CLOUD_SQL_CONNECTION_NAME = module.cloud_sql.connection_name
    REDIS_URL                 = "rediss://${module.redis.host}:${module.redis.port}/0"
    ALLOWED_HOSTS             = local.backend_allowed_hosts
    # CORS and Frontend URL will be updated after deployment when we know the Cloud Run URLs
    # For initial deployment, allow all origins temporarily
    CORS_ALLOWED_ORIGINS      = var.frontend_domain != "" ? "https://${var.frontend_domain}" : "*"
    FRONTEND_URL              = var.frontend_domain != "" ? "https://${var.frontend_domain}" : ""
  }

  secrets = {
    DJANGO_SECRET_KEY          = module.secrets.django_secret_key_id
    ENCRYPTION_KEY             = module.secrets.encryption_key_id
    GOOGLE_OAUTH_CLIENT_ID     = module.secrets.google_oauth_client_id_id
    GOOGLE_OAUTH_CLIENT_SECRET = module.secrets.google_oauth_secret_id
    GOOGLE_API_KEY             = local.google_api_key_secret_id
    DATABASE_URL               = "database-url"
  }

  depends_on = [google_project_service.apis, module.secrets]
}

module "worker" {
  source                     = "./modules/cloud-run"
  project_id                 = var.project_id
  region                     = var.region
  service_name               = "ai-news-worker"
  image                      = var.worker_image
  vpc_connector              = module.vpc.connector_id
  cloud_sql_connection       = module.cloud_sql.connection_name
  service_account_email      = google_service_account.backend.email
  min_instances              = var.environment == "production" ? 1 : 0
  max_instances              = var.environment == "production" ? 5 : 1
  memory                     = "2Gi"
  cpu                        = "2"
  is_job                     = true

  env_vars = {
    DJANGO_SETTINGS_MODULE    = "config.settings.production"
    GOOGLE_CLOUD_PROJECT      = var.project_id
    VERTEX_AI_LOCATION        = var.region
    USE_SECRET_MANAGER        = "true"
    USE_CLOUD_SQL_AUTH_PROXY  = "true"
    CLOUD_SQL_CONNECTION_NAME = module.cloud_sql.connection_name
    REDIS_URL                 = "rediss://${module.redis.host}:${module.redis.port}/0"
  }

  secrets = {
    DJANGO_SECRET_KEY          = module.secrets.django_secret_key_id
    ENCRYPTION_KEY             = module.secrets.encryption_key_id
    GOOGLE_OAUTH_CLIENT_ID     = module.secrets.google_oauth_client_id_id
    GOOGLE_OAUTH_CLIENT_SECRET = module.secrets.google_oauth_secret_id
    GOOGLE_API_KEY             = local.google_api_key_secret_id
    DATABASE_URL               = "database-url"
  }

  depends_on = [google_project_service.apis, module.secrets]
}

# Migration Job - runs database migrations
module "migrate" {
  source                     = "./modules/cloud-run"
  project_id                 = var.project_id
  region                     = var.region
  service_name               = "ai-news-migrate"
  image                      = var.backend_image
  vpc_connector              = module.vpc.connector_id
  cloud_sql_connection       = module.cloud_sql.connection_name
  service_account_email      = google_service_account.backend.email
  memory                     = "512Mi"
  cpu                        = "1"
  is_job                     = true

  # Run Django migrations
  command = ["python"]
  args    = ["manage.py", "migrate", "--noinput"]

  env_vars = {
    DJANGO_SETTINGS_MODULE    = "config.settings.production"
    GOOGLE_CLOUD_PROJECT      = var.project_id
    USE_SECRET_MANAGER        = "true"
    USE_CLOUD_SQL_AUTH_PROXY  = "true"
    CLOUD_SQL_CONNECTION_NAME = module.cloud_sql.connection_name
  }

  secrets = {
    DJANGO_SECRET_KEY = module.secrets.django_secret_key_id
    DATABASE_URL      = "database-url"
  }

  depends_on = [google_project_service.apis, module.secrets]
}

module "frontend" {
  source                = "./modules/cloud-run"
  project_id            = var.project_id
  region                = var.region
  service_name          = "ai-news-frontend"
  image                 = var.frontend_image
  service_account_email = google_service_account.frontend.email
  min_instances         = var.environment == "production" ? 1 : 0
  max_instances         = var.environment == "production" ? 10 : 2
  memory                = "512Mi"
  cpu                   = "1"

  env_vars = {
    # These will be set during Cloud Build with actual URLs
    # Or updated after initial deployment
    NEXT_PUBLIC_API_URL = var.backend_domain != "" ? "https://${var.backend_domain}/api" : ""
    BACKEND_URL         = var.backend_domain != "" ? "https://${var.backend_domain}" : ""
    NEXTAUTH_URL        = var.frontend_domain != "" ? "https://${var.frontend_domain}" : ""
  }

  secrets = {
    NEXTAUTH_SECRET      = local.nextauth_secret_id
    GOOGLE_CLIENT_ID     = module.secrets.google_oauth_client_id_id
    GOOGLE_CLIENT_SECRET = module.secrets.google_oauth_secret_id
  }

  depends_on = [google_project_service.apis, module.secrets]
}

# Redis (Memorystore)
module "redis" {
  source                  = "./modules/redis"
  project_id              = var.project_id
  region                  = var.region
  name                    = "ai-news-redis"
  memory_size_gb          = var.environment == "production" ? 2 : 1
  authorized_network      = module.vpc.network_id
  transit_encryption_mode = "SERVER_AUTHENTICATION"

  depends_on = [google_project_service.apis]
}

# Service Accounts
resource "google_service_account" "backend" {
  account_id   = "ai-news-backend-sa"
  display_name = "AI News Backend Service Account"
}

resource "google_service_account" "frontend" {
  account_id   = "ai-news-frontend-sa"
  display_name = "AI News Frontend Service Account"
}

resource "google_service_account" "scheduler" {
  account_id   = "ai-news-scheduler-sa"
  display_name = "AI News Scheduler Service Account"
}

# IAM for backend service account
resource "google_project_iam_member" "backend_roles" {
  for_each = toset([
    "roles/aiplatform.user",
    "roles/secretmanager.secretAccessor",
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# IAM for frontend service account
resource "google_project_iam_member" "frontend_roles" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.frontend.email}"
}

# Cloud Scheduler for periodic tasks

# Email sync job - runs every 4 hours
resource "google_cloud_scheduler_job" "email_sync" {
  name        = "ai-news-email-sync"
  description = "Trigger periodic email sync"
  schedule    = "0 */4 * * *"  # Every 4 hours
  time_zone   = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${module.backend.service_url}/api/emails/sync/"

    oidc_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  depends_on = [google_project_service.apis, module.backend]
}

# Scrape pending articles job - runs every 5 minutes
resource "google_cloud_scheduler_job" "scrape_pending" {
  name        = "ai-news-scrape-pending"
  description = "Process pending articles for scraping"
  schedule    = "*/5 * * * *"  # Every 5 minutes
  time_zone   = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${module.backend.service_url}/api/articles/process_pending/"

    oidc_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  depends_on = [google_project_service.apis, module.backend]
}

# Generate missing embeddings job - runs every 10 minutes
resource "google_cloud_scheduler_job" "generate_embeddings" {
  name        = "ai-news-generate-embeddings"
  description = "Generate missing article embeddings"
  schedule    = "*/10 * * * *"  # Every 10 minutes
  time_zone   = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${module.backend.service_url}/api/articles/generate_missing_embeddings/"

    oidc_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  depends_on = [google_project_service.apis, module.backend]
}

# Allow scheduler to invoke backend
resource "google_cloud_run_service_iam_member" "scheduler_invoker" {
  location = var.region
  service  = module.backend.service_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}
