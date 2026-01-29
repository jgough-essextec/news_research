"""
Content generation service using Gemini and Imagen.
"""
import logging
from typing import Optional

from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify

from apps.articles.models import Article
from apps.clusters.models import TopicCluster
from apps.core.models import User
from apps.generation.models import BlogPost, GeneratedImage, GenerationJob

logger = logging.getLogger(__name__)


class GenerationService:
    """Service for generating content using Vertex AI."""

    def __init__(self):
        self._model = None
        self._image_model = None

    def _get_model(self):
        """Get or create Gemini model."""
        if self._model is None:
            from google.cloud import aiplatform
            from vertexai.generative_models import GenerativeModel

            aiplatform.init(
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.VERTEX_AI_LOCATION,
            )

            self._model = GenerativeModel(settings.GENERATION_MODEL)

        return self._model

    def _get_image_model(self):
        """Get or create Imagen model."""
        if self._image_model is None:
            from google.cloud import aiplatform
            from vertexai.preview.vision_models import ImageGenerationModel

            aiplatform.init(
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.VERTEX_AI_LOCATION,
            )

            self._image_model = ImageGenerationModel.from_pretrained(
                settings.IMAGE_GENERATION_MODEL
            )

        return self._image_model

    def generate_cluster_summary(self, cluster: TopicCluster) -> Optional[str]:
        """Generate a summary for a topic cluster."""
        articles = cluster.articles.filter(
            scrape_status=Article.ScrapeStatus.SUCCESS
        ).order_by('-publication_date')[:10]

        if not articles:
            return None

        # Build context from articles
        articles_context = []
        for i, article in enumerate(articles, 1):
            articles_context.append(f"""
Article {i}: {article.title}
Source: {article.publication or 'Unknown'}
Date: {article.publication_date.strftime('%Y-%m-%d') if article.publication_date else 'Unknown'}
Summary: {article.excerpt or article.content_text[:500]}
""")

        prompt = f"""You are an AI news analyst. Summarize the following collection of articles about the same topic.

Topic: {cluster.name}

Articles:
{''.join(articles_context)}

Provide a comprehensive 2-3 paragraph summary that:
1. Identifies the main theme and key developments
2. Highlights the most significant points across all articles
3. Notes any different perspectives or conflicting information
4. Mentions the timeframe and sources covered

Write in a professional, journalistic style."""

        try:
            model = self._get_model()
            response = model.generate_content(prompt)

            summary = response.text
            cluster.master_summary = summary
            cluster.summary_generated_at = timezone.now()
            cluster.save(update_fields=['master_summary', 'summary_generated_at'])

            logger.info(f'Generated summary for cluster: {cluster.name}')
            return summary

        except Exception as e:
            logger.error(f'Error generating cluster summary: {e}')
            return None

    def generate_blog_post(
        self,
        user: User,
        cluster: TopicCluster,
        custom_prompt: str = ''
    ) -> Optional[BlogPost]:
        """Generate a blog post from a topic cluster."""
        articles = cluster.articles.filter(
            scrape_status=Article.ScrapeStatus.SUCCESS
        ).order_by('-publication_date')[:10]

        if not articles:
            logger.warning(f'No articles in cluster {cluster.name}')
            return None

        # Build article summaries for context
        article_summaries = []
        for article in articles:
            article_summaries.append(f"""
Title: {article.title}
Source: {article.publication or article.canonical_url}
Date: {article.publication_date.strftime('%Y-%m-%d') if article.publication_date else 'N/A'}
Content: {article.content_text[:1500]}
URL: {article.canonical_url}
""")

        base_prompt = f"""You are an expert technology journalist writing for a blog about AI news and developments.

Write a comprehensive, engaging blog post based on the following source articles about: {cluster.name}

Source Articles:
{'---'.join(article_summaries)}

Requirements:
1. Write a compelling headline
2. Start with an engaging introduction that hooks the reader
3. Cover the main developments and key points from all sources
4. Include proper attribution and citations to source articles (use markdown links)
5. Provide your analysis and insights on the implications
6. End with a conclusion that summarizes the key takeaways
7. Use markdown formatting (headers, bold, bullet points where appropriate)
8. Target 800-1200 words
9. Write in an informative but accessible style

{f'Additional instructions: {custom_prompt}' if custom_prompt else ''}

Format your response as:
TITLE: [Your headline]
EXCERPT: [A 1-2 sentence summary for preview]
CONTENT:
[Your full blog post in markdown]
"""

        try:
            model = self._get_model()
            response = model.generate_content(base_prompt)

            # Parse the response
            text = response.text
            title, excerpt, content = self._parse_blog_response(text)

            # Generate slug
            base_slug = slugify(title)[:200]
            slug = base_slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1

            # Create blog post
            post = BlogPost.objects.create(
                created_by=user,
                title=title,
                slug=slug,
                content_markdown=content,
                excerpt=excerpt,
                source_cluster=cluster,
                generation_prompt=base_prompt,
                generation_model=settings.GENERATION_MODEL,
                status=BlogPost.Status.DRAFT,
            )

            # Link source articles
            post.source_articles.set(articles)

            logger.info(f'Generated blog post: {post.title}')
            return post

        except Exception as e:
            logger.error(f'Error generating blog post: {e}')
            return None

    def _parse_blog_response(self, text: str) -> tuple[str, str, str]:
        """Parse the structured blog post response."""
        lines = text.strip().split('\n')

        title = ''
        excerpt = ''
        content_lines = []
        current_section = None

        for line in lines:
            if line.startswith('TITLE:'):
                title = line.replace('TITLE:', '').strip()
                current_section = 'title'
            elif line.startswith('EXCERPT:'):
                excerpt = line.replace('EXCERPT:', '').strip()
                current_section = 'excerpt'
            elif line.startswith('CONTENT:'):
                current_section = 'content'
            elif current_section == 'content':
                content_lines.append(line)

        content = '\n'.join(content_lines).strip()

        # Fallback parsing if structured format not followed
        if not title and content:
            # Try to extract title from first markdown header
            for line in content.split('\n'):
                if line.startswith('# '):
                    title = line.replace('# ', '').strip()
                    break

        if not title:
            title = 'AI News Update'

        if not excerpt:
            excerpt = content[:200] + '...' if len(content) > 200 else content

        return title, excerpt, content

    def generate_image(
        self,
        blog_post: BlogPost,
        custom_prompt: str = ''
    ) -> Optional[GeneratedImage]:
        """Generate a header image for a blog post."""
        # Build image prompt from blog post content
        base_prompt = custom_prompt or f"""Create a professional, modern illustration for a technology blog post titled: "{blog_post.title}"

The image should:
- Be suitable as a blog header image
- Have a clean, professional tech aesthetic
- Use a modern color palette
- Not include any text or words
- Convey themes of AI, technology, and innovation
- Be visually striking and attention-grabbing"""

        try:
            model = self._get_image_model()

            response = model.generate_images(
                prompt=base_prompt,
                number_of_images=1,
                aspect_ratio='16:9',
                safety_filter_level='block_some',
            )

            if not response.images:
                logger.warning('No images generated')
                return None

            image = response.images[0]

            # Save image to storage
            import base64
            import uuid

            from django.core.files.base import ContentFile
            from django.core.files.storage import default_storage

            filename = f'generated/{blog_post.id}/{uuid.uuid4()}.png'
            image_bytes = base64.b64decode(image._image_bytes)
            path = default_storage.save(filename, ContentFile(image_bytes))

            # Create GeneratedImage record
            generated_image = GeneratedImage.objects.create(
                blog_post=blog_post,
                image_type=GeneratedImage.ImageType.HEADER,
                prompt=base_prompt,
                generation_model=settings.IMAGE_GENERATION_MODEL,
                storage_path=path,
                image_url=default_storage.url(path),
                width=1920,
                height=1080,
                alt_text=f'Header image for: {blog_post.title}',
            )

            logger.info(f'Generated image for blog post: {blog_post.title}')
            return generated_image

        except Exception as e:
            logger.error(f'Error generating image: {e}')
            return None


