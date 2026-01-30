"""
Gmail API service for fetching newsletter emails.
"""
import base64
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup
from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from apps.core.models import User
from apps.emails.models import ExtractedLink, NewsletterEmail

logger = logging.getLogger(__name__)


class GmailService:
    """Service for interacting with Gmail API."""

    # Domains to exclude from link extraction
    EXCLUDED_DOMAINS = {
        'google.com', 'facebook.com', 'twitter.com', 'linkedin.com',
        'instagram.com', 'youtube.com', 'mailchimp.com', 'list-manage.com',
        'substack.com', 'beehiiv.com', 'convertkit.com', 'buttondown.email',
        'unsubscribe', 'mailto:', 'javascript:',
    }

    def __init__(self, user: User):
        self.user = user
        self.service = None

    def _get_credentials(self) -> Optional[Credentials]:
        """Get valid Google credentials for the user."""
        if not self.user.gmail_refresh_token:
            logger.warning(f'No Gmail refresh token for user {self.user.email}')
            return None

        creds = Credentials(
            token=None,
            refresh_token=self.user.gmail_refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            scopes=settings.GMAIL_SCOPES,
        )

        # Refresh the token
        try:
            creds.refresh(Request())
        except Exception as e:
            logger.error(f'Failed to refresh Gmail token for user {self.user.email}: {e}')
            return None

        return creds

    def _get_service(self):
        """Get or create Gmail API service."""
        if self.service is None:
            creds = self._get_credentials()
            if creds is None:
                raise ValueError('Could not get valid Gmail credentials')
            self.service = build('gmail', 'v1', credentials=creds)
        return self.service

    def fetch_emails(self, max_results: int = 50, after_date: Optional[datetime] = None) -> list[NewsletterEmail]:
        """Fetch newsletter emails from Gmail."""
        service = self._get_service()

        # Build query
        query_parts = [f'label:{settings.GMAIL_NEWSLETTER_LABEL}']
        if after_date:
            query_parts.append(f'after:{after_date.strftime("%Y/%m/%d")}')
        query = ' '.join(query_parts)

        # Fetch message list
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])
        logger.info(f'Found {len(messages)} messages for user {self.user.email}')

        fetched_emails = []
        for msg_summary in messages:
            msg_id = msg_summary['id']

            # Skip if already processed
            if NewsletterEmail.objects.filter(
                user=self.user,
                gmail_message_id=msg_id
            ).exists():
                continue

            # Fetch full message
            try:
                msg = service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='full'
                ).execute()

                email = self._process_message(msg)
                if email:
                    fetched_emails.append(email)
            except Exception as e:
                logger.error(f'Failed to fetch message {msg_id}: {e}')

        return fetched_emails

    def _process_message(self, msg: dict) -> Optional[NewsletterEmail]:
        """Process a Gmail message and create a NewsletterEmail."""
        headers = {h['name'].lower(): h['value'] for h in msg['payload'].get('headers', [])}

        # Parse sender
        sender_raw = headers.get('from', '')
        sender_name, sender_email = self._parse_sender(sender_raw)

        # Parse date
        date_raw = headers.get('date', '')
        received_date = self._parse_date(date_raw)

        # Get HTML content
        raw_html = self._extract_html_content(msg['payload'])

        # Create email record
        email = NewsletterEmail.objects.create(
            user=self.user,
            gmail_message_id=msg['id'],
            thread_id=msg.get('threadId', ''),
            sender_email=sender_email,
            sender_name=sender_name,
            subject=headers.get('subject', '(No subject)'),
            received_date=received_date,
            raw_html=raw_html,
            snippet=msg.get('snippet', ''),
        )

        logger.info(f'Created email record: {email.subject}')
        return email

    def _parse_sender(self, sender_raw: str) -> tuple[str, str]:
        """Parse sender name and email from From header."""
        match = re.match(r'^(.+?)\s*<(.+?)>$', sender_raw)
        if match:
            return match.group(1).strip('"'), match.group(2)
        return '', sender_raw

    def _parse_date(self, date_raw: str) -> datetime:
        """Parse email date header."""
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(date_raw)
        except Exception:
            return datetime.now(timezone.utc)

    def _extract_html_content(self, payload: dict) -> str:
        """Extract HTML content from email payload."""
        if payload.get('mimeType') == 'text/html':
            data = payload.get('body', {}).get('data', '')
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        parts = payload.get('parts', [])
        for part in parts:
            if part.get('mimeType') == 'text/html':
                data = part.get('body', {}).get('data', '')
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            if part.get('mimeType', '').startswith('multipart/'):
                result = self._extract_html_content(part)
                if result:
                    return result

        return ''

    def extract_links(self, email: NewsletterEmail) -> list[ExtractedLink]:
        """Extract and canonicalize links from a newsletter email."""
        if not email.raw_html:
            return []

        soup = BeautifulSoup(email.raw_html, 'lxml')
        links = []

        for anchor in soup.find_all('a', href=True):
            raw_url = anchor['href']

            # Skip excluded URLs
            if any(excluded in raw_url.lower() for excluded in self.EXCLUDED_DOMAINS):
                continue

            # Skip non-http URLs
            if not raw_url.startswith(('http://', 'https://')):
                continue

            canonical_url = self._canonicalize_url(raw_url)
            if not canonical_url:
                continue

            # Get anchor text and surrounding context
            anchor_text = anchor.get_text(strip=True)
            surrounding_text = self._get_surrounding_text(anchor)

            # Create link record
            link, created = ExtractedLink.objects.get_or_create(
                newsletter_email=email,
                canonical_url=canonical_url,
                defaults={
                    'raw_url': raw_url,
                    'anchor_text': anchor_text[:500],
                    'surrounding_text': surrounding_text[:1000],
                }
            )

            if created:
                # Validate link on creation
                link.is_valid_article = self._is_valid_article(canonical_url)
                link.save(update_fields=['is_valid_article'])
                links.append(link)

        # Update email link count
        email.link_count = email.extracted_links.count()
        email.save(update_fields=['link_count'])

        return links

    def _canonicalize_url(self, url: str) -> Optional[str]:
        """Canonicalize a URL by removing tracking parameters."""
        try:
            parsed = urlparse(url)

            # Remove tracking parameters
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'ref', 'source', 'mc_cid', 'mc_eid', 'fbclid', 'gclid', 'twclid',
                '_hsenc', '_hsmi', 'mkt_tok', 'trk', 'trkEmail',
            }

            query_params = parse_qs(parsed.query, keep_blank_values=True)
            filtered_params = {
                k: v for k, v in query_params.items()
                if k.lower() not in tracking_params
            }

            # Rebuild URL
            clean_query = urlencode(filtered_params, doseq=True)
            canonical = urlunparse((
                parsed.scheme,
                parsed.netloc.lower(),
                parsed.path.rstrip('/'),
                parsed.params,
                clean_query,
                ''  # Remove fragment
            ))

            return canonical

        except Exception as e:
            logger.warning(f'Failed to canonicalize URL {url}: {e}')
            return None

    def _get_surrounding_text(self, anchor) -> str:
        """Get text surrounding a link for context."""
        parent = anchor.parent
        if parent:
            return parent.get_text(strip=True)[:500]
        return ''

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
