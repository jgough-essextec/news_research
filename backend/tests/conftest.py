"""
Pytest fixtures for testing.
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    """Set up test database with pgvector extension."""
    from django.conf import settings
    from django.test.utils import setup_test_environment, teardown_test_environment

    with django_db_blocker.unblock():
        # Create pgvector extension
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # Run migrations
        from django.core.management import call_command
        call_command('migrate', '--run-syncdb', verbosity=0)


@pytest.fixture
def api_client():
    """Return an API client instance."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create and return a test user."""
    return User.objects.create_user(
        email='testuser@example.com',
        password='testpass123',
        name='Test User'
    )


@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    return User.objects.create_superuser(
        email='admin@example.com',
        password='adminpass123',
        name='Admin User'
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an admin authenticated API client."""
    api_client.force_authenticate(user=admin_user)
    return api_client
