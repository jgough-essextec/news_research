"""
Custom authentication classes for the API.
"""
from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Session authentication that doesn't enforce CSRF.
    Use only for development purposes.
    """

    def enforce_csrf(self, request):
        return  # Skip CSRF check
