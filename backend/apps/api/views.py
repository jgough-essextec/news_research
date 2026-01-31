"""
API ViewSets.
"""
from django_filters import rest_framework as filters
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.articles.models import Article
from apps.clusters.models import TopicCluster
from apps.core.models import User
from apps.emails.models import ExtractedLink, NewsletterEmail
from apps.generation.models import BlogPost, GenerationJob

from .serializers import (
    ArticleDetailSerializer,
    ArticleListSerializer,
    BlogPostDetailSerializer,
    BlogPostListSerializer,
    ExtractedLinkSerializer,
    GenerationJobSerializer,
    NewsletterEmailDetailSerializer,
    NewsletterEmailSerializer,
    TopicClusterSerializer,
    UserSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for user management."""

    serializer_class = UserSerializer
    # permission_classes inherited from settings

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return User.objects.none()
        if user.is_admin:
            return User.objects.all()
        return User.objects.filter(id=user.id)


class NewsletterEmailFilter(filters.FilterSet):
    sender = filters.CharFilter(field_name='sender_email', lookup_expr='icontains')
    subject = filters.CharFilter(field_name='subject', lookup_expr='icontains')
    received_after = filters.DateTimeFilter(field_name='received_date', lookup_expr='gte')
    received_before = filters.DateTimeFilter(field_name='received_date', lookup_expr='lte')

    class Meta:
        model = NewsletterEmail
        fields = ['is_processed', 'sender', 'subject', 'received_after', 'received_before']


class EmailViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for newsletter emails."""

    # permission_classes inherited from settings
    filterset_class = NewsletterEmailFilter
    search_fields = ['subject', 'sender_name', 'sender_email']
    ordering_fields = ['received_date', 'created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return NewsletterEmailDetailSerializer
        return NewsletterEmailSerializer

    def get_queryset(self):
        qs = NewsletterEmail.objects.all() if not self.request.user.is_authenticated else NewsletterEmail.objects.filter(user=self.request.user)
        if self.action == 'retrieve':
            return qs.prefetch_related('extracted_links__article')
        return qs

    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Trigger a Gmail sync for the current user."""
        from django.conf import settings
        from apps.emails.tasks import fetch_emails_for_user
        from apps.core.models import User

        # For development: use first user or create dev user
        if not request.user.is_authenticated:
            if settings.DEBUG:
                user = User.objects.first()
                if not user:
                    return Response(
                        {'error': 'No users exist. Create a user in Django admin first.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    {'error': 'Authentication required to sync emails'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        else:
            user = request.user

        if not user.gmail_connected:
            return Response(
                {'error': 'Gmail not connected. Connect Gmail in Django admin or settings.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        task = fetch_emails_for_user.delay(user.id)
        return Response({'task_id': task.id, 'status': 'started'})

    @action(detail=True, methods=['post'])
    def generate_summary(self, request, pk=None):
        """Generate AI summary for a single email."""
        from bs4 import BeautifulSoup
        from services.generation_service import GenerationService

        email = self.get_object()

        if not email.raw_html:
            return Response(
                {'error': 'No email content to summarize'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Strip HTML to plain text
        text = BeautifulSoup(email.raw_html, 'html.parser').get_text()

        try:
            service = GenerationService()
            prompt = f"""Create a concise summary of this newsletter.

Format:
**Headline** (5-10 words capturing the main theme)

• Bullet 1 (key point, max 15 words)
• Bullet 2
• Bullet 3 (3-5 bullets total)

Rules:
- No preamble ("Here is a summary", "This newsletter covers")
- No filler phrases ("The newsletter provides", "Readers will learn")
- Start bullets with action verbs or key nouns
- Facts only, no commentary

Email:
{text[:8000]}"""

            summary = service._generate_text(prompt)

            if not summary:
                return Response(
                    {'error': 'Failed to generate summary - AI service returned empty response'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            email.ai_summary = summary
            email.save(update_fields=['ai_summary'])

            return Response({
                'status': 'success',
                'ai_summary': summary
            })

        except Exception as e:
            return Response(
                {'error': f'Failed to generate summary: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExtractedLinkViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for extracted links."""

    serializer_class = ExtractedLinkSerializer
    # permission_classes inherited from settings
    filterset_fields = ['status', 'is_valid_article']
    search_fields = ['canonical_url', 'anchor_text']
    ordering_fields = ['created_at']

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return ExtractedLink.objects.all().select_related('newsletter_email', 'article')
        return ExtractedLink.objects.filter(
            newsletter_email__user=self.request.user
        ).select_related('newsletter_email', 'article')


class ArticleFilter(filters.FilterSet):
    publication = filters.CharFilter(lookup_expr='icontains')
    title = filters.CharFilter(lookup_expr='icontains')
    published_after = filters.DateTimeFilter(field_name='publication_date', lookup_expr='gte')
    published_before = filters.DateTimeFilter(field_name='publication_date', lookup_expr='lte')
    has_cluster = filters.BooleanFilter(field_name='topic_cluster', lookup_expr='isnull', exclude=True)

    class Meta:
        model = Article
        fields = ['scrape_status', 'topic_cluster', 'publication', 'title', 'has_cluster']


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for articles (shared across all users)."""

    # permission_classes inherited from settings
    filterset_class = ArticleFilter
    search_fields = ['title', 'content_text', 'canonical_url']
    ordering_fields = ['publication_date', 'created_at', 'word_count']

    def get_queryset(self):
        return Article.objects.select_related('topic_cluster')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ArticleDetailSerializer
        return ArticleListSerializer

    @action(detail=True, methods=['post'])
    def rescrape(self, request, pk=None):
        """Re-scrape an article."""
        from apps.articles.tasks import scrape_article

        article = self.get_object()
        task = scrape_article.delay(article.id)
        return Response({'task_id': task.id, 'status': 'started'})

    @action(detail=True, methods=['post'])
    def generate_summary(self, request, pk=None):
        """Generate AI summary for an article."""
        from apps.articles.tasks import generate_article_summary

        article = self.get_object()
        task = generate_article_summary.delay(article.id)
        return Response({'task_id': task.id, 'status': 'started'})

    @action(detail=False, methods=['post'])
    def process_pending(self, request):
        """Process all pending articles by triggering scrape tasks."""
        from apps.articles.tasks import scrape_pending_articles

        pending_count = Article.objects.filter(
            scrape_status=Article.ScrapeStatus.PENDING,
            scrape_attempts__lt=3
        ).count()

        if pending_count == 0:
            return Response({'status': 'no_pending', 'message': 'No pending articles'})

        task = scrape_pending_articles.delay()
        return Response({
            'task_id': task.id,
            'status': 'started',
            'pending_count': pending_count
        })

    @action(detail=False, methods=['get'])
    def similar(self, request):
        """Find similar articles to a given article."""
        article_id = request.query_params.get('article_id')
        threshold = float(request.query_params.get('threshold', 0.85))
        limit = int(request.query_params.get('limit', 10))

        if not article_id:
            return Response(
                {'error': 'article_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            return Response(
                {'error': 'Article not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if article.embedding is None:
            return Response(
                {'error': 'Article has no embedding'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from pgvector.django import CosineDistance

        similar = Article.objects.exclude(id=article.id).exclude(
            embedding__isnull=True
        ).annotate(
            distance=CosineDistance('embedding', article.embedding)
        ).filter(
            distance__lt=(1 - threshold)
        ).order_by('distance')[:limit]

        serializer = ArticleListSerializer(similar, many=True)
        return Response(serializer.data)


class ClusterViewSet(viewsets.ModelViewSet):
    """ViewSet for topic clusters (shared across all users)."""

    serializer_class = TopicClusterSerializer
    # permission_classes inherited from settings
    filterset_fields = ['is_active']
    search_fields = ['name', 'description', 'master_summary']
    ordering_fields = ['priority_score', 'article_count', 'created_at']

    def get_queryset(self):
        return TopicCluster.objects.select_related('primary_article')

    @action(detail=True, methods=['get'])
    def articles(self, request, pk=None):
        """Get articles in this cluster."""
        cluster = self.get_object()
        articles = cluster.articles.all().order_by('-publication_date')

        # Use the viewset's paginator for consistency with other list endpoints
        page = self.paginate_queryset(articles)
        if page is not None:
            serializer = ArticleListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ArticleListSerializer(articles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def generate_summary(self, request, pk=None):
        """Generate a summary for this cluster."""
        from apps.clusters.tasks import generate_cluster_summary

        cluster = self.get_object()
        task = generate_cluster_summary.delay(cluster.id)
        return Response({'task_id': task.id, 'status': 'started'})

    @action(detail=True, methods=['post'])
    def generate_post(self, request, pk=None):
        """Generate a blog post from this cluster."""
        from django.utils.text import slugify
        from apps.generation.tasks import generate_blog_post

        cluster = self.get_object()
        if cluster.article_count < 2:
            return Response(
                {'error': 'Need at least 2 articles to generate a post'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the user (for development, use first user if not authenticated)
        if request.user.is_authenticated:
            user = request.user
        else:
            from django.conf import settings
            if settings.DEBUG:
                user = User.objects.first()
                if not user:
                    return Response(
                        {'error': 'No users exist. Create a user first.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        # Create draft blog post
        import uuid
        post = BlogPost.objects.create(
            title=f"Draft: {cluster.name}",
            slug=slugify(f"{cluster.name}-{uuid.uuid4().hex[:8]}"),
            source_cluster=cluster,
            created_by=user,
            status=BlogPost.Status.DRAFT,
        )

        prompt = request.data.get('prompt', '')
        task = generate_blog_post.delay(user.id, cluster.id, prompt)

        return Response({
            'task_id': task.id,
            'post_id': post.id,
            'status': 'started'
        })


class BlogPostViewSet(viewsets.ModelViewSet):
    """ViewSet for blog posts (user-owned)."""

    # permission_classes inherited from settings
    filterset_fields = ['status', 'source_cluster']
    search_fields = ['title', 'content_markdown', 'excerpt']
    ordering_fields = ['created_at', 'published_at']

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return BlogPost.objects.all().select_related(
                'source_cluster', 'created_by'
            ).prefetch_related('images')
        return BlogPost.objects.filter(
            created_by=self.request.user
        ).select_related(
            'source_cluster', 'created_by'
        ).prefetch_related('images')

    def get_serializer_class(self):
        if self.action in ['retrieve', 'create', 'update', 'partial_update']:
            return BlogPostDetailSerializer
        return BlogPostListSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a new blog post from a cluster."""
        from apps.generation.tasks import generate_blog_post

        cluster_id = request.data.get('cluster_id')
        prompt = request.data.get('prompt', '')

        if not cluster_id:
            return Response(
                {'error': 'cluster_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        task = generate_blog_post.delay(
            user_id=request.user.id,
            cluster_id=cluster_id,
            prompt=prompt
        )
        return Response({'task_id': task.id, 'status': 'started'})

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a blog post."""
        from django.utils import timezone

        post = self.get_object()
        post.status = BlogPost.Status.PUBLISHED
        post.published_at = timezone.now()
        post.save()

        serializer = self.get_serializer(post)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def generate_image(self, request, pk=None):
        """Generate a header image for the blog post."""
        from apps.generation.tasks import generate_blog_image

        post = self.get_object()
        prompt = request.data.get('prompt', '')

        task = generate_blog_image.delay(
            blog_post_id=post.id,
            prompt=prompt
        )
        return Response({'task_id': task.id, 'status': 'started'})


class GenerationJobViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for generation jobs (user-owned)."""

    serializer_class = GenerationJobSerializer
    # permission_classes inherited from settings
    filterset_fields = ['job_type', 'status']
    ordering_fields = ['created_at', 'started_at', 'completed_at']

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return GenerationJob.objects.all()
        return GenerationJob.objects.filter(user=self.request.user)
