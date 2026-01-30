"""
Management command to generate a test blog post from a cluster without requiring LLM.
This is for testing the UI without Google Cloud authentication.
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify

from apps.articles.models import Article
from apps.clusters.models import TopicCluster
from apps.core.models import User
from apps.generation.models import BlogPost


class Command(BaseCommand):
    help = 'Generate a test blog post from a cluster'

    def add_arguments(self, parser):
        parser.add_argument(
            'cluster_id',
            type=int,
            help='ID of the cluster to generate post from',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to create post as (default: first user)',
        )

    def handle(self, *args, **options):
        cluster_id = options['cluster_id']

        try:
            cluster = TopicCluster.objects.get(id=cluster_id)
        except TopicCluster.DoesNotExist:
            raise CommandError(f'Cluster {cluster_id} not found')

        # Get user
        if options['user_id']:
            try:
                user = User.objects.get(id=options['user_id'])
            except User.DoesNotExist:
                raise CommandError(f'User {options["user_id"]} not found')
        else:
            user = User.objects.first()
            if not user:
                raise CommandError('No users exist')

        # Get articles in cluster
        articles = cluster.articles.filter(
            scrape_status=Article.ScrapeStatus.SUCCESS
        ).order_by('-publication_date')[:10]

        if articles.count() < 2:
            raise CommandError(f'Cluster only has {articles.count()} articles, need at least 2')

        self.stdout.write(f'Generating post from cluster: {cluster.name}')
        self.stdout.write(f'Source articles: {articles.count()}')

        # Generate title
        title = f"AI News Roundup: {cluster.name}"

        # Generate slug
        base_slug = slugify(title)[:200]
        slug = base_slug
        counter = 1
        while BlogPost.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        # Generate content from articles
        content_parts = [
            f"# {title}\n",
            f"*Generated {timezone.now().strftime('%B %d, %Y')} from {articles.count()} source articles*\n",
            "---\n",
            f"## Overview\n",
            f"This week in {cluster.name}, we've seen several notable developments across the AI industry. ",
            f"Here's a roundup of the most important stories.\n\n",
        ]

        # Add article summaries
        for i, article in enumerate(articles, 1):
            content_parts.append(f"### {i}. {article.title}\n")
            content_parts.append(f"*Source: [{article.publication or 'Link'}]({article.canonical_url})*\n\n")

            excerpt = article.excerpt or (article.content_text[:300] if article.content_text else '')
            if excerpt:
                content_parts.append(f"{excerpt}\n\n")

        # Add conclusion
        content_parts.extend([
            "---\n",
            "## Key Takeaways\n",
            f"- The {cluster.name} space continues to evolve rapidly\n",
            "- Multiple major players are making significant moves\n",
            "- Watch this space for more developments\n\n",
            "*This is a test post generated for demonstration purposes.*\n",
        ])

        content = ''.join(content_parts)

        # Generate excerpt
        excerpt = f"A roundup of the latest developments in {cluster.name}, featuring {articles.count()} articles from leading sources."

        # Create blog post
        post = BlogPost.objects.create(
            created_by=user,
            title=title,
            slug=slug,
            content_markdown=content,
            excerpt=excerpt,
            source_cluster=cluster,
            generation_prompt='Test generation',
            generation_model='manual',
            status=BlogPost.Status.DRAFT,
        )

        # Link source articles
        post.source_articles.set(articles)

        self.stdout.write(self.style.SUCCESS(f'\nCreated blog post:'))
        self.stdout.write(f'  ID: {post.id}')
        self.stdout.write(f'  Title: {post.title}')
        self.stdout.write(f'  Slug: {post.slug}')
        self.stdout.write(f'  Status: {post.status}')
        self.stdout.write(f'  Articles linked: {post.source_articles.count()}')
        self.stdout.write('')
        self.stdout.write(f'View at: http://localhost:8000/api/posts/{post.id}/')
