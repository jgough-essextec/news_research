"""
Celery tasks for the Creator Agent.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def generate_blog_post(self, user_id: int, cluster_id: int, prompt: str = ''):
    """Generate a blog post from a topic cluster."""
    from services.generation_service import generate_blog_post_task

    try:
        post_id = generate_blog_post_task(user_id, cluster_id, prompt)

        if post_id:
            logger.info(f'Generated blog post {post_id} for cluster {cluster_id}')
            return post_id
        else:
            logger.warning(f'Failed to generate blog post for cluster {cluster_id}')
            return None

    except Exception as e:
        logger.error(f'Error generating blog post: {e}')
        self.retry(exc=e)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_blog_image(self, blog_post_id: int, prompt: str = ''):
    """Generate a header image for a blog post."""
    from services.generation_service import generate_blog_image_task

    try:
        image_id = generate_blog_image_task(blog_post_id, prompt)

        if image_id:
            logger.info(f'Generated image {image_id} for blog post {blog_post_id}')
            return image_id
        else:
            logger.warning(f'Failed to generate image for blog post {blog_post_id}')
            return None

    except Exception as e:
        logger.error(f'Error generating blog image: {e}')
        self.retry(exc=e)
