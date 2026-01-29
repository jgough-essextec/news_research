"""
API URL configuration.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ArticleViewSet,
    BlogPostViewSet,
    ClusterViewSet,
    EmailViewSet,
    ExtractedLinkViewSet,
    GenerationJobViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'emails', EmailViewSet, basename='email')
router.register(r'links', ExtractedLinkViewSet, basename='link')
router.register(r'articles', ArticleViewSet, basename='article')
router.register(r'clusters', ClusterViewSet, basename='cluster')
router.register(r'posts', BlogPostViewSet, basename='post')
router.register(r'jobs', GenerationJobViewSet, basename='job')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('apps.api.auth_urls')),
]
