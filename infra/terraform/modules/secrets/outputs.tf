output "django_secret_key_id" {
  value = google_secret_manager_secret.django_secret_key.secret_id
}

output "encryption_key_id" {
  value = google_secret_manager_secret.encryption_key.secret_id
}

output "google_oauth_client_id_id" {
  value = google_secret_manager_secret.google_oauth_client_id.secret_id
}

output "google_oauth_secret_id" {
  value = google_secret_manager_secret.google_oauth_secret.secret_id
}

output "database_url_id" {
  value = google_secret_manager_secret.database_url.secret_id
}

output "nextauth_secret_id" {
  value = google_secret_manager_secret.nextauth_secret.secret_id
}
