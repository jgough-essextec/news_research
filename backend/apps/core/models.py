"""
Core models including custom User model.
"""
import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    """Custom user manager."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """Custom user model using email as the username."""

    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    google_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    avatar_url = models.URLField(max_length=500, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    # Gmail integration
    gmail_connected = models.BooleanField(default=False)
    _gmail_refresh_token = models.BinaryField(blank=True, null=True, db_column='gmail_refresh_token')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return self.email

    def _get_encryption_key(self) -> bytes:
        """Derive encryption key from settings."""
        key = settings.ENCRYPTION_KEY or 'dev-encryption-key'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'ai-news-aggregator-salt',
            iterations=480000,
        )
        return base64.urlsafe_b64encode(kdf.derive(key.encode()))

    @property
    def gmail_refresh_token(self) -> str | None:
        """Decrypt and return the Gmail refresh token."""
        if not self._gmail_refresh_token:
            return None
        try:
            f = Fernet(self._get_encryption_key())
            return f.decrypt(bytes(self._gmail_refresh_token)).decode()
        except Exception:
            return None

    @gmail_refresh_token.setter
    def gmail_refresh_token(self, value: str | None):
        """Encrypt and store the Gmail refresh token."""
        if value is None:
            self._gmail_refresh_token = None
        else:
            f = Fernet(self._get_encryption_key())
            self._gmail_refresh_token = f.encrypt(value.encode())


class SystemSetting(TimeStampedModel):
    """Key-value store for system-wide settings."""

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'system setting'
        verbose_name_plural = 'system settings'

    def __str__(self):
        return self.key
