"""
Local development settings.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Use console email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable CSRF for local API testing
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# More permissive CORS for local dev
CORS_ALLOW_ALL_ORIGINS = True

# REST Framework settings for local development
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Celery in eager mode for easier debugging (optional)
# CELERY_TASK_ALWAYS_EAGER = True
# CELERY_TASK_EAGER_PROPAGATES = True

# Debug toolbar (optional)
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ['debug_toolbar']  # noqa: F405
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa: F405
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass
