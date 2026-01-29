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
    # Configure in environments
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
  ])

  service            = each.value
  disable_on_destroy = false
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

  depends_on = [google_project_service.apis]
}

# Secrets Manager
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
    DJANGO_SETTINGS_MODULE = "config.settings.production"
    GOOGLE_CLOUD_PROJECT   = var.project_id
    VERTEX_AI_LOCATION     = var.region
    USE_SECRET_MANAGER     = "true"
    USE_CLOUD_SQL_AUTH_PROXY = "true"
    CLOUD_SQL_CONNECTION_NAME = module.cloud_sql.connection_name
    REDIS_URL              = "redis://${module.redis.host}:${module.redis.port}/0"
    ALLOWED_HOSTS          = var.backend_domain
    CORS_ALLOWED_ORIGINS   = "https://${var.frontend_domain}"
    FRONTEND_URL           = "https://${var.frontend_domain}"
  }

  secrets = {
    DJANGO_SECRET_KEY          = module.secrets.django_secret_key_id
    ENCRYPTION_KEY             = module.secrets.encryption_key_id
    GOOGLE_OAUTH_CLIENT_ID     = module.secrets.google_oauth_client_id_id
    GOOGLE_OAUTH_CLIENT_SECRET = module.secrets.google_oauth_secret_id
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
    DJANGO_SETTINGS_MODULE = "config.settings.production"
    GOOGLE_CLOUD_PROJECT   = var.project_id
    VERTEX_AI_LOCATION     = var.region
    USE_SECRET_MANAGER     = "true"
    USE_CLOUD_SQL_AUTH_PROXY = "true"
    CLOUD_SQL_CONNECTION_NAME = module.cloud_sql.connection_name
    REDIS_URL              = "redis://${module.redis.host}:${module.redis.port}/0"
  }

  secrets = {
    DJANGO_SECRET_KEY          = module.secrets.django_secret_key_id
    ENCRYPTION_KEY             = module.secrets.encryption_key_id
    GOOGLE_OAUTH_CLIENT_ID     = module.secrets.google_oauth_client_id_id
    GOOGLE_OAUTH_CLIENT_SECRET = module.secrets.google_oauth_secret_id
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
    NEXT_PUBLIC_API_URL = "https://${var.backend_domain}/api"
    BACKEND_URL         = "https://${var.backend_domain}"
    NEXTAUTH_URL        = "https://${var.frontend_domain}"
  }

  secrets = {
    NEXTAUTH_SECRET        = module.secrets.nextauth_secret_id
    GOOGLE_CLIENT_ID       = module.secrets.google_oauth_client_id_id
    GOOGLE_CLIENT_SECRET   = module.secrets.google_oauth_secret_id
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

# Cloud Scheduler for periodic tasks
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

  depends_on = [google_project_service.apis]
}

# Allow scheduler to invoke backend
resource "google_cloud_run_service_iam_member" "scheduler_invoker" {
  location = var.region
  service  = module.backend.service_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}
