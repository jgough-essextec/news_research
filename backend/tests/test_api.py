"""
API endpoint tests.
"""
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestArticleAPI:
    """Tests for the Article API."""

    def test_list_articles_unauthenticated(self, api_client):
        """Unauthenticated users can access articles (public read-only)."""
        response = api_client.get('/api/articles/')
        # Articles endpoint is publicly accessible for read-only
        assert response.status_code == status.HTTP_200_OK

    def test_list_articles_authenticated(self, authenticated_client):
        """Authenticated users can list articles."""
        response = authenticated_client.get('/api/articles/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data


@pytest.mark.django_db
class TestClusterAPI:
    """Tests for the Cluster API."""

    def test_list_clusters_authenticated(self, authenticated_client):
        """Authenticated users can list clusters."""
        response = authenticated_client.get('/api/clusters/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data


@pytest.mark.django_db
class TestBlogPostAPI:
    """Tests for the BlogPost API."""

    def test_list_posts_authenticated(self, authenticated_client):
        """Authenticated users can list their blog posts."""
        response = authenticated_client.get('/api/posts/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data


@pytest.mark.django_db
class TestAuthAPI:
    """Tests for authentication endpoints."""

    def test_current_user_authenticated(self, authenticated_client, user):
        """Authenticated users can get their profile."""
        response = authenticated_client.get('/api/auth/me/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email

    def test_current_user_unauthenticated(self, api_client):
        """Unauthenticated users cannot get profile."""
        response = api_client.get('/api/auth/me/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
