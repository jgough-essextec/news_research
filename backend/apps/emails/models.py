"""
Email models for the Collector Agent.
"""
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class NewsletterEmail(TimeStampedModel):
    """Represents an email fetched from Gmail."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='newsletter_emails'
    )

    gmail_message_id = models.CharField(max_length=255, db_index=True)
    thread_id = models.CharField(max_length=255, blank=True)
    sender_email = models.EmailField()
    sender_name = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=500)
    received_date = models.DateTimeField(db_index=True)

    raw_html = models.TextField(blank=True)
    snippet = models.TextField(blank=True)

    is_processed = models.BooleanField(default=False, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    link_count = models.IntegerField(default=0)
    ai_summary = models.TextField(blank=True, help_text="AI-generated summary of email contents")

    class Meta:
        verbose_name = 'newsletter email'
        verbose_name_plural = 'newsletter emails'
        ordering = ['-received_date']
        unique_together = ['user', 'gmail_message_id']

    def __str__(self):
        return f"{self.sender_name}: {self.subject}"


class ExtractedLink(TimeStampedModel):
    """Represents a link extracted from a newsletter email."""

    class LinkStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        VALID = 'valid', 'Valid Article'
        INVALID = 'invalid', 'Invalid'
        DUPLICATE = 'duplicate', 'Duplicate'
        ERROR = 'error', 'Error'

    newsletter_email = models.ForeignKey(
        NewsletterEmail,
        on_delete=models.CASCADE,
        related_name='extracted_links'
    )

    raw_url = models.URLField(max_length=2000)
    canonical_url = models.URLField(max_length=2000, db_index=True)
    anchor_text = models.TextField(blank=True)
    surrounding_text = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=LinkStatus.choices,
        default=LinkStatus.PENDING
    )
    is_valid_article = models.BooleanField(default=False)

    # Reference to the article if successfully scraped
    article = models.ForeignKey(
        'articles.Article',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_links'
    )

    class Meta:
        verbose_name = 'extracted link'
        verbose_name_plural = 'extracted links'
        ordering = ['-created_at']

    def __str__(self):
        return self.canonical_url
