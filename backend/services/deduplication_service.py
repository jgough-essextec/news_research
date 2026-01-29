"""
Deduplication and clustering service using pgvector.
"""
import logging
from typing import Optional

import numpy as np
from django.conf import settings
from django.db.models import F
from django.utils import timezone
from django.utils.text import slugify
from pgvector.django import CosineDistance

from apps.articles.models import Article, ArticleDuplicate
from apps.clusters.models import TopicCluster

logger = logging.getLogger(__name__)


class DeduplicationService:
    """Service for deduplicating articles and clustering by topic."""

    def __init__(
        self,
        duplicate_threshold: float = None,
        cluster_threshold: float = None
    ):
        self.duplicate_threshold = duplicate_threshold or settings.DUPLICATE_THRESHOLD
        self.cluster_threshold = cluster_threshold or settings.CLUSTER_THRESHOLD

    def find_duplicates(self, article: Article) -> list[tuple[Article, float]]:
        """
        Find duplicate articles (similarity > duplicate_threshold).
        Returns list of (article, similarity_score) tuples.
        """
        if article.embedding is None:
            return []

        # Find articles with high similarity
        similar = Article.objects.exclude(
            id=article.id
        ).exclude(
            embedding__isnull=True
        ).annotate(
            distance=CosineDistance('embedding', article.embedding)
        ).filter(
            distance__lt=(1 - self.duplicate_threshold)
        ).order_by('distance')[:10]

        results = []
        for sim_article in similar:
            similarity = 1 - sim_article.distance
            results.append((sim_article, similarity))

        return results

    def find_similar_articles(self, article: Article) -> list[tuple[Article, float]]:
        """
        Find similar articles (similarity between cluster_threshold and duplicate_threshold).
        Returns list of (article, similarity_score) tuples.
        """
        if article.embedding is None:
            return []

        # Find articles with medium-high similarity (same topic, not duplicates)
        similar = Article.objects.exclude(
            id=article.id
        ).exclude(
            embedding__isnull=True
        ).annotate(
            distance=CosineDistance('embedding', article.embedding)
        ).filter(
            distance__lt=(1 - self.cluster_threshold),
            distance__gte=(1 - self.duplicate_threshold)
        ).order_by('distance')[:20]

        results = []
        for sim_article in similar:
            similarity = 1 - sim_article.distance
            results.append((sim_article, similarity))

        return results

    def process_article(self, article: Article) -> Optional[TopicCluster]:
        """
        Process a new article for deduplication and clustering.
        Returns the assigned cluster (if any).
        """
        if article.embedding is None:
            logger.warning(f'Article {article.id} has no embedding')
            return None

        # Check for duplicates first
        duplicates = self.find_duplicates(article)
        if duplicates:
            # Mark as duplicate of the oldest article
            primary_article = min(duplicates, key=lambda x: x[0].created_at)[0]

            ArticleDuplicate.objects.get_or_create(
                primary_article=primary_article,
                duplicate_article=article,
                defaults={'similarity_score': duplicates[0][1]}
            )

            # If primary has a cluster, assign this article to it
            if primary_article.topic_cluster:
                article.topic_cluster = primary_article.topic_cluster
                article.similarity_to_cluster = duplicates[0][1]
                article.save(update_fields=['topic_cluster', 'similarity_to_cluster'])
                return primary_article.topic_cluster

        # Find best matching cluster
        best_cluster = self._find_best_cluster(article)

        if best_cluster:
            article.topic_cluster = best_cluster
            article.save(update_fields=['topic_cluster'])
            self._update_cluster_centroid(best_cluster)
            return best_cluster

        # Create new cluster if no good match
        cluster = self._create_cluster(article)
        return cluster

    def _find_best_cluster(self, article: Article) -> Optional[TopicCluster]:
        """Find the best matching cluster for an article."""
        # Find clusters with similar centroid
        clusters = TopicCluster.objects.exclude(
            centroid_embedding__isnull=True
        ).filter(
            is_active=True
        ).annotate(
            distance=CosineDistance('centroid_embedding', article.embedding)
        ).filter(
            distance__lt=(1 - self.cluster_threshold)
        ).order_by('distance')[:1]

        if clusters:
            cluster = clusters[0]
            similarity = 1 - cluster.distance
            article.similarity_to_cluster = similarity
            logger.info(f'Found matching cluster {cluster.name} for article {article.title} (sim: {similarity:.3f})')
            return cluster

        return None

    def _create_cluster(self, article: Article) -> TopicCluster:
        """Create a new cluster for an article."""
        # Generate cluster name from article title
        name = article.title[:100] if article.title else f'Topic {article.id}'
        base_slug = slugify(name)[:200]

        # Ensure unique slug
        slug = base_slug
        counter = 1
        while TopicCluster.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        cluster = TopicCluster.objects.create(
            name=name,
            slug=slug,
            primary_article=article,
            centroid_embedding=article.embedding,
            article_count=1,
            last_article_added_at=timezone.now(),
        )

        article.topic_cluster = cluster
        article.similarity_to_cluster = 1.0
        article.save(update_fields=['topic_cluster', 'similarity_to_cluster'])

        logger.info(f'Created new cluster: {cluster.name}')
        return cluster

    def _update_cluster_centroid(self, cluster: TopicCluster):
        """Update cluster centroid based on all article embeddings."""
        articles = cluster.articles.exclude(embedding__isnull=True)[:100]

        if not articles:
            return

        # Calculate new centroid as mean of all embeddings
        embeddings = [list(a.embedding) for a in articles if a.embedding]
        if embeddings:
            centroid = np.mean(embeddings, axis=0).tolist()
            cluster.centroid_embedding = centroid

        # Update statistics
        cluster.article_count = cluster.articles.count()
        cluster.last_article_added_at = timezone.now()

        # Update primary article (most representative)
        if len(embeddings) >= 3:
            # Find article closest to centroid
            best_article = cluster.articles.exclude(
                embedding__isnull=True
            ).annotate(
                distance=CosineDistance('embedding', centroid)
            ).order_by('distance').first()

            if best_article:
                cluster.primary_article = best_article

        cluster.save()

    def merge_clusters(self, source: TopicCluster, target: TopicCluster, reason: str = ''):
        """Merge source cluster into target cluster."""
        from apps.clusters.models import ClusterMerge

        # Move all articles to target cluster
        articles_moved = source.articles.update(topic_cluster=target)

        # Record the merge
        ClusterMerge.objects.create(
            source_cluster=source,
            target_cluster=target,
            reason=reason,
            articles_moved=articles_moved,
        )

        # Deactivate source cluster
        source.is_active = False
        source.save(update_fields=['is_active'])

        # Update target cluster
        self._update_cluster_centroid(target)

        logger.info(f'Merged cluster {source.name} into {target.name} ({articles_moved} articles)')


def process_new_article(article_id: int) -> bool:
    """Process a newly scraped article for deduplication and clustering."""
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        logger.error(f'Article {article_id} not found')
        return False

    service = DeduplicationService()
    cluster = service.process_article(article)

    if cluster:
        logger.info(f'Article {article.title} assigned to cluster {cluster.name}')
        return True

    logger.warning(f'Article {article.title} could not be clustered')
    return False
