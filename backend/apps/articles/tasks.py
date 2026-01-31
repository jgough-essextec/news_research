"""
Celery tasks for the Analyst Agent (scraping and embedding).
"""
import logging

from celery import shared_task

from apps.articles.models import Article

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def scrape_article(self, article_id: int):
    """Scrape content for an article."""
    from services.scraper_service import scrape_article_sync

    try:
        success = scrape_article_sync(article_id)

        if success:
            # Queue embedding generation
            generate_article_embedding.delay(article_id)
            # Queue summary generation
            generate_article_summary.delay(article_id)

    except Exception as e:
        logger.error(f'Error scraping article {article_id}: {e}')
        self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_article_embedding(self, article_id: int):
    """Generate embedding for an article."""
    from services.embedding_service import generate_article_embedding as gen_embedding

    try:
        success = gen_embedding(article_id)

        if success:
            # Queue deduplication and clustering
            process_article_clustering.delay(article_id)

    except Exception as e:
        logger.error(f'Error generating embedding for article {article_id}: {e}')
        self.retry(exc=e)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def process_article_clustering(self, article_id: int):
    """Process article for deduplication and clustering."""
    from services.deduplication_service import process_new_article

    try:
        process_new_article(article_id)
    except Exception as e:
        logger.error(f'Error clustering article {article_id}: {e}')
        self.retry(exc=e)


@shared_task
def scrape_pending_articles():
    """Periodic task to scrape pending articles."""
    articles = Article.objects.filter(
        scrape_status=Article.ScrapeStatus.PENDING,
        scrape_attempts__lt=3
    ).order_by('created_at')[:20]

    for article in articles:
        scrape_article.delay(article.id)

    logger.info(f'Queued {articles.count()} articles for scraping')


@shared_task
def retry_failed_articles():
    """Periodic task to retry failed article scrapes."""
    from django.utils import timezone
    from datetime import timedelta

    # Retry articles that failed more than 1 hour ago
    cutoff = timezone.now() - timedelta(hours=1)

    articles = Article.objects.filter(
        scrape_status=Article.ScrapeStatus.FAILED,
        scrape_attempts__lt=3,
        last_scrape_at__lt=cutoff
    ).order_by('last_scrape_at')[:10]

    for article in articles:
        scrape_article.delay(article.id)

    if articles:
        logger.info(f'Queued {articles.count()} failed articles for retry')


@shared_task
def generate_missing_embeddings():
    """Periodic task to generate embeddings for articles missing them."""
    articles = Article.objects.filter(
        scrape_status=Article.ScrapeStatus.SUCCESS,
        embedding__isnull=True
    ).order_by('created_at')[:20]

    for article in articles:
        generate_article_embedding.delay(article.id)

    if articles:
        logger.info(f'Queued {articles.count()} articles for embedding generation')


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_article_summary(self, article_id: int) -> str:
    """Generate AI summary for an article."""
    from services.generation_service import GenerationService

    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        logger.error(f'Article {article_id} not found')
        return "Article not found"

    if not article.content_text:
        logger.warning(f'Article {article_id} has no content to summarize')
        return "No content to summarize"

    try:
        service = GenerationService()
        prompt = f"""Summarize this article in 2-3 sentences.
Focus on the key takeaway and why it matters.
Be concise and factual.

Title: {article.title}
Content:
{article.content_text[:6000]}"""

        summary = service._generate_text(prompt)

        if summary:
            article.summary = summary
            article.save(update_fields=['summary'])
            logger.info(f'Generated summary for article {article_id}: {article.title}')
            return summary

        logger.warning(f'Failed to generate summary for article {article_id}')
        return "Failed to generate"

    except Exception as e:
        logger.error(f'Error generating summary for article {article_id}: {e}')
        self.retry(exc=e)
