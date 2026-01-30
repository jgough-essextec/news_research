"""
Management command to create test clusters by grouping articles with similar keywords.
This is for testing the pipeline without needing Vertex AI embeddings.
"""
import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.articles.models import Article
from apps.clusters.models import TopicCluster


class Command(BaseCommand):
    help = 'Create test clusters by grouping articles with similar keywords'

    # Keywords to group articles by
    TOPIC_KEYWORDS = {
        'OpenAI & ChatGPT': ['openai', 'chatgpt', 'gpt-4', 'gpt-5', 'sam altman'],
        'Google AI': ['google', 'gemini', 'deepmind', 'bard', 'vertex'],
        'Anthropic & Claude': ['anthropic', 'claude', 'constitutional ai'],
        'Meta AI': ['meta', 'llama', 'facebook ai', 'zuckerberg'],
        'AI Agents': ['agent', 'agentic', 'autonomous', 'copilot'],
        'AI Hardware & Chips': ['nvidia', 'chip', 'gpu', 'hardware', 'tpu'],
        'AI Startups & Funding': ['funding', 'startup', 'raise', 'investment', 'seed', 'series'],
        'AI Research': ['research', 'paper', 'arxiv', 'model', 'benchmark'],
        'AI Regulation': ['regulation', 'safety', 'policy', 'government', 'law'],
        'Generative AI': ['generative', 'image', 'video', 'audio', 'creative'],
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-articles',
            type=int,
            default=2,
            help='Minimum articles per cluster (default: 2)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing clusters first',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing clusters...')
            # Remove cluster assignments from articles
            Article.objects.update(topic_cluster=None, similarity_to_cluster=None)
            # Delete clusters
            deleted = TopicCluster.objects.all().delete()
            self.stdout.write(f'Deleted {deleted[0]} clusters')

        # Get all successfully scraped articles
        articles = Article.objects.filter(
            scrape_status=Article.ScrapeStatus.SUCCESS
        ).exclude(title='')

        self.stdout.write(f'Found {articles.count()} scraped articles')

        # Group articles by topic
        topic_articles = defaultdict(list)

        for article in articles:
            title_lower = article.title.lower()
            content_lower = (article.content_text or '')[:500].lower()
            combined = f'{title_lower} {content_lower}'

            for topic, keywords in self.TOPIC_KEYWORDS.items():
                if any(kw in combined for kw in keywords):
                    topic_articles[topic].append(article)
                    break  # Assign to first matching topic only

        # Create clusters for topics with enough articles
        created_clusters = []
        min_articles = options['min_articles']

        for topic, articles_list in topic_articles.items():
            if len(articles_list) >= min_articles:
                # Check if cluster already exists
                slug = slugify(topic)
                cluster, created = TopicCluster.objects.get_or_create(
                    slug=slug,
                    defaults={
                        'name': topic,
                        'description': f'Articles about {topic}',
                        'article_count': 0,
                        'is_active': True,
                    }
                )

                # Assign articles to cluster
                for article in articles_list:
                    article.topic_cluster = cluster
                    article.similarity_to_cluster = 0.85  # Placeholder similarity
                    article.save(update_fields=['topic_cluster', 'similarity_to_cluster'])

                # Set primary article (first one)
                cluster.primary_article = articles_list[0]
                cluster.article_count = len(articles_list)
                cluster.last_article_added_at = timezone.now()
                cluster.save()

                created_clusters.append((cluster, len(articles_list)))

                status = 'Created' if created else 'Updated'
                self.stdout.write(
                    self.style.SUCCESS(f'  {status}: {topic} ({len(articles_list)} articles)')
                )

        # Assign remaining articles to "Uncategorized" if they exist
        uncategorized = Article.objects.filter(
            scrape_status=Article.ScrapeStatus.SUCCESS,
            topic_cluster__isnull=True
        ).exclude(title='')

        if uncategorized.count() >= min_articles:
            cluster, created = TopicCluster.objects.get_or_create(
                slug='uncategorized-ai-news',
                defaults={
                    'name': 'Other AI News',
                    'description': 'Uncategorized AI news articles',
                    'is_active': True,
                }
            )

            for article in uncategorized[:50]:  # Limit to 50
                article.topic_cluster = cluster
                article.similarity_to_cluster = 0.5
                article.save(update_fields=['topic_cluster', 'similarity_to_cluster'])

            cluster.article_count = cluster.articles.count()
            cluster.primary_article = cluster.articles.first()
            cluster.last_article_added_at = timezone.now()
            cluster.save()

            created_clusters.append((cluster, cluster.article_count))
            self.stdout.write(
                self.style.SUCCESS(f'  Created: Other AI News ({cluster.article_count} articles)')
            )

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Created/updated {len(created_clusters)} clusters'))

        total_clustered = Article.objects.filter(topic_cluster__isnull=False).count()
        total_articles = Article.objects.filter(scrape_status=Article.ScrapeStatus.SUCCESS).count()
        self.stdout.write(f'Clustered: {total_clustered}/{total_articles} articles')
