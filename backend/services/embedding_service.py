"""
Embedding service using Vertex AI text-embedding-gecko or Google GenAI.
Supports both API key and Vertex AI authentication modes.
"""
import logging
from typing import Optional

from django.conf import settings

from apps.articles.models import Article
from services.google_ai_client import use_api_key

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using Google AI."""

    def __init__(self):
        self._client = None
        self._model = None
        self._genai_client = None

    def _use_api_key(self) -> bool:
        """Check if API key authentication should be used."""
        return use_api_key()

    def _get_genai_client(self):
        """Get or create Google GenAI client for API key mode."""
        if self._genai_client is None:
            from google import genai
            self._genai_client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        return self._genai_client

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

        if self._use_api_key():
            return self._generate_embedding_api_key(text)
        else:
            return self._generate_embedding_vertex(text)

    def _generate_embedding_api_key(self, text: str) -> Optional[list[float]]:
        """Generate embedding using Google GenAI API key authentication."""
        try:
            client = self._get_genai_client()
            result = client.models.embed_content(
                model=settings.EMBEDDING_MODEL,
                contents=text
            )

            if result.embeddings and len(result.embeddings) > 0:
                return list(result.embeddings[0].values)

            return None

        except Exception as e:
            logger.error(f'Error generating embedding with API key: {e}')
            return None

    def _generate_embedding_vertex(self, text: str) -> Optional[list[float]]:
        """Generate embedding using Vertex AI authentication."""
        try:
            model = self._get_model()
            embeddings = model.get_embeddings([text])

            if embeddings and len(embeddings) > 0:
                return embeddings[0].values

            return None

        except Exception as e:
            logger.error(f'Error generating embedding with Vertex AI: {e}')
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

        if self._use_api_key():
            return self._generate_embeddings_batch_api_key(processed_texts)
        else:
            return self._generate_embeddings_batch_vertex(processed_texts)

    def _generate_embeddings_batch_api_key(self, texts: list[str]) -> list[Optional[list[float]]]:
        """Generate batch embeddings using Google GenAI API key authentication."""
        try:
            client = self._get_genai_client()
            all_embeddings = []

            # Process each text individually (API may have batch limits)
            for text in texts:
                if text:
                    try:
                        result = client.models.embed_content(
                            model=settings.EMBEDDING_MODEL,
                            contents=text
                        )
                        if result.embeddings and len(result.embeddings) > 0:
                            all_embeddings.append(list(result.embeddings[0].values))
                        else:
                            all_embeddings.append(None)
                    except Exception as e:
                        logger.error(f'Error generating single embedding in batch: {e}')
                        all_embeddings.append(None)
                else:
                    all_embeddings.append(None)

            return all_embeddings

        except Exception as e:
            logger.error(f'Error generating batch embeddings with API key: {e}')
            return [None] * len(texts)

    def _generate_embeddings_batch_vertex(self, texts: list[str]) -> list[Optional[list[float]]]:
        """Generate batch embeddings using Vertex AI authentication."""
        try:
            model = self._get_model()

            # Process in batches of 5 (Vertex AI limit)
            batch_size = 5
            all_embeddings = []

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
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
            logger.error(f'Error generating batch embeddings with Vertex AI: {e}')
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
