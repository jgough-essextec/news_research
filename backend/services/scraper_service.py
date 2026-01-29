"""
Web scraping service using Playwright and Readability.
"""
import hashlib
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import unquote, urlparse

from django.utils import timezone

from apps.articles.models import Article

logger = logging.getLogger(__name__)


def extract_real_url(tracking_url: str) -> str:
    """Extract the real URL from a tracking/redirect URL."""
    original_url = tracking_url

    # TLDR newsletter pattern: /CL0/https:%2F%2Fexample.com.../3/hash
    if '/CL0/' in tracking_url or '/CL1/' in tracking_url:
        parts = re.split(r'/CL\d+/', tracking_url)
        if len(parts) > 1:
            rest = parts[1]
            # The encoded URL ends at /number/ pattern
            encoded_part = re.split(r'/\d+/', rest)[0]
            real_url = unquote(encoded_part)
            parsed = urlparse(real_url)
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                logger.info(f'Extracted URL from TLDR tracking: {real_url[:80]}...')
                return real_url

    # Beehiiv pattern: contains hclick or similar
    if 'beehiiv' in tracking_url.lower() or 'hclick' in tracking_url.lower():
        # Try to find encoded URL in path
        match = re.search(r'(https?%3A%2F%2F[^&\s]+)', tracking_url)
        if match:
            real_url = unquote(match.group(1))
            parsed = urlparse(real_url)
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                logger.info(f'Extracted URL from Beehiiv tracking: {real_url[:80]}...')
                return real_url

    # Generic: url parameter
    match = re.search(r'[?&](?:url|redirect|goto|link|target)=([^&]+)', tracking_url, re.IGNORECASE)
    if match:
        real_url = unquote(match.group(1))
        parsed = urlparse(real_url)
        if parsed.scheme in ('http', 'https') and parsed.netloc:
            logger.info(f'Extracted URL from query param: {real_url[:80]}...')
            return real_url

    # Return original if no pattern matched
    return original_url


