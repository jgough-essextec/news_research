"""
Authentication URL configuration.
"""
from django.urls import path

from .auth_views import (
    CurrentUserView,
    GmailAuthCallbackView,
    GmailAuthStartView,
    GoogleAuthCallbackView,
    GoogleAuthStartView,
    LogoutView,
)

urlpatterns = [
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('google/', GoogleAuthStartView.as_view(), name='google-auth-start'),
    path('google/callback/', GoogleAuthCallbackView.as_view(), name='google-auth-callback'),
    path('gmail/', GmailAuthStartView.as_view(), name='gmail-auth-start'),
    path('gmail/callback/', GmailAuthCallbackView.as_view(), name='gmail-auth-callback'),
]
