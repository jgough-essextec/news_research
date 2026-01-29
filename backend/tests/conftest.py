"""
Pytest fixtures for testing.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


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