class ScraperService:
    """Service for scraping article content from URLs."""

    # Minimum content length to consider valid
    MIN_CONTENT_LENGTH = 200

    # User agent for scraping
    USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    def __init__(self):
        self._browser = None
        self._context = None

    async def _get_browser(self):
        """Get or create Playwright browser instance."""
        if self._browser is None:
            from playwright.async_api import async_playwright

            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self._context = await self._browser.new_context(
                user_agent=self.USER_AGENT,
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True,  # Ignore SSL cert errors for tracking URLs
            )
        return self._context

    async def scrape_url(self, url: str) -> Optional[dict]:
        """Scrape article content from a URL."""
        from readability import Document

        context = await self._get_browser()
        page = await context.new_page()

        try:
            # Navigate to page
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            if response is None or response.status >= 400:
                logger.warning(f'Failed to load {url}: status {response.status if response else "None"}')
                return None

            # Wait for content to load
            await page.wait_for_load_state('networkidle', timeout=10000)

            # Get page content
            html = await page.content()

            # Extract article using Readability
            doc = Document(html)
            content_html = doc.summary()
            title = doc.short_title() or doc.title()

            # Extract plain text
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content_html, 'lxml')
            content_text = soup.get_text(separator=' ', strip=True)

            # Check content length
            if len(content_text) < self.MIN_CONTENT_LENGTH:
                logger.warning(f'Content too short for {url}: {len(content_text)} chars')
                return None

            # Extract metadata
            metadata = await self._extract_metadata(page)

            return {
                'title': title,
                'content_html': content_html,
                'content_text': content_text,
                'word_count': len(content_text.split()),
                'excerpt': content_text[:500],
                **metadata
            }

        except Exception as e:
            logger.error(f'Error scraping {url}: {e}')
            return None
        finally:
            await page.close()

    async def _extract_metadata(self, page) -> dict:
        """Extract metadata from page."""
        metadata = {}

        try:
            # Get Open Graph and meta tags
            og_image = await page.evaluate('''
                () => {
                    const og = document.querySelector('meta[property="og:image"]');
                    return og ? og.content : '';
                }
            ''')
            metadata['og_image'] = og_image or ''

            author = await page.evaluate('''
                () => {
                    const meta = document.querySelector('meta[name="author"]');
                    if (meta) return meta.content;
                    const rel = document.querySelector('[rel="author"]');
                    if (rel) return rel.textContent;
                    return '';
                }
            ''')
            metadata['author'] = author or ''

            publication_date = await page.evaluate('''
                () => {
                    const selectors = [
                        'meta[property="article:published_time"]',
                        'meta[name="date"]',
                        'time[datetime]',
                    ];
                    for (const selector of selectors) {
                        const el = document.querySelector(selector);
                        if (el) {
                            return el.content || el.getAttribute('datetime') || '';
                        }
                    }
                    return '';
                }
            ''')
            if publication_date:
                try:
                    metadata['publication_date'] = datetime.fromisoformat(
                        publication_date.replace('Z', '+00:00')
                    )
                except ValueError:
                    pass

            # Get publication name
            publication = await page.evaluate('''
                () => {
                    const og = document.querySelector('meta[property="og:site_name"]');
                    return og ? og.content : '';
                }
            ''')
            metadata['publication'] = publication or ''

        except Exception as e:
            logger.warning(f'Error extracting metadata: {e}')

        return metadata

    async def close(self):
        """Close browser instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None


def scrape_article_sync(article_id: int) -> bool:
    """Synchronous wrapper for scraping an article."""
    import asyncio

    # Get article outside of async context
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        logger.error(f'Article {article_id} not found')
        return False

    # Update status
    article.scrape_status = Article.ScrapeStatus.IN_PROGRESS
    article.scrape_attempts += 1
    article.last_scrape_at = timezone.now()
    article.save(update_fields=['scrape_status', 'scrape_attempts', 'last_scrape_at'])

    # Extract real URL from tracking URL if needed
    url = extract_real_url(article.canonical_url)

    async def _scrape():
        scraper = ScraperService()
        try:
            return await scraper.scrape_url(url)
        finally:
            await scraper.close()

    try:
        result = asyncio.run(_scrape())

        if result is None:
            article.scrape_status = Article.ScrapeStatus.FAILED
            article.scrape_error = 'Failed to extract content'
            article.save()
            return False

        # Update article with scraped content
        article.title = result.get('title', '')[:500]
        article.author = result.get('author', '')[:255]
        article.publication = result.get('publication', '')[:255]
        article.publication_date = result.get('publication_date')
        article.content_text = result.get('content_text', '')
        article.content_html = result.get('content_html', '')
        article.excerpt = result.get('excerpt', '')[:500]
        article.word_count = result.get('word_count', 0)
        article.og_image = result.get('og_image', '')[:2000]
        article.scrape_status = Article.ScrapeStatus.SUCCESS
        article.scrape_error = ''
        article.save()

        logger.info(f'Successfully scraped article: {article.title}')
        return True

    except Exception as e:
        article.scrape_status = Article.ScrapeStatus.FAILED
        article.scrape_error = str(e)[:500]
        article.save()
        logger.error(f'Error scraping article {article_id}: {e}')
        return False


def create_article_from_link(link) -> Optional[Article]:
    """Create an article from an extracted link."""
    canonical_url = link.canonical_url
    url_hash = hashlib.sha256(canonical_url.encode()).hexdigest()

    # Check if article already exists
    existing = Article.objects.filter(url_hash=url_hash).first()
    if existing:
        link.article = existing
        link.status = link.LinkStatus.DUPLICATE
        link.save()
        return existing

    # Create new article
    article = Article.objects.create(
        canonical_url=canonical_url,
        url_hash=url_hash,
        scrape_status=Article.ScrapeStatus.PENDING,
    )

    link.article = article
    link.status = link.LinkStatus.VALID
    link.save()

    return article
