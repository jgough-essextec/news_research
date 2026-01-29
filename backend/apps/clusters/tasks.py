"""
Celery tasks for cluster management.
"""
import logging

from celery import shared_task

from apps.clusters.models import TopicCluster

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_cluster_summary(self, cluster_id: int):
    """Generate a summary for a topic cluster."""
    from services.generation_service import generate_cluster_summary_task

    try:
        success = generate_cluster_summary_task(cluster_id)
        if success:
            logger.info(f'Generated summary for cluster {cluster_id}')
    except Exception as e:
        logger.error(f'Error generating cluster summary {cluster_id}: {e}')
        self.retry(exc=e)


@shared_task
def update_all_cluster_statistics():
    """Periodic task to update statistics for all active clusters."""
    clusters = TopicCluster.objects.filter(is_active=True)

    for cluster in clusters:
        cluster.update_statistics()

    logger.info(f'Updated statistics for {clusters.count()} clusters')


@shared_task
def generate_summaries_for_new_clusters():
    """Generate summaries for clusters that don't have one yet."""
    clusters = TopicCluster.objects.filter(
        is_active=True,
        master_summary='',
        article_count__gte=3  # Only clusters with enough articles
    ).order_by('-priority_score')[:5]

    for cluster in clusters:
        generate_cluster_summary.delay(cluster.id)

    if clusters:
        logger.info(f'Queued {clusters.count()} clusters for summary generation')


@shared_task
def cleanup_empty_clusters():
    """Periodic task to deactivate clusters with no articles."""
    from django.utils import timezone
    from datetime import timedelta

    # Deactivate clusters with no articles that are older than 7 days
    cutoff = timezone.now() - timedelta(days=7)

    empty_clusters = TopicCluster.objects.filter(
        is_active=True,
        article_count=0,
        created_at__lt=cutoff
    )

    count = empty_clusters.update(is_active=False)

    if count:
        logger.info(f'Deactivated {count} empty clusters')
