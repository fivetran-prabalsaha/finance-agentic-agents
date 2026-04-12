"""
Embedding Service - Unified interface for generating and managing embeddings

This service provides:
1. Embedding generation for rules, violations, and exemptions
2. Support for multiple embedding providers (HuggingFace, Voyage AI, OpenAI)
3. pgvector storage and retrieval
4. Similarity search utilities
5. Caching for performance
"""

import logging
import os
from enum import Enum
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EmbeddingProvider(Enum):
    """Supported embedding providers"""
    HUGGINGFACE = "huggingface"  # Free, local
    VOYAGE = "voyage"  # Production, high quality
    OPENAI = "openai"  # Alternative
    COHERE = "cohere"  # Alternative


class EmbeddingService:
    """Service for generating and managing embeddings with pgvector"""

    def __init__(
        self,
        provider: str = "huggingface",
        model_name: str | None = None,
        dimension: int = 384,
        cache_embeddings: bool = True,
        session: Session | None = None
    ):
        """
        Initialize Embedding Service

        Args:
            provider: Embedding provider (huggingface, voyage, openai, cohere)
            model_name: Specific model to use (provider-dependent)
            dimension: Embedding dimension (384 for MiniLM, 1536 for OpenAI/Voyage)
            cache_embeddings: Whether to cache embeddings in memory
            session: SQLAlchemy session for database operations
        """
        self.provider = EmbeddingProvider(provider.lower())
        self.dimension = dimension
        self.cache_embeddings = cache_embeddings
        self.session = session
        self._embedding_cache: dict[str, np.ndarray] = {}

        # Initialize embedding model based on provider
        self.model = self._initialize_model(model_name)

        logger.info(
            f"Embedding Service initialized: {self.provider.value} "
            f"(dim={self.dimension}, cache={cache_embeddings})"
        )

    def _initialize_model(self, model_name: str | None = None):
        """Initialize embedding model based on provider"""
        if self.provider == EmbeddingProvider.HUGGINGFACE:
            return self._init_huggingface(model_name)
        elif self.provider == EmbeddingProvider.VOYAGE:
            return self._init_voyage(model_name)
        elif self.provider == EmbeddingProvider.OPENAI:
            return self._init_openai(model_name)
        elif self.provider == EmbeddingProvider.COHERE:
            return self._init_cohere(model_name)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _init_huggingface(self, model_name: str | None) -> Any:
        """Initialize HuggingFace embeddings (free, local)"""
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            from langchain_community.embeddings import HuggingFaceEmbeddings

        default_model = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dim
        # alternative: "sentence-transformers/all-mpnet-base-v2"  # 768 dim

        model = HuggingFaceEmbeddings(
            model_name=model_name or default_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

        logger.info(f"Initialized HuggingFace: {model_name or default_model}")
        return model

    def _init_voyage(self, model_name: str | None) -> Any:
        """Initialize Voyage AI embeddings (production quality)"""
        try:
            import voyageai
            api_key = os.getenv('VOYAGE_API_KEY')
            if not api_key:
                raise ValueError("VOYAGE_API_KEY not found in environment")

            client = voyageai.Client(api_key=api_key)
            default_model = "voyage-2"  # 1536 dim

            class VoyageWrapper:
                def __init__(self, client, model):
                    self.client = client
                    self.model = model

                def embed_query(self, text: str) -> list[float]:
                    result = self.client.embed([text], model=self.model)
                    return result.embeddings[0]

                def embed_documents(self, texts: list[str]) -> list[list[float]]:
                    result = self.client.embed(texts, model=self.model)
                    return result.embeddings

            logger.info(f"Initialized Voyage AI: {model_name or default_model}")
            return VoyageWrapper(client, model_name or default_model)

        except ImportError:
            logger.error("voyageai package not installed. Run: pip install voyageai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Voyage AI: {str(e)}")
            raise

    def _init_openai(self, model_name: str | None) -> Any:
        """Initialize OpenAI embeddings"""
        from langchain_openai import OpenAIEmbeddings

        default_model = "text-embedding-3-small"  # 1536 dim

        model = OpenAIEmbeddings(
            model=model_name or default_model,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )

        logger.info(f"Initialized OpenAI: {model_name or default_model}")
        return model

    def _init_cohere(self, model_name: str | None) -> Any:
        """Initialize Cohere embeddings"""
        from langchain_cohere import CohereEmbeddings

        default_model = "embed-english-v3.0"  # 1024 dim

        model = CohereEmbeddings(
            model=model_name or default_model,
            cohere_api_key=os.getenv('COHERE_API_KEY')
        )

        logger.info(f"Initialized Cohere: {model_name or default_model}")
        return model

    def embed_text(self, text: str, cache_key: str | None = None) -> np.ndarray:
        """
        Generate embedding for a single text

        Args:
            text: Text to embed
            cache_key: Optional key for caching (e.g., rule_id)

        Returns:
            Embedding vector as numpy array
        """
        # Check cache first
        if cache_key and self.cache_embeddings and cache_key in self._embedding_cache:
            logger.debug(f"Cache hit for: {cache_key}")
            return self._embedding_cache[cache_key]

        # Generate embedding
        try:
            embedding = self.model.embed_query(text)
            embedding_array = np.array(embedding, dtype=np.float32)

            # Normalize if needed
            if not self._is_normalized(embedding_array):
                embedding_array = self._normalize(embedding_array)

            # Cache if enabled
            if cache_key and self.cache_embeddings:
                self._embedding_cache[cache_key] = embedding_array

            return embedding_array

        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise

    def embed_texts(self, texts: list[str]) -> list[np.ndarray]:
        """
        Generate embeddings for multiple texts (batch processing)

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self.model.embed_documents(texts)
            embedding_arrays = [
                self._normalize(np.array(emb, dtype=np.float32))
                for emb in embeddings
            ]
            return embedding_arrays

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {str(e)}")
            raise

    def embed_rule(self, rule: dict[str, Any]) -> np.ndarray:
        """
        Generate embedding for an SOD rule

        Args:
            rule: SOD rule dictionary

        Returns:
            Embedding vector
        """
        rule_text = self._rule_to_text(rule)
        cache_key = f"rule_{rule.get('rule_id', '')}"
        return self.embed_text(rule_text, cache_key=cache_key)

    def embed_violation(self, violation: dict[str, Any]) -> np.ndarray:
        """
        Generate embedding for a violation

        Args:
            violation: Violation dictionary

        Returns:
            Embedding vector
        """
        violation_text = self._violation_to_text(violation)
        cache_key = f"violation_{violation.get('id', '')}"
        return self.embed_text(violation_text, cache_key=cache_key)

    def embed_exemption(self, exemption: dict[str, Any]) -> np.ndarray:
        """
        Generate embedding for an exemption rationale

        Args:
            exemption: Exemption dictionary

        Returns:
            Embedding vector
        """
        exemption_text = self._exemption_to_text(exemption)
        cache_key = f"exemption_{exemption.get('id', '')}"
        return self.embed_text(exemption_text, cache_key=cache_key)

    def similarity_search(
        self,
        query_embedding: np.ndarray,
        table_name: str,
        top_k: int = 5,
        min_similarity: float = 0.5,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Perform similarity search using pgvector

        Args:
            query_embedding: Query vector
            table_name: Table to search (sod_rules, violations, exemptions)
            top_k: Number of results to return
            min_similarity: Minimum cosine similarity threshold
            filters: Optional filters (e.g., {"severity": "CRITICAL"})

        Returns:
            List of matching records with similarity scores
        """
        if not self.session:
            raise ValueError("Database session required for similarity search")

        # Convert numpy array to list for SQL
        query_vector = query_embedding.tolist()

        # Build filter clause
        filter_clause = ""
        if filters:
            conditions = [f"{k} = :{k}" for k in filters.keys()]
            filter_clause = "WHERE " + " AND ".join(conditions)

        # pgvector cosine similarity query
        # Using <=> operator for cosine distance (1 - similarity)
        query = text(f"""
            SELECT
                *,
                1 - (embedding <=> :query_vector) AS similarity
            FROM {table_name}
            {filter_clause}
            ORDER BY embedding <=> :query_vector
            LIMIT :top_k
        """)

        params = {"query_vector": query_vector, "top_k": top_k, **(filters or {})}

        try:
            result = self.session.execute(query, params)
            results = []

            for row in result:
                row_dict = dict(row._mapping)
                similarity = row_dict.get('similarity', 0)

                if similarity >= min_similarity:
                    results.append(row_dict)

            logger.info(f"Found {len(results)} similar items in {table_name}")
            return results

        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}")
            raise

    def find_similar_rules(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> list[dict[str, Any]]:
        """Find similar SOD rules"""
        query_embedding = self.embed_text(query)
        return self.similarity_search(
            query_embedding,
            "sod_rules",
            top_k=top_k,
            min_similarity=min_similarity
        )

    def find_similar_violations(
        self,
        violation_description: str,
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> list[dict[str, Any]]:
        """Find similar historical violations"""
        query_embedding = self.embed_text(violation_description)
        return self.similarity_search(
            query_embedding,
            "violations",
            top_k=top_k,
            min_similarity=min_similarity
        )

    def find_similar_exemptions(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> list[dict[str, Any]]:
        """Find similar exemption cases"""
        query_embedding = self.embed_text(query)
        return self.similarity_search(
            query_embedding,
            "violation_exemptions",
            top_k=top_k,
            min_similarity=min_similarity
        )

    # Helper methods for text conversion

    def _rule_to_text(self, rule: dict[str, Any]) -> str:
        """Convert rule to rich text for embedding"""
        text_parts = [
            f"Rule: {rule.get('rule_name', '')}",
            f"Type: {rule.get('rule_type', '')}",
            f"Description: {rule.get('description', '')}",
            f"Severity: {rule.get('severity', '')}",
            f"Framework: {rule.get('regulatory_framework', 'INTERNAL')}"
        ]

        # Add conflicting permissions
        conflicts = rule.get('conflicting_permissions', {}).get('conflicts', [])
        if conflicts:
            conflict_text = ", ".join([" and ".join(pair) for pair in conflicts])
            text_parts.append(f"Conflicts: {conflict_text}")

        return " | ".join(text_parts)

    def _violation_to_text(self, violation: dict[str, Any]) -> str:
        """Convert violation to rich text for embedding"""
        text_parts = [
            f"Violation: {violation.get('title', '')}",
            f"Description: {violation.get('description', '')}",
            f"Severity: {violation.get('severity', '')}",
            f"User: {violation.get('user_name', '')}",
            f"Roles: {', '.join(violation.get('conflicting_roles', []))}"
        ]
        return " | ".join(text_parts)

    def _exemption_to_text(self, exemption: dict[str, Any]) -> str:
        """Convert exemption to rich text for embedding"""
        text_parts = [
            f"Exemption Reason: {exemption.get('reason', '')}",
            f"Rationale: {exemption.get('rationale', '')}",
            f"Business Justification: {exemption.get('business_justification', '')}",
            f"Compensating Controls: {exemption.get('compensating_controls', '')}"
        ]
        return " | ".join(text_parts)

    def _normalize(self, vector: np.ndarray) -> np.ndarray:
        """Normalize vector to unit length"""
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm

    def _is_normalized(self, vector: np.ndarray, tolerance: float = 0.01) -> bool:
        """Check if vector is normalized"""
        norm = np.linalg.norm(vector)
        return abs(norm - 1.0) < tolerance

    def clear_cache(self):
        """Clear embedding cache"""
        self._embedding_cache.clear()
        logger.info("Embedding cache cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self._embedding_cache),
            "cache_enabled": self.cache_embeddings,
            "provider": self.provider.value,
            "dimension": self.dimension
        }


# Factory function
def create_embedding_service(
    provider: str = None,
    session: Session | None = None
) -> EmbeddingService:
    """
    Create a configured Embedding Service instance

    Args:
        provider: Override provider from env (huggingface, voyage, openai, cohere)
        session: SQLAlchemy session for database operations

    Returns:
        Configured EmbeddingService instance
    """
    # Get provider from environment or use default
    provider = provider or os.getenv('EMBEDDING_PROVIDER', 'huggingface')

    # Set dimension based on provider
    dimension_map = {
        'huggingface': 384,  # all-MiniLM-L6-v2
        'voyage': 1536,      # voyage-2
        'openai': 1536,      # text-embedding-3-small
        'cohere': 1024       # embed-english-v3.0
    }

    dimension = dimension_map.get(provider.lower(), 384)

    return EmbeddingService(
        provider=provider,
        dimension=dimension,
        cache_embeddings=True,
        session=session
    )
