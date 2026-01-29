"""
Management command to process pending links - create articles and scrape them.
"""
from django.core.management.base import BaseCommand

from apps.emails.models import ExtractedLink
from apps.articles.tasks import scrape_article
from services.scraper_service import create_article_from_link, scrape_article_sync


class Command(BaseCommand):
    help = 'Process pending links - create articles and scrape them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum number of links to process (default: 10)',
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Run synchronously instead of queuing Celery tasks',
        )

    def handle(self, *args, **options):
        pending_links = ExtractedLink.objects.filter(
            status=ExtractedLink.LinkStatus.PENDING,
            is_valid_article=True,
        ).select_related('newsletter_email')[:options['limit']]

        if not pending_links:
            self.stdout.write(self.style.WARNING('No pending links to process'))
            return

        self.stdout.write(f'Processing {len(pending_links)} links...\n')

        for link in pending_links:
            self.stdout.write(f'Processing: {link.canonical_url}')

            # Create article from link
            article = create_article_from_link(link)
            if not article:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed to create article'))
                continue

            self.stdout.write(f'  → Created article ID: {article.id}')

            if options['sync']:
                # Run synchronously for debugging
                try:
                    success = scrape_article_sync(article.id)
                    if success:
                        article.refresh_from_db()
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Scraped: {article.title}'))
                    else:
                        self.stdout.write(self.style.ERROR(f'  ✗ Failed to scrape'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Error: {e}'))
            else:
                # Queue Celery task
                task = scrape_article.delay(article.id)
                self.stdout.write(f'  → Queued scrape task: {task.id}')

        self.stdout.write(self.style.SUCCESS('\nDone!'))
