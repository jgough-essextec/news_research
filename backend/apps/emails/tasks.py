"""
Celery tasks for the Collector Agent.
"""
import logging

from celery import shared_task
from django.utils import timezone

from apps.core.models import User

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_emails_for_user(self, user_id: int):
    """Fetch new emails for a specific user."""
    from services.gmail_service import GmailService

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f'User {user_id} not found')
        return

    if not user.gmail_connected:
        logger.warning(f'Gmail not connected for user {user.email}')
        return

    try:
        service = GmailService(user)
        emails = service.fetch_emails(max_results=50)

        logger.info(f'Fetched {len(emails)} new emails for user {user.email}')

        # Process each email
        for email in emails:
            process_email.delay(email.id)

    except Exception as e:
        logger.error(f'Error fetching emails for user {user.email}: {e}')
        self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_email(self, email_id: int):
    """Process an email to extract links."""
    from apps.emails.models import NewsletterEmail
    from services.gmail_service import GmailService
    from services.scraper_service import create_article_from_link

    try:
        email = NewsletterEmail.objects.get(id=email_id)
    except NewsletterEmail.DoesNotExist:
        logger.error(f'Email {email_id} not found')
        return

    if email.is_processed:
        return

    try:
        service = GmailService(email.user)
        links = service.extract_links(email)

        logger.info(f'Extracted {len(links)} links from email: {email.subject}')

        # Create articles for valid links
        for link in links:
            article = create_article_from_link(link)
            if article and article.scrape_status == 'pending':
                from apps.articles.tasks import scrape_article
                scrape_article.delay(article.id)

        # Mark email as processed
        email.is_processed = True
        email.processed_at = timezone.now()
        email.save(update_fields=['is_processed', 'processed_at'])

    except Exception as e:
        logger.error(f'Error processing email {email_id}: {e}')
        self.retry(exc=e)


@shared_task
def fetch_all_user_emails():
    """Periodic task to fetch emails for all connected users."""
    users = User.objects.filter(gmail_connected=True, is_active=True)

    for user in users:
        fetch_emails_for_user.delay(user.id)

    logger.info(f'Queued email fetch for {users.count()} users')


@shared_task
def generate_email_summary(email_id: int) -> str:
    """Generate AI summary with bullet points for an email."""
    from bs4 import BeautifulSoup
    from apps.emails.models import NewsletterEmail
    from services.generation_service import GenerationService

    try:
        email = NewsletterEmail.objects.get(id=email_id)
    except NewsletterEmail.DoesNotExist:
        logger.error(f'Email {email_id} not found')
        return "Email not found"

    if not email.raw_html:
        return "No content to summarize"

    # Strip HTML to plain text
    text = BeautifulSoup(email.raw_html, 'html.parser').get_text()

    service = GenerationService()
    prompt = f"""Summarize this newsletter email in 3-5 bullet points.
Focus on the main topics and key announcements. Keep each bullet concise (1-2 sentences max).
Format as a simple list with "•" bullet characters.

Email content:
{text[:8000]}"""

    try:
        summary = service._generate_text(prompt)
        if summary:
            email.ai_summary = summary
            email.save(update_fields=['ai_summary'])
            logger.info(f'Generated summary for email: {email.subject}')
            return summary
        return "Failed to generate summary"
    except Exception as e:
        logger.error(f'Error generating email summary: {e}')
        return f"Error: {e}"