def generate_cluster_summary_task(cluster_id: int) -> bool:
    """Task wrapper for generating cluster summary."""
    try:
        cluster = TopicCluster.objects.get(id=cluster_id)
    except TopicCluster.DoesNotExist:
        logger.error(f'Cluster {cluster_id} not found')
        return False

    service = GenerationService()
    summary = service.generate_cluster_summary(cluster)
    return summary is not None


def generate_blog_post_task(user_id: int, cluster_id: int, prompt: str = '') -> Optional[int]:
    """Task wrapper for generating blog post."""
    try:
        user = User.objects.get(id=user_id)
        cluster = TopicCluster.objects.get(id=cluster_id)
    except (User.DoesNotExist, TopicCluster.DoesNotExist) as e:
        logger.error(f'User or cluster not found: {e}')
        return None

    # Create job record
    job = GenerationJob.objects.create(
        user=user,
        job_type=GenerationJob.JobType.BLOG_POST,
        status=GenerationJob.Status.IN_PROGRESS,
        cluster=cluster,
        input_data={'prompt': prompt},
        started_at=timezone.now(),
    )

    service = GenerationService()
    post = service.generate_blog_post(user, cluster, prompt)

    if post:
        job.status = GenerationJob.Status.COMPLETED
        job.blog_post = post
        job.output_data = {'blog_post_id': post.id}
        job.completed_at = timezone.now()
        job.save()
        return post.id
    else:
        job.status = GenerationJob.Status.FAILED
        job.error_message = 'Failed to generate blog post'
        job.completed_at = timezone.now()
        job.save()
        return None


def generate_blog_image_task(blog_post_id: int, prompt: str = '') -> Optional[int]:
    """Task wrapper for generating blog image."""
    try:
        post = BlogPost.objects.get(id=blog_post_id)
    except BlogPost.DoesNotExist:
        logger.error(f'Blog post {blog_post_id} not found')
        return None

    # Create job record
    job = GenerationJob.objects.create(
        user=post.created_by,
        job_type=GenerationJob.JobType.IMAGE,
        status=GenerationJob.Status.IN_PROGRESS,
        blog_post=post,
        input_data={'prompt': prompt},
        started_at=timezone.now(),
    )

    service = GenerationService()
    image = service.generate_image(post, prompt)

    if image:
        job.status = GenerationJob.Status.COMPLETED
        job.output_data = {'image_id': image.id}
        job.completed_at = timezone.now()
        job.save()
        return image.id
    else:
        job.status = GenerationJob.Status.FAILED
        job.error_message = 'Failed to generate image'
        job.completed_at = timezone.now()
        job.save()
        return None
