"""
Management command to set up Celery Beat periodic task schedules.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Set up Celery Beat periodic task schedules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing schedules before creating new ones',
        )

    def handle(self, *args, **options):
        try:
            from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
        except ImportError:
            self.stdout.write(self.style.ERROR(
                'django-celery-beat is not installed. Install it with:\n'
                '  pip install django-celery-beat'
            ))
            return

        if options['clear']:
            self.stdout.write('Clearing existing periodic tasks...')
            PeriodicTask.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared all periodic tasks'))

        # Create interval schedules
        schedules = {}

        # 5 minutes
        schedules['5min'], _ = IntervalSchedule.objects.get_or_create(
            every=5, period=IntervalSchedule.MINUTES
        )

        # 10 minutes
        schedules['10min'], _ = IntervalSchedule.objects.get_or_create(
            every=10, period=IntervalSchedule.MINUTES
        )

        # 30 minutes
        schedules['30min'], _ = IntervalSchedule.objects.get_or_create(
            every=30, period=IntervalSchedule.MINUTES
        )

        # 1 hour
        schedules['1hour'], _ = IntervalSchedule.objects.get_or_create(
            every=1, period=IntervalSchedule.HOURS
        )

        # 2 hours
        schedules['2hours'], _ = IntervalSchedule.objects.get_or_create(
            every=2, period=IntervalSchedule.HOURS
        )

        # Daily at 3am
        schedules['daily_3am'], _ = CrontabSchedule.objects.get_or_create(
            minute='0', hour='3', day_of_week='*', day_of_month='*', month_of_year='*'
        )

        # Define tasks
        tasks = [
            {
                'name': 'Fetch all user emails',
                'task': 'apps.emails.tasks.fetch_all_user_emails',
                'schedule': schedules['30min'],
                'description': 'Fetch new newsletter emails from Gmail for all connected users',
            },
            {
                'name': 'Scrape pending articles',
                'task': 'apps.articles.tasks.scrape_pending_articles',
                'schedule': schedules['5min'],
                'description': 'Scrape content for articles in pending status',
            },
            {
                'name': 'Retry failed articles',
                'task': 'apps.articles.tasks.retry_failed_articles',
                'schedule': schedules['1hour'],
                'description': 'Retry scraping for failed articles (up to 3 attempts)',
            },
            {
                'name': 'Generate missing embeddings',
                'task': 'apps.articles.tasks.generate_missing_embeddings',
                'schedule': schedules['10min'],
                'description': 'Generate embeddings for successfully scraped articles',
            },
            {
                'name': 'Update cluster statistics',
                'task': 'apps.clusters.tasks.update_all_cluster_statistics',
                'schedule': schedules['1hour'],
                'description': 'Update article counts and priority scores for all clusters',
            },
            {
                'name': 'Generate cluster summaries',
                'task': 'apps.clusters.tasks.generate_summaries_for_new_clusters',
                'schedule': schedules['2hours'],
                'description': 'Generate AI summaries for clusters without one',
            },
            {
                'name': 'Cleanup empty clusters',
                'task': 'apps.clusters.tasks.cleanup_empty_clusters',
                'schedule': schedules['daily_3am'],
                'description': 'Deactivate clusters with no articles older than 7 days',
                'is_crontab': True,
            },
        ]

        created_count = 0
        updated_count = 0

        for task_config in tasks:
            schedule_field = 'crontab' if task_config.get('is_crontab') else 'interval'

            task, created = PeriodicTask.objects.update_or_create(
                name=task_config['name'],
                defaults={
                    'task': task_config['task'],
                    schedule_field: task_config['schedule'],
                    'enabled': True,
                    'description': task_config['description'],
                }
            )

            # Clear the other schedule field to avoid conflicts
            if task_config.get('is_crontab'):
                task.interval = None
            else:
                task.crontab = None
            task.save()

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  + Created: {task_config["name"]}'))
            else:
                updated_count += 1
                self.stdout.write(f'  ~ Updated: {task_config["name"]}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done! Created {created_count} tasks, updated {updated_count} tasks.'
        ))
        self.stdout.write('')
        self.stdout.write('Configured schedules:')
        self.stdout.write('  - fetch_all_user_emails: Every 30 minutes')
        self.stdout.write('  - scrape_pending_articles: Every 5 minutes')
        self.stdout.write('  - retry_failed_articles: Every 1 hour')
        self.stdout.write('  - generate_missing_embeddings: Every 10 minutes')
        self.stdout.write('  - update_all_cluster_statistics: Every 1 hour')
        self.stdout.write('  - generate_summaries_for_new_clusters: Every 2 hours')
        self.stdout.write('  - cleanup_empty_clusters: Daily at 3am')
        self.stdout.write('')
        self.stdout.write(
            'Remember to restart Celery beat to pick up changes:\n'
            '  docker compose restart beat'
        )
