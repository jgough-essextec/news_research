"""
Production settings for GCP deployment.
"""
import os

from google.cloud import secretmanager

from .base import *  # noqa: F401, F403

DEBUG = False

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True


def get_secret(secret_id: str) -> str:
    """Retrieve a secret from Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


# Load secrets from Secret Manager
if os.environ.get('USE_SECRET_MANAGER', 'false').lower() == 'true':
    SECRET_KEY = get_secret('django-secret-key')
    ENCRYPTION_KEY = get_secret('encryption-key')

# ALLOWED_HOSTS from environment
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Database - Cloud SQL connection
if os.environ.get('USE_CLOUD_SQL_AUTH_PROXY', 'false').lower() == 'true':
    DATABASES['default']['HOST'] = '/cloudsql/' + os.environ.get('CLOUD_SQL_CONNECTION_NAME', '')  # noqa: F405

# Static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# CORS - restrict to specific origins
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')

# Logging for Cloud Run
LOGGING['handlers']['console']['formatter'] = 'verbose'  # noqa: F405
LOGGING['root']['level'] = 'WARNING'  # noqa: F405
