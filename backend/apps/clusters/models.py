"""
Topic cluster models for grouping related articles.
"""
from django.db import models
from pgvector.django import VectorField

from apps.core.models import TimeStampedModel


class TopicCluster(TimeStampedModel):
    """Represents a cluster of related articles on the same topic."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    # The most representative article for this cluster
    primary_article = models.ForeignKey(
        'articles.Article',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_for_clusters'
    )

    # Centroid embedding for the cluster
    centroid_embedding = VectorField(dimensions=768, null=True, blank=True)

    # Statistics
    article_count = models.IntegerField(default=0)
    priority_score = models.FloatField(default=0.0)

    # AI-generated summary of the topic
    master_summary = models.TextField(blank=True)
    summary_generated_at = models.DateTimeField(null=True, blank=True)

    # Tracking
    is_active = models.BooleanField(default=True)
    last_article_added_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'topic cluster'
        verbose_name_plural = 'topic clusters'
        ordering = ['-priority_score', '-article_count']

    def __str__(self):
        return self.name

    def update_statistics(self):
        """Update cluster statistics based on current articles."""
        self.article_count = self.articles.count()
        # Priority score based on recency and article count
        if self.article_count > 0:
            from django.utils import timezone
            from datetime import timedelta

            recent_count = self.articles.filter(
                publication_date__gte=timezone.now() - timedelta(days=7)
            ).count()
            self.priority_score = (self.article_count * 0.3) + (recent_count * 0.7)
        self.save(update_fields=['article_count', 'priority_score'])


class ClusterMerge(TimeStampedModel):
    """Tracks when clusters are merged together."""

    source_cluster = models.ForeignKey(
        TopicCluster,
        on_delete=models.CASCADE,
        related_name='merged_from'
    )
    target_cluster = models.ForeignKey(
        TopicCluster,
        on_delete=models.CASCADE,
        related_name='merged_into'
    )
    reason = models.TextField(blank=True)
    articles_moved = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'cluster merge'
        verbose_name_plural = 'cluster merges'

    def __str__(self):
        return f"{self.source_cluster} -> {self.target_cluster}"
