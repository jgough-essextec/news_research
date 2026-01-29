resource "google_secret_manager_secret" "django_secret_key" {
  secret_id = "django-secret-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "django_secret_key" {
  secret      = google_secret_manager_secret.django_secret_key.id
  secret_data = var.django_secret_key
}

resource "google_secret_manager_secret" "encryption_key" {
  secret_id = "encryption-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "encryption_key" {
  secret      = google_secret_manager_secret.encryption_key.id
  secret_data = var.encryption_key
}

resource "google_secret_manager_secret" "google_oauth_client_id" {
  secret_id = "google-oauth-client-id"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "google_oauth_client_id" {
  secret      = google_secret_manager_secret.google_oauth_client_id.id
  secret_data = var.google_oauth_client_id
}

resource "google_secret_manager_secret" "google_oauth_secret" {
  secret_id = "google-oauth-secret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "google_oauth_secret" {
  secret      = google_secret_manager_secret.google_oauth_secret.id
  secret_data = var.google_oauth_secret
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "database-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = var.database_url
}

resource "google_secret_manager_secret" "nextauth_secret" {
  secret_id = "nextauth-secret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "nextauth_secret" {
  secret      = google_secret_manager_secret.nextauth_secret.id
  secret_data = var.nextauth_secret != "" ? var.nextauth_secret : var.django_secret_key
}
