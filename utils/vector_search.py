"""
Vector Search Utilities - Helper functions for pgvector similarity search

Provides utilities for:
1. Similarity search with various distance metrics
2. Query builders for pgvector operations
3. Result formatting and ranking
4. Performance optimizations
"""

import logging
from enum import Enum
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DistanceMetric(Enum):
    """Supported distance metrics for vector similarity"""
    COSINE = "cosine"          # <=> operator (1 - cosine similarity)
    L2 = "l2"                  # <-> operator (Euclidean distance)
    INNER_PRODUCT = "inner"    # <#> operator (negative inner product)


class VectorSearchConfig:
    """Configuration for vector search operations"""

    def __init__(
        self,
        metric: DistanceMetric = DistanceMetric.COSINE,
        min_similarity: float = 0.5,
        max_distance: float | None = None,
        enable_explain: bool = False
    ):
        """
        Initialize search configuration

        Args:
            metric: Distance metric to use
            min_similarity: Minimum similarity threshold (for cosine)
            max_distance: Maximum distance threshold (for L2)
            enable_explain: Whether to run EXPLAIN on queries
        """
        self.metric = metric
        self.min_similarity = min_similarity
        self.max_distance = max_distance
        self.enable_explain = enable_explain


def get_distance_operator(metric: DistanceMetric) -> str:
    """Get pgvector operator for distance metric"""
    operators = {
        DistanceMetric.COSINE: "<=>",
        DistanceMetric.L2: "<->",
        DistanceMetric.INNER_PRODUCT: "<#>"
    }
    return operators[metric]


def cosine_to_similarity(distance: float) -> float:
    """Convert cosine distance to similarity score (0-1)"""
    return 1 - distance


def similarity_to_cosine(similarity: float) -> float:
    """Convert similarity score to cosine distance"""
    return 1 - similarity


