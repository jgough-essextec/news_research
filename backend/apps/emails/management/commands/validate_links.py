"""
Management command to validate existing extracted links and mark valid articles.
"""
import re
from urllib.parse import urlparse

from django.core.management.base import BaseCommand

from apps.emails.models import ExtractedLink


class Command(BaseCommand):
    help = 'Validate extracted links and mark valid articles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be validated without making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each link',
        )

    def handle(self, *args, **options):
        links = ExtractedLink.objects.filter(is_valid_article=False)
        total = links.count()

        self.stdout.write(f'Found {total} links to validate...\n')

        validated = 0
        invalid = 0

        for link in links:
            is_valid = self._is_valid_article(link.canonical_url)

            if options['verbose']:
                status = 'VALID' if is_valid else 'INVALID'
                self.stdout.write(f'  [{status}] {link.canonical_url}')

            if is_valid:
                validated += 1
                if not options['dry_run']:
                    link.is_valid_article = True
                    link.save(update_fields=['is_valid_article'])
            else:
                invalid += 1

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'\nDry run: Would validate {validated} links, skip {invalid}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nValidated {validated} links, skipped {invalid}')
            )

    def _is_valid_article(self, url: str) -> bool:
        """
        Determine if a URL is likely to be a valid article.

        Checks for:
        - Sufficient path depth
        - Article-like URL patterns
        - Not a homepage or category page
        - Not a media file
        """
        try:
            parsed = urlparse(url.lower())
        except Exception:
            return False

        path = parsed.path

        # Skip empty or root paths
        if path in ['/', ''] or len(path) < 10:
            return False

        # Skip media files
        media_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.mp4', '.mp3', '.webp', '.svg']
        if any(path.endswith(ext) for ext in media_extensions):
            return False

        # Skip common non-article paths
        skip_patterns = [
            '/category/', '/categories/', '/tag/', '/tags/',
            '/author/', '/authors/', '/about/', '/contact/',
            '/login/', '/signup/', '/register/', '/subscribe/',
            '/search/', '/feed/', '/rss/', '/sitemap',
            '/privacy/', '/terms/', '/legal/',
        ]
        if any(pattern in path for pattern in skip_patterns):
            return False

        # Check for article-like URL patterns
        article_indicators = [
            '/article/', '/articles/',
            '/post/', '/posts/',
            '/blog/', '/blogs/',
            '/news/',
            '/story/', '/stories/',
            '/p/',  # Substack, Medium
            '/entry/',
            '/research/',
            '/insights/',
            '/opinion/',
            '/analysis/',
        ]

        # URL contains article indicator
        if any(indicator in path for indicator in article_indicators):
            return True

        # URL has date pattern like /2024/01/ or /2024-01-15/
        if re.search(r'/\d{4}/\d{2}/', path) or re.search(r'/\d{4}-\d{2}-\d{2}/', path):
            return True

        # URL has sufficient path depth (at least 3 segments)
        segments = [s for s in path.split('/') if s]
        if len(segments) >= 3:
            return True

        # URL ends with a slug-like pattern (letters/numbers with hyphens)
        last_segment = segments[-1] if segments else ''
        if re.match(r'^[a-z0-9]+-[a-z0-9-]+[a-z0-9]$', last_segment) and len(last_segment) > 20:
            return True

        return False
