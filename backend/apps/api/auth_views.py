"""
Authentication views for Google OAuth2.
"""
import logging

from django.conf import settings
from django.contrib.auth import login, logout
from django.shortcuts import redirect
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import User

from .serializers import UserSerializer

logger = logging.getLogger(__name__)


class CurrentUserView(APIView):
    """Get the currently authenticated user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class LogoutView(APIView):
    """Log out the current user."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'status': 'logged out'})


class GoogleAuthStartView(APIView):
    """Start Google OAuth2 flow for user authentication."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from google_auth_oauthlib.flow import Flow

        # Build the OAuth2 flow
        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
                    'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                }
            },
            scopes=[
                'openid',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
            ]
        )

        callback_url = request.build_absolute_uri('/api/auth/google/callback/')
        flow.redirect_uri = callback_url

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        # Store state in session
        request.session['oauth_state'] = state

        return redirect(authorization_url)


class GoogleAuthCallbackView(APIView):
    """Handle Google OAuth2 callback."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        import os
        from google_auth_oauthlib.flow import Flow
        from googleapiclient.discovery import build

        # Allow scope changes (Google may return additional granted scopes)
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

        state = request.session.get('oauth_state')
        if not state:
            return Response(
                {'error': 'Invalid state'},
                status=status.HTTP_400_BAD_REQUEST
            )

        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
                    'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                }
            },
            scopes=[
                'openid',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
            ],
            state=state
        )

        callback_url = request.build_absolute_uri('/api/auth/google/callback/')
        flow.redirect_uri = callback_url

        # Exchange authorization code for tokens
        authorization_response = request.build_absolute_uri()
        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials

        # Get user info
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()

        # Create or update user - first try by email, then by google_id
        try:
            user = User.objects.get(email=user_info['email'])
            # Update existing user with google_id if not set
            if not user.google_id:
                user.google_id = user_info['id']
            user.name = user_info.get('name', '') or user.name
            user.avatar_url = user_info.get('picture', '') or user.avatar_url
            user.save()
            created = False
        except User.DoesNotExist:
            # Try by google_id
            user, created = User.objects.update_or_create(
                google_id=user_info['id'],
                defaults={
                    'email': user_info['email'],
                    'name': user_info.get('name', ''),
                    'avatar_url': user_info.get('picture', ''),
                }
            )

        # Log the user in
        login(request, user)

        # Redirect to frontend
        frontend_url = settings.FRONTEND_URL or 'http://localhost:3000'
        return redirect(f'{frontend_url}/dashboard')


class GmailAuthStartView(APIView):
    """Start Gmail OAuth2 flow for email access."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
                    'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                }
            },
            scopes=settings.GMAIL_SCOPES
        )

        callback_url = request.build_absolute_uri('/api/auth/gmail/callback/')
        flow.redirect_uri = callback_url

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        request.session['gmail_oauth_state'] = state

        return redirect(authorization_url)


class GmailAuthCallbackView(APIView):
    """Handle Gmail OAuth2 callback."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        import os
        from google_auth_oauthlib.flow import Flow

        # Allow scope changes (Google may return additional granted scopes)
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

        state = request.session.get('gmail_oauth_state')
        if not state:
            return Response(
                {'error': 'Invalid state'},
                status=status.HTTP_400_BAD_REQUEST
            )

        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
                    'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                }
            },
            scopes=settings.GMAIL_SCOPES,
            state=state
        )

        callback_url = request.build_absolute_uri('/api/auth/gmail/callback/')
        flow.redirect_uri = callback_url

        authorization_response = request.build_absolute_uri()
        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials

        # Store the refresh token
        user = request.user
        user.gmail_refresh_token = credentials.refresh_token
        user.gmail_connected = True
        user.save()

        logger.info(f'Gmail connected for user {user.email}')

        # Redirect to frontend
        frontend_url = settings.FRONTEND_URL or 'http://localhost:3000'
        return redirect(f'{frontend_url}/settings?gmail=connected')