def normalize_vector(vector: list[float]) -> list[float]:
    """Normalize vector to unit length"""
    arr = np.array(vector, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return vector
    normalized = arr / norm
    return normalized.tolist()


class VectorSearcher:
    """Utility class for performing vector similarity searches"""

    def __init__(
        self,
        session: Session,
        config: VectorSearchConfig | None = None
    ):
        """
        Initialize Vector Searcher

        Args:
            session: SQLAlchemy database session
            config: Search configuration
        """
        self.session = session
        self.config = config or VectorSearchConfig()

    def search(
        self,
        query_vector: list[float],
        table_name: str,
        embedding_column: str = "embedding",
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        select_columns: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Perform similarity search

        Args:
            query_vector: Query embedding
            table_name: Table to search
            embedding_column: Name of embedding column
            top_k: Number of results to return
            filters: Optional filters (e.g., {"status": "ACTIVE"})
            select_columns: Columns to return (None = all)

        Returns:
            List of matching records with similarity/distance scores
        """
        operator = get_distance_operator(self.config.metric)

        # Build column selection
        if select_columns:
            columns_str = ", ".join(select_columns)
        else:
            columns_str = "*"

        # Build distance/similarity expression
        # Use CAST instead of :: to avoid SQLAlchemy parameter parsing issues
        query_vec_cast = "CAST(:query_vector AS vector)"
        if self.config.metric == DistanceMetric.COSINE:
            score_expr = f"1 - ({embedding_column} {operator} {query_vec_cast}) AS similarity"
            order_by = f"{embedding_column} {operator} {query_vec_cast}"
        else:
            score_expr = f"{embedding_column} {operator} {query_vec_cast} AS distance"
            order_by = f"{embedding_column} {operator} {query_vec_cast}"

        # Build filter clause
        filter_clause = ""
        if filters:
            conditions = [f"{k} = :{k}" for k in filters.keys()]
            filter_clause = "WHERE " + " AND ".join(conditions)

            # Add similarity/distance threshold
            query_vec_cast = "CAST(:query_vector AS vector)"
            if self.config.metric == DistanceMetric.COSINE and self.config.min_similarity:
                filter_clause += f" AND (1 - ({embedding_column} {operator} {query_vec_cast})) >= :min_similarity"
            elif self.config.max_distance:
                filter_clause += f" AND ({embedding_column} {operator} {query_vec_cast}) <= :max_distance"
        else:
            query_vec_cast = "CAST(:query_vector AS vector)"
            if self.config.metric == DistanceMetric.COSINE and self.config.min_similarity:
                filter_clause = f"WHERE (1 - ({embedding_column} {operator} {query_vec_cast})) >= :min_similarity"
            elif self.config.max_distance:
                filter_clause = f"WHERE ({embedding_column} {operator} {query_vec_cast}) <= :max_distance"

        # Build query
        query_sql = f"""
            SELECT
                {columns_str},
                {score_expr}
            FROM {table_name}
            {filter_clause}
            ORDER BY {order_by}
            LIMIT :top_k
        """

        # Prepare parameters
        params = {
            "query_vector": query_vector,
            "top_k": top_k,
            **(filters or {})
        }

        if self.config.metric == DistanceMetric.COSINE and self.config.min_similarity:
            params["min_similarity"] = self.config.min_similarity
        elif self.config.max_distance:
            params["max_distance"] = self.config.max_distance

        try:
            # Execute query
            if self.config.enable_explain:
                explain_query = f"EXPLAIN ANALYZE {query_sql}"
                explain_result = self.session.execute(text(explain_query), params)
                logger.debug("Query plan:\n" + "\n".join([row[0] for row in explain_result]))

            result = self.session.execute(text(query_sql), params)
            results = []

            for row in result:
                row_dict = dict(row._mapping)
                results.append(row_dict)

            logger.info(f"Found {len(results)} similar items in {table_name}")
            return results

        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise

    def batch_search(
        self,
        query_vectors: list[list[float]],
        table_name: str,
        embedding_column: str = "embedding",
        top_k: int = 5,
        filters: dict[str, Any] | None = None
    ) -> list[list[dict[str, Any]]]:
        """
        Perform batch similarity search for multiple query vectors

        Args:
            query_vectors: List of query embeddings
            table_name: Table to search
            embedding_column: Name of embedding column
            top_k: Number of results per query
            filters: Optional filters

        Returns:
            List of result lists (one per query vector)
        """
        results = []
        for query_vector in query_vectors:
            result = self.search(
                query_vector=query_vector,
                table_name=table_name,
                embedding_column=embedding_column,
                top_k=top_k,
                filters=filters
            )
            results.append(result)

        return results

    def search_with_reranking(
        self,
        query_vector: list[float],
        table_name: str,
        top_k: int = 5,
        rerank_top_k: int = 20,
        rerank_func: callable | None = None,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Perform similarity search with re-ranking

        First retrieves more results than needed, then applies a
        re-ranking function for more accurate results.

        Args:
            query_vector: Query embedding
            table_name: Table to search
            top_k: Final number of results to return
            rerank_top_k: Number of candidates to retrieve
            rerank_func: Optional custom re-ranking function
            filters: Optional filters

        Returns:
            Re-ranked results
        """
        # Retrieve more candidates
        candidates = self.search(
            query_vector=query_vector,
            table_name=table_name,
            top_k=rerank_top_k,
            filters=filters
        )

        if not rerank_func:
            # Default: just return top_k
            return candidates[:top_k]

        # Apply custom re-ranking
        reranked = rerank_func(query_vector, candidates)
        return reranked[:top_k]

    def hybrid_search(
        self,
        query_vector: list[float],
        text_query: str,
        table_name: str,
        text_columns: list[str],
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
        top_k: int = 5,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Perform hybrid search combining vector similarity and text search

        Args:
            query_vector: Query embedding
            text_query: Text search query
            table_name: Table to search
            text_columns: Columns to search for text
            vector_weight: Weight for vector similarity (0-1)
            text_weight: Weight for text relevance (0-1)
            top_k: Number of results
            filters: Optional filters

        Returns:
            Combined and ranked results
        """
        # Validate weights
        if abs(vector_weight + text_weight - 1.0) > 0.01:
            raise ValueError("vector_weight + text_weight must equal 1.0")

        operator = get_distance_operator(self.config.metric)

        # Build text search conditions
        text_conditions = " OR ".join([
            f"{col} ILIKE :text_query"
            for col in text_columns
        ])

        # Build filter clause
        filter_clause = ""
        if filters:
            conditions = [f"{k} = :{k}" for k in filters.keys()]
            filter_clause = "WHERE " + " AND ".join(conditions)
            filter_clause += f" AND ({text_conditions})"
        else:
            filter_clause = f"WHERE {text_conditions}"

        # Hybrid scoring
        query_sql = f"""
            SELECT
                *,
                (
                    ({vector_weight} * (1 - (embedding {operator} :query_vector))) +
                    ({text_weight} * CASE WHEN {text_conditions} THEN 1 ELSE 0 END)
                ) AS hybrid_score
            FROM {table_name}
            {filter_clause}
            ORDER BY hybrid_score DESC
            LIMIT :top_k
        """

        params = {
            "query_vector": query_vector,
            "text_query": f"%{text_query}%",
            "top_k": top_k,
            **(filters or {})
        }

        try:
            result = self.session.execute(text(query_sql), params)
            results = [dict(row._mapping) for row in result]

            logger.info(f"Hybrid search found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            raise


# Helper Functions

def compute_similarity_matrix(
    vectors: list[list[float]],
    metric: DistanceMetric = DistanceMetric.COSINE
) -> np.ndarray:
    """
    Compute pairwise similarity matrix for a list of vectors

    Args:
        vectors: List of embedding vectors
        metric: Distance metric to use

    Returns:
        NxN similarity matrix
    """
    n = len(vectors)
    matrix = np.zeros((n, n))

    for i in range(n):
        for j in range(i, n):
            if metric == DistanceMetric.COSINE:
                # Cosine similarity
                v1 = np.array(vectors[i])
                v2 = np.array(vectors[j])
                similarity = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            elif metric == DistanceMetric.L2:
                # L2 distance (convert to similarity)
                v1 = np.array(vectors[i])
                v2 = np.array(vectors[j])
                distance = np.linalg.norm(v1 - v2)
                similarity = 1 / (1 + distance)
            else:
                # Inner product
                v1 = np.array(vectors[i])
                v2 = np.array(vectors[j])
                similarity = np.dot(v1, v2)

            matrix[i][j] = similarity
            matrix[j][i] = similarity

    return matrix


def find_duplicates(
    vectors: list[list[float]],
    similarity_threshold: float = 0.95,
    metric: DistanceMetric = DistanceMetric.COSINE
) -> list[tuple[int, int, float]]:
    """
    Find potential duplicate vectors based on high similarity

    Args:
        vectors: List of embedding vectors
        similarity_threshold: Threshold for considering duplicates
        metric: Distance metric to use

    Returns:
        List of (index1, index2, similarity) tuples
    """
    duplicates = []
    matrix = compute_similarity_matrix(vectors, metric)

    n = len(vectors)
    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i][j] >= similarity_threshold:
                duplicates.append((i, j, matrix[i][j]))

    return sorted(duplicates, key=lambda x: x[2], reverse=True)


def cluster_vectors(
    vectors: list[list[float]],
    n_clusters: int = 5
) -> dict[int, list[int]]:
    """
    Perform simple clustering on vectors using K-means

    Args:
        vectors: List of embedding vectors
        n_clusters: Number of clusters

    Returns:
        Dictionary mapping cluster_id to list of vector indices
    """
    try:
        from sklearn.cluster import KMeans

        X = np.array(vectors)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(X)

        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)

        return clusters

    except ImportError:
        logger.warning("scikit-learn not installed. Clustering unavailable.")
        return {}


# Factory function
def create_vector_searcher(
    session: Session,
    metric: DistanceMetric = DistanceMetric.COSINE,
    min_similarity: float = 0.5
) -> VectorSearcher:
    """
    Create a configured VectorSearcher instance

    Args:
        session: SQLAlchemy database session
        metric: Distance metric to use
        min_similarity: Minimum similarity threshold

    Returns:
        Configured VectorSearcher instance
    """
    config = VectorSearchConfig(
        metric=metric,
        min_similarity=min_similarity
    )

    return VectorSearcher(session=session, config=config)
