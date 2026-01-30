"""
Google AI client factory supporting both API key and Vertex AI authentication.
"""
import logging
from enum import Enum
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class AuthMode(Enum):
    """Authentication mode for Google AI services."""
    API_KEY = 'api_key'
    VERTEX_AI = 'vertex_ai'


def get_auth_mode() -> AuthMode:
    """
    Determine which authentication mode to use.

    Priority:
    1. API key if GOOGLE_API_KEY is set
    2. Vertex AI if GOOGLE_CLOUD_PROJECT is set
    """
    if settings.GOOGLE_API_KEY:
        return AuthMode.API_KEY
    elif settings.GOOGLE_CLOUD_PROJECT:
        return AuthMode.VERTEX_AI
    else:
        raise ValueError(
            'No Google AI credentials configured. '
            'Set either GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT environment variable.'
        )


def get_genai_client():
    """
    Get a Google GenAI client for API key authentication.

    Returns:
        google.genai.Client configured with API key
    """
    from google import genai

    if not settings.GOOGLE_API_KEY:
        raise ValueError('GOOGLE_API_KEY not configured')

    return genai.Client(api_key=settings.GOOGLE_API_KEY)


def init_vertex_ai():
    """
    Initialize Vertex AI for service account authentication.
    """
    from google.cloud import aiplatform

    if not settings.GOOGLE_CLOUD_PROJECT:
        raise ValueError('GOOGLE_CLOUD_PROJECT not configured')

    aiplatform.init(
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.VERTEX_AI_LOCATION,
    )


def use_api_key() -> bool:
    """Check if API key mode should be used."""
    return bool(settings.GOOGLE_API_KEY)


def use_vertex_ai() -> bool:
    """Check if Vertex AI mode should be used."""
    return not settings.GOOGLE_API_KEY and bool(settings.GOOGLE_CLOUD_PROJECT)
