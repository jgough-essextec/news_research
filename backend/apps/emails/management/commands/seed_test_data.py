"""
Management command to seed test data for development.
Creates sample emails and links that can be processed through the pipeline.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import User
from apps.emails.models import NewsletterEmail, ExtractedLink


class Command(BaseCommand):
    help = 'Seed test data for development (emails, links)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test data before seeding',
        )

    def handle(self, *args, **options):
        # Get or create a test user
        user, created = User.objects.get_or_create(
            email='test@example.com',
            defaults={
                'name': 'Test User',
                'is_admin': True,
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created test user: {user.email}'))
        else:
            self.stdout.write(f'Using existing user: {user.email}')

        if options['clear']:
            NewsletterEmail.objects.filter(user=user).delete()
            self.stdout.write(self.style.WARNING('Cleared existing test data'))

        # Sample AI news articles to test scraping
        test_articles = [
            {
                'url': 'https://openai.com/blog/chatgpt',
                'anchor_text': 'ChatGPT: Optimizing Language Models for Dialogue',
            },
            {
                'url': 'https://www.anthropic.com/news/claude-3-family',
                'anchor_text': 'Introducing Claude 3',
            },
            {
                'url': 'https://blog.google/technology/ai/google-gemini-ai/',
                'anchor_text': 'Introducing Gemini: Google\'s most capable AI model',
            },
            {
                'url': 'https://ai.meta.com/blog/meta-llama-3/',
                'anchor_text': 'Introducing Meta Llama 3',
            },
            {
                'url': 'https://www.theverge.com/2024/1/18/24042354/openai-gpt-store-ai-apps-available-chatgpt-plus',
                'anchor_text': 'OpenAI launches GPT Store',
            },
            {
                'url': 'https://techcrunch.com/2024/02/15/google-gemini-pro-1-5/',
                'anchor_text': 'Google announces Gemini 1.5 Pro',
            },
        ]

        # Create sample newsletter emails
        newsletters = [
            {
                'sender_email': 'newsletter@tldr.tech',
                'sender_name': 'TLDR AI',
                'subject': 'TLDR AI: Latest in AI and Machine Learning',
                'articles': test_articles[:3],
            },
            {
                'sender_email': 'digest@importai.net',
                'sender_name': 'Import AI',
                'subject': 'Import AI: Weekly AI News Digest',
                'articles': test_articles[3:],
            },
        ]

        for i, newsletter_data in enumerate(newsletters):
            email = NewsletterEmail.objects.create(
                user=user,
                gmail_message_id=f'test-message-{i}-{timezone.now().timestamp()}',
                thread_id=f'test-thread-{i}',
                sender_email=newsletter_data['sender_email'],
                sender_name=newsletter_data['sender_name'],
                subject=newsletter_data['subject'],
                received_date=timezone.now(),
                raw_html=f'<html><body>Test newsletter {i}</body></html>',
                is_processed=False,
            )
            self.stdout.write(f'Created email: {email.subject}')

            for article in newsletter_data['articles']:
                link = ExtractedLink.objects.create(
                    newsletter_email=email,
                    raw_url=article['url'],
                    canonical_url=article['url'],
                    anchor_text=article['anchor_text'],
                    is_valid_article=True,
                    status=ExtractedLink.LinkStatus.PENDING,
                )
                self.stdout.write(f'  - Added link: {link.canonical_url}')

        self.stdout.write(self.style.SUCCESS('\nTest data seeded successfully!'))
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Run scraping task: docker exec ai-news-backend python manage.py process_links')
        self.stdout.write('2. Or trigger from API: POST /api/articles/scrape-pending/')
        self.stdout.write('3. Check Django admin: http://localhost:8000/admin/')
