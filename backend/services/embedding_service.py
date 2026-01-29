"""
Embedding service using Vertex AI text-embedding-gecko.
"""
import logging
from typing import Optional

from django.conf import settings

from apps.articles.models import Article

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using Vertex AI."""

    def __init__(self):
        self._client = None
        self._model = None

    def _get_model(self):
        """Get or create Vertex AI embedding model."""
        if self._model is None:
            from google.cloud import aiplatform
            from vertexai.language_models import TextEmbeddingModel

            aiplatform.init(
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.VERTEX_AI_LOCATION,
            )

            self._model = TextEmbeddingModel.from_pretrained(settings.EMBEDDING_MODEL)

        return self._model

    def generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate embedding for a text string."""
        if not text or len(text.strip()) < 10:
            return None

        # Truncate text to model's limit (around 3000 tokens ~= 12000 chars)
        text = text[:12000]

        try:
            model = self._get_model()
            embeddings = model.get_embeddings([text])

            if embeddings and len(embeddings) > 0:
                return embeddings[0].values

            return None

        except Exception as e:
            logger.error(f'Error generating embedding: {e}')
            return None

    def generate_embeddings_batch(self, texts: list[str]) -> list[Optional[list[float]]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []

        # Truncate and filter texts
        processed_texts = []
        for text in texts:
            if text and len(text.strip()) >= 10:
                processed_texts.append(text[:12000])
            else:
                processed_texts.append('')

        try:
            model = self._get_model()

            # Process in batches of 5 (Vertex AI limit)
            batch_size = 5
            all_embeddings = []

            for i in range(0, len(processed_texts), batch_size):
                batch = processed_texts[i:i + batch_size]
                valid_batch = [t for t in batch if t]

                if valid_batch:
                    embeddings = model.get_embeddings(valid_batch)

                    # Map embeddings back to original positions
                    embedding_iter = iter(embeddings)
                    for text in batch:
                        if text:
                            emb = next(embedding_iter)
                            all_embeddings.append(emb.values)
                        else:
                            all_embeddings.append(None)
                else:
                    all_embeddings.extend([None] * len(batch))

            return all_embeddings

        except Exception as e:
            logger.error(f'Error generating batch embeddings: {e}')
            return [None] * len(texts)


def generate_article_embedding(article_id: int) -> bool:
    """Generate embedding for an article."""
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        logger.error(f'Article {article_id} not found')
        return False

    if not article.content_text:
        logger.warning(f'Article {article_id} has no content')
        return False

    # Combine title and content for embedding
    text = f"{article.title}\n\n{article.content_text}"

    service = EmbeddingService()
    embedding = service.generate_embedding(text)

    if embedding is None:
        logger.error(f'Failed to generate embedding for article {article_id}')
        return False

    article.embedding = embedding
    article.embedding_model = settings.EMBEDDING_MODEL
    article.save(update_fields=['embedding', 'embedding_model'])

    logger.info(f'Generated embedding for article: {article.title}')
    return True
