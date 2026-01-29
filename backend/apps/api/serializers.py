"""
API Serializers.
"""
from rest_framework import serializers

from apps.articles.models import Article
from apps.clusters.models import TopicCluster
from apps.core.models import User
from apps.emails.models import ExtractedLink, NewsletterEmail
from apps.generation.models import BlogPost, GeneratedImage, GenerationJob


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'avatar_url', 'gmail_connected', 'is_admin', 'created_at']
        read_only_fields = ['id', 'email', 'gmail_connected', 'is_admin', 'created_at']


class NewsletterEmailSerializer(serializers.ModelSerializer):
    link_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = NewsletterEmail
        fields = [
            'id', 'gmail_message_id', 'sender_email', 'sender_name',
            'subject', 'received_date', 'snippet', 'is_processed',
            'processed_at', 'link_count', 'created_at'
        ]
        read_only_fields = ['id', 'gmail_message_id', 'processed_at', 'link_count', 'created_at']


class ExtractedLinkSerializer(serializers.ModelSerializer):
    newsletter_subject = serializers.CharField(source='newsletter_email.subject', read_only=True)

    class Meta:
        model = ExtractedLink
        fields = [
            'id', 'newsletter_email', 'newsletter_subject', 'raw_url',
            'canonical_url', 'anchor_text', 'status', 'is_valid_article',
            'article', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ArticleListSerializer(serializers.ModelSerializer):
    cluster_name = serializers.CharField(source='topic_cluster.name', read_only=True, allow_null=True)

    class Meta:
        model = Article
        fields = [
            'id', 'canonical_url', 'title', 'author', 'publication',
            'publication_date', 'excerpt', 'word_count', 'scrape_status',
            'topic_cluster', 'cluster_name', 'og_image', 'created_at'
        ]


class ArticleDetailSerializer(serializers.ModelSerializer):
    cluster_name = serializers.CharField(source='topic_cluster.name', read_only=True, allow_null=True)
    source_links = ExtractedLinkSerializer(many=True, read_only=True)

    class Meta:
        model = Article
        fields = [
            'id', 'canonical_url', 'url_hash', 'title', 'author',
            'publication', 'publication_date', 'content_text', 'excerpt',
            'word_count', 'summary', 'scrape_status', 'scrape_error',
            'topic_cluster', 'cluster_name', 'similarity_to_cluster',
            'og_image', 'language', 'source_links', 'created_at', 'updated_at'
        ]


class TopicClusterSerializer(serializers.ModelSerializer):
    primary_article_title = serializers.CharField(
        source='primary_article.title', read_only=True, allow_null=True
    )

    class Meta:
        model = TopicCluster
        fields = [
            'id', 'name', 'slug', 'description', 'primary_article',
            'primary_article_title', 'article_count', 'priority_score',
            'master_summary', 'summary_generated_at', 'is_active',
            'last_article_added_at', 'created_at'
        ]
        read_only_fields = ['id', 'article_count', 'priority_score', 'summary_generated_at', 'created_at']


class GeneratedImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedImage
        fields = [
            'id', 'image_type', 'prompt', 'image_url', 'storage_path',
            'width', 'height', 'alt_text', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class BlogPostListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='created_by.name', read_only=True)
    cluster_name = serializers.CharField(source='source_cluster.name', read_only=True, allow_null=True)
    header_image = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'status', 'created_by',
            'author_name', 'source_cluster', 'cluster_name', 'header_image',
            'published_at', 'created_at'
        ]

    def get_header_image(self, obj):
        header = obj.images.filter(image_type='header').first()
        if header:
            return header.image_url
        return None


class BlogPostDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='created_by.name', read_only=True)
    cluster_name = serializers.CharField(source='source_cluster.name', read_only=True, allow_null=True)
    images = GeneratedImageSerializer(many=True, read_only=True)
    source_articles = ArticleListSerializer(many=True, read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'content_markdown', 'content_html',
            'excerpt', 'status', 'created_by', 'author_name',
            'source_cluster', 'cluster_name', 'source_articles', 'images',
            'generation_prompt', 'generation_model', 'meta_title',
            'meta_description', 'published_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'generation_model', 'created_at', 'updated_at']


class GenerationJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenerationJob
        fields = [
            'id', 'job_type', 'status', 'blog_post', 'cluster',
            'input_data', 'output_data', 'error_message',
            'started_at', 'completed_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'status', 'output_data', 'error_message',
            'started_at', 'completed_at', 'created_at'
        ]
