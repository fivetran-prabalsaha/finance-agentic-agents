"""
Violation Embedder - Step 8 Implementation: Embed violations after detection

This utility:
1. Generates embeddings for new violations
2. Backfills embeddings for existing violations
3. Enables historical violation similarity search
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from models.database import Violation
from repositories.violation_repository import ViolationRepository
from services.embedding_service import create_embedding_service

logger = logging.getLogger(__name__)


class ViolationEmbedder:
    """Handles embedding generation for violations"""

    def __init__(
        self,
        session: Session,
        violation_repo: ViolationRepository,
        embedding_provider: str = "huggingface"
    ):
        """
        Initialize Violation Embedder

        Args:
            session: SQLAlchemy database session
            violation_repo: Violation repository
            embedding_provider: Embedding provider to use
        """
        self.session = session
        self.violation_repo = violation_repo
        self.embedding_service = create_embedding_service(
            provider=embedding_provider,
            session=session
        )

        logger.info(f"Violation Embedder initialized with {embedding_provider}")

    def embed_violation(self, violation: Violation) -> bool:
        """
        Generate and store embedding for a single violation

        Args:
            violation: Violation object

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create rich text representation
            violation_dict = {
                'id': str(violation.id),
                'title': violation.title,
                'description': violation.description,
                'severity': violation.severity.value,
                'user_name': violation.user.name if violation.user else 'Unknown',
                'conflicting_roles': violation.conflicting_roles or []
            }

            # Generate embedding
            embedding = self.embedding_service.embed_violation(violation_dict)

            # Store embedding
            self.violation_repo.update_embedding(
                violation_id=str(violation.id),
                embedding=embedding.tolist()
            )

            logger.debug(f"Embedded violation: {violation.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to embed violation {violation.id}: {str(e)}")
            return False

    def embed_violations_batch(
        self,
        violations: list[Violation],
        batch_size: int = 10
    ) -> dict[str, int]:
        """
        Embed multiple violations in batches

        Args:
            violations: List of Violation objects
            batch_size: Number of violations to process at once

        Returns:
            Dictionary with success/failure counts
        """
        stats = {'success': 0, 'failed': 0, 'total': len(violations)}

        logger.info(f"Embedding {len(violations)} violations in batches of {batch_size}")

        for i in range(0, len(violations), batch_size):
            batch = violations[i:i + batch_size]

            for violation in batch:
                if self.embed_violation(violation):
                    stats['success'] += 1
                else:
                    stats['failed'] += 1

            # Commit after each batch
            self.session.commit()

            logger.info(
                f"Progress: {stats['success']}/{stats['total']} "
                f"({stats['success'] / stats['total'] * 100:.1f}%)"
            )

        logger.info(
            f"Embedding complete: {stats['success']} succeeded, "
            f"{stats['failed']} failed out of {stats['total']} total"
        )

        return stats

    def backfill_embeddings(self, batch_size: int = 100) -> dict[str, int]:
        """
        Backfill embeddings for violations that don't have them

        Args:
            batch_size: Number of violations to process in each batch

        Returns:
            Dictionary with statistics
        """
        logger.info("Starting embedding backfill for violations")

        total_stats = {'success': 0, 'failed': 0, 'total': 0}

        while True:
            # Get violations without embeddings
            violations = self.violation_repo.get_violations_without_embeddings(
                limit=batch_size
            )

            if not violations:
                logger.info("No more violations to backfill")
                break

            total_stats['total'] += len(violations)

            # Process batch
            batch_stats = self.embed_violations_batch(violations, batch_size=10)

            total_stats['success'] += batch_stats['success']
            total_stats['failed'] += batch_stats['failed']

        logger.info(
            f"Backfill complete: {total_stats['success']} succeeded, "
            f"{total_stats['failed']} failed out of {total_stats['total']} total"
        )

        return total_stats

    def embed_new_violation(self, violation_data: dict[str, Any]) -> dict[str, Any]:
        """
        Generate embedding for new violation data (before creating in DB)

        This is the preferred method for integrating with the analyzer agent.

        Args:
            violation_data: Dictionary with violation fields

        Returns:
            Updated violation_data with 'embedding' field added
        """
        try:
            # Generate embedding
            embedding = self.embedding_service.embed_violation(violation_data)

            # Add to violation data
            violation_data['embedding'] = embedding.tolist()

            logger.debug("Generated embedding for new violation")
            return violation_data

        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            # Return without embedding (violation will be created without it)
            return violation_data


def embed_violations_for_scan(
    session: Session,
    scan_id: str,
    embedding_provider: str = "huggingface"
) -> dict[str, int]:
    """
    Embed all violations from a specific scan

    Args:
        session: SQLAlchemy session
        scan_id: ComplianceScan UUID
        embedding_provider: Embedding provider to use

    Returns:
        Dictionary with statistics
    """
    violation_repo = ViolationRepository(session)
    embedder = ViolationEmbedder(
        session=session,
        violation_repo=violation_repo,
        embedding_provider=embedding_provider
    )

    # Get violations from scan
    violations = violation_repo.get_violations_by_scan(scan_id)

    # Filter out those that already have embeddings
    violations_to_embed = [v for v in violations if v.embedding is None]

    logger.info(
        f"Embedding {len(violations_to_embed)} violations from scan {scan_id} "
        f"({len(violations)} total, {len(violations) - len(violations_to_embed)} already embedded)"
    )

    # Embed them
    stats = embedder.embed_violations_batch(violations_to_embed)

    return stats


# Factory function
def create_violation_embedder(
    session: Session,
    violation_repo: ViolationRepository | None = None,
    embedding_provider: str = "huggingface"
) -> ViolationEmbedder:
    """Create a configured ViolationEmbedder instance"""
    if violation_repo is None:
        violation_repo = ViolationRepository(session)

    return ViolationEmbedder(
        session=session,
        violation_repo=violation_repo,
        embedding_provider=embedding_provider
    )
