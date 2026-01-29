"""
Management command to fetch emails from Gmail.
"""
import logging

from django.core.management.base import BaseCommand, CommandError

from apps.core.models import User
from services.gmail_service import GmailService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch newsletter emails from Gmail for a user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to fetch emails for. If not provided, uses the first connected user.',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='User email to fetch emails for.',
        )
        parser.add_argument(
            '--max-results',
            type=int,
            default=50,
            help='Maximum number of emails to fetch (default: 50)',
        )
        parser.add_argument(
            '--process',
            action='store_true',
            help='Also process emails to extract links',
        )

    def handle(self, *args, **options):
        # Find the user
        user = None

        if options['user_id']:
            try:
                user = User.objects.get(id=options['user_id'])
            except User.DoesNotExist:
                raise CommandError(f"User with ID {options['user_id']} not found")
        elif options['email']:
            try:
                user = User.objects.get(email=options['email'])
            except User.DoesNotExist:
                raise CommandError(f"User with email {options['email']} not found")
        else:
            # Get first user with Gmail connected
            user = User.objects.filter(gmail_connected=True).first()
            if not user:
                # Get any user
                user = User.objects.first()

        if not user:
            raise CommandError(
                "No users found. Create a user first:\n"
                "  1. Go to http://localhost:8000/api/auth/google/ to login\n"
                "  2. Then go to http://localhost:8000/api/auth/gmail/ to connect Gmail"
            )

        self.stdout.write(f"Found user: {user.email}")

        if not user.gmail_connected:
            raise CommandError(
                f"Gmail not connected for user {user.email}.\n"
                f"Connect Gmail by visiting: http://localhost:8000/api/auth/gmail/\n"
                f"(You must be logged in first via http://localhost:8000/api/auth/google/)"
            )

        if not user.gmail_refresh_token:
            raise CommandError(
                f"No Gmail refresh token for user {user.email}.\n"
                f"Re-connect Gmail by visiting: http://localhost:8000/api/auth/gmail/"
            )

        # Fetch emails
        self.stdout.write(f"Fetching emails for {user.email}...")

        try:
            service = GmailService(user)
            emails = service.fetch_emails(max_results=options['max_results'])

            self.stdout.write(
                self.style.SUCCESS(f"Fetched {len(emails)} new emails")
            )

            for email in emails:
                self.stdout.write(f"  - {email.subject} (from {email.sender_email})")

            if options['process'] and emails:
                self.stdout.write("\nProcessing emails to extract links...")
                total_links = 0

                for email in emails:
                    links = service.extract_links(email)
                    total_links += len(links)
                    self.stdout.write(f"  - {email.subject}: {len(links)} links")

                self.stdout.write(
                    self.style.SUCCESS(f"\nExtracted {total_links} total links")
                )

        except Exception as e:
            raise CommandError(f"Error fetching emails: {e}")
