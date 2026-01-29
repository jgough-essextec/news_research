"""
Article models for the Analyst Agent.
"""
from django.db import models
from pgvector.django import VectorField

from apps.core.models import TimeStampedModel


class Article(TimeStampedModel):
    """Represents a scraped and processed article."""

    class ScrapeStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        SKIPPED = 'skipped', 'Skipped'

    # Core identifiers
    canonical_url = models.URLField(max_length=2000, unique=True, db_index=True)
    url_hash = models.CharField(max_length=64, unique=True, db_index=True)

    # Article metadata
    title = models.CharField(max_length=500, blank=True)
    author = models.CharField(max_length=255, blank=True)
    publication = models.CharField(max_length=255, blank=True)
    publication_date = models.DateTimeField(null=True, blank=True, db_index=True)

    # Content
    content_text = models.TextField(blank=True)
    content_html = models.TextField(blank=True)
    excerpt = models.TextField(blank=True)
    word_count = models.IntegerField(default=0)

    # Embedding for vector similarity
    embedding = VectorField(dimensions=768, null=True, blank=True)
    embedding_model = models.CharField(max_length=100, blank=True)

    # AI-generated summary
    summary = models.TextField(blank=True)

    # Clustering
    topic_cluster = models.ForeignKey(
        'clusters.TopicCluster',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='articles'
    )
    similarity_to_cluster = models.FloatField(null=True, blank=True)

    # Status tracking
    scrape_status = models.CharField(
        max_length=20,
        choices=ScrapeStatus.choices,
        default=ScrapeStatus.PENDING
    )
    scrape_error = models.TextField(blank=True)
    scrape_attempts = models.IntegerField(default=0)
    last_scrape_at = models.DateTimeField(null=True, blank=True)

    # Metadata from scraping
    og_image = models.URLField(max_length=2000, blank=True)
    language = models.CharField(max_length=10, blank=True, default='en')

    class Meta:
        verbose_name = 'article'
        verbose_name_plural = 'articles'
        ordering = ['-publication_date', '-created_at']
        indexes = [
            models.Index(fields=['scrape_status', 'scrape_attempts']),
        ]

    def __str__(self):
        return self.title or self.canonical_url

    def save(self, *args, **kwargs):
        if not self.url_hash:
            import hashlib
            self.url_hash = hashlib.sha256(self.canonical_url.encode()).hexdigest()
        super().save(*args, **kwargs)


class ArticleDuplicate(TimeStampedModel):
    """Tracks duplicate relationships between articles."""

    primary_article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name='duplicate_references'
    )
    duplicate_article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name='duplicated_by'
    )
    similarity_score = models.FloatField()

    class Meta:
        verbose_name = 'article duplicate'
        verbose_name_plural = 'article duplicates'
        unique_together = ['primary_article', 'duplicate_article']

    def __str__(self):
        return f"{self.duplicate_article} -> {self.primary_article} ({self.similarity_score:.3f})"
