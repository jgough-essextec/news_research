"""
Blog post and image generation models for the Creator Agent.
"""
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class BlogPost(TimeStampedModel):
    """Represents a generated blog post."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        GENERATING = 'generating', 'Generating'
        REVIEW = 'review', 'Review'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'

    # Ownership
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_posts'
    )

    # Content
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500, unique=True)
    content_markdown = models.TextField(blank=True)
    content_html = models.TextField(blank=True)
    excerpt = models.TextField(blank=True, max_length=500)

    # Source tracking
    source_cluster = models.ForeignKey(
        'clusters.TopicCluster',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blog_posts'
    )
    source_articles = models.ManyToManyField(
        'articles.Article',
        related_name='featured_in_posts',
        blank=True
    )

    # Generation metadata
    generation_prompt = models.TextField(blank=True)
    generation_model = models.CharField(max_length=100, blank=True)
    generation_config = models.JSONField(default=dict, blank=True)

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    published_at = models.DateTimeField(null=True, blank=True)

    # SEO
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)

    class Meta:
        verbose_name = 'blog post'
        verbose_name_plural = 'blog posts'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class GeneratedImage(TimeStampedModel):
    """Represents an AI-generated image for a blog post."""

    class ImageType(models.TextChoices):
        HEADER = 'header', 'Header Image'
        INLINE = 'inline', 'Inline Image'
        THUMBNAIL = 'thumbnail', 'Thumbnail'

    blog_post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name='images'
    )

    image_type = models.CharField(
        max_length=20,
        choices=ImageType.choices,
        default=ImageType.HEADER
    )

    # Generation details
    prompt = models.TextField()
    negative_prompt = models.TextField(blank=True)
    generation_model = models.CharField(max_length=100, blank=True)
    generation_config = models.JSONField(default=dict, blank=True)

    # Storage
    image_url = models.URLField(max_length=2000, blank=True)
    storage_path = models.CharField(max_length=500, blank=True)

    # Metadata
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'generated image'
        verbose_name_plural = 'generated images'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.image_type} for {self.blog_post.title}"


class GenerationJob(TimeStampedModel):
    """Tracks async generation jobs."""

    class JobType(models.TextChoices):
        BLOG_POST = 'blog_post', 'Blog Post'
        CLUSTER_SUMMARY = 'cluster_summary', 'Cluster Summary'
        IMAGE = 'image', 'Image'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='generation_jobs'
    )

    job_type = models.CharField(max_length=20, choices=JobType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # References to generated content
    blog_post = models.ForeignKey(
        BlogPost,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generation_jobs'
    )
    cluster = models.ForeignKey(
        'clusters.TopicCluster',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generation_jobs'
    )

    # Job details
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'generation job'
        verbose_name_plural = 'generation jobs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.job_type} - {self.status}"
