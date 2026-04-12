"""
Knowledge Base Agent with pgvector - Enhanced version using PostgreSQL vector storage

This agent replaces in-memory embeddings with pgvector persistence for:
1. Rule embeddings stored in database
2. Persistent similarity search
3. Phase 3 learning from exemptions
4. Production-ready performance
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from repositories.exemption_repository import ExemptionRepository
from repositories.sod_rule_repository import SODRuleRepository
from services.embedding_service import create_embedding_service
from services.llm import LLMMessage, get_llm_from_config
from utils.vector_search import DistanceMetric, create_vector_searcher

logger = logging.getLogger(__name__)


class KnowledgeBaseAgentPgvector:
    """Enhanced Knowledge Base Agent using pgvector for embeddings"""

    def __init__(
        self,
        session: Session,
        sod_rule_repo: SODRuleRepository,
        exemption_repo: ExemptionRepository | None = None,
        sod_rules_path: str | None = None,
        embedding_provider: str = "huggingface"
    ):
        """
        Initialize Knowledge Base Agent with pgvector

        Args:
            session: SQLAlchemy database session
            sod_rule_repo: SOD rule repository
            exemption_repo: Exemption repository (for Phase 3)
            sod_rules_path: Path to SOD rules JSON file
            embedding_provider: Embedding provider (huggingface, voyage, openai)
        """
        self.session = session
        self.sod_rule_repo = sod_rule_repo
        self.exemption_repo = exemption_repo

        # Initialize embedding service
        self.embedding_service = create_embedding_service(
            provider=embedding_provider,
            session=session
        )

        # Initialize vector searcher
        self.vector_searcher = create_vector_searcher(
            session=session,
            metric=DistanceMetric.COSINE,
            min_similarity=0.3
        )

        # Initialize LLM for explanations
        try:
            self.llm = get_llm_from_config()
            self.ai_enabled = True
        except Exception as e:
            logger.warning(f"AI explanations disabled: {str(e)}")
            self.llm = None
            self.ai_enabled = False

        # Load and index rules if path provided
        if sod_rules_path:
            self.initialize_rules_from_json(sod_rules_path)

        logger.info("Knowledge Base Agent (pgvector) initialized")

    def initialize_rules_from_json(self, rules_path: str) -> int:
        """
        Load SOD rules from JSON and store embeddings in pgvector

        Args:
            rules_path: Path to SOD rules JSON file

        Returns:
            Number of rules processed
        """
        logger.info(f"Loading SOD rules from: {rules_path}")

        try:
            with open(rules_path) as f:
                rules = json.load(f)

            count = 0
            for rule_data in rules:
                # Check if rule already exists
                existing_rule = self.sod_rule_repo.get_rule_by_id(
                    rule_data['rule_id']
                )

                if existing_rule and existing_rule.embedding is not None:
                    logger.debug(f"Rule {rule_data['rule_id']} already has embedding")
                    continue

                # Generate embedding
                embedding = self.embedding_service.embed_rule(rule_data)

                if existing_rule:
                    # Update existing rule with embedding
                    existing_rule.embedding = embedding.tolist()
                    self.session.commit()
                else:
                    # Create new rule with embedding
                    self.sod_rule_repo.create_rule(
                        rule_id=rule_data['rule_id'],
                        rule_name=rule_data['rule_name'],
                        category=rule_data.get('rule_type', 'GENERAL'),
                        description=rule_data['description'],
                        conflicting_permissions=rule_data.get('conflicting_permissions'),
                        severity=rule_data.get('severity', 'MEDIUM'),
                        embedding=embedding.tolist()
                    )

                count += 1

            logger.info(f"Processed {count} SOD rules with embeddings")
            return count

        except Exception as e:
            logger.error(f"Failed to load SOD rules: {str(e)}")
            raise

    def search_similar_rules(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> list[dict[str, Any]]:
        """
        Find SOD rules similar to a query using pgvector

        Args:
            query: Search query
            top_k: Number of results
            min_similarity: Minimum similarity threshold

        Returns:
            List of similar rules with similarity scores
        """
        logger.info(f"Searching for rules similar to: '{query}'")

        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)

        # Search using pgvector
        results = self.vector_searcher.search(
            query_vector=query_embedding.tolist(),
            table_name="sod_rules",
            embedding_column="embedding",
            top_k=top_k,
            filters={"is_active": True}
        )

        # Filter by minimum similarity
        filtered_results = [
            r for r in results
            if r.get('similarity', 0) >= min_similarity
        ]

        logger.info(f"Found {len(filtered_results)} similar rules")
        return filtered_results

    def find_rules_for_permissions(
        self,
        permissions: list[str]
    ) -> list[dict[str, Any]]:
        """
        Find SOD rules that might be violated by a set of permissions

        Args:
            permissions: List of permission names

        Returns:
            List of potentially applicable rules
        """
        logger.info(f"Finding rules for {len(permissions)} permissions")

        # Get all active rules
        all_rules = self.sod_rule_repo.get_active_rules()
        applicable_rules = []

        for rule in all_rules:
            conflicts = rule.conflicting_permissions.get('conflicts', []) if rule.conflicting_permissions else []

            for conflict_pair in conflicts:
                # Check if user has permissions matching both sides of conflict
                matches = []
                for conflict_perm in conflict_pair:
                    if any(conflict_perm.lower() in p.lower() for p in permissions):
                        matches.append(conflict_perm)

                # If both sides of conflict match, this rule applies
                if len(matches) == len(conflict_pair):
                    applicable_rules.append({
                        'rule': rule,
                        'matched_permissions': matches,
                        'rule_id': rule.rule_id
                    })
                    break

        logger.info(f"Found {len(applicable_rules)} applicable rules")
        return applicable_rules

    def find_similar_violations(
        self,
        violation_description: str,
        top_k: int = 3
    ) -> list[dict[str, Any]]:
        """
        Find similar historical violations using pgvector (Step 8 feature)

        Args:
            violation_description: Description of a violation
            top_k: Number of similar violations to return

        Returns:
            List of similar violations
        """
        logger.info("Finding similar violations using pgvector")

        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(violation_description)

        # Search violations table
        results = self.vector_searcher.search(
            query_vector=query_embedding.tolist(),
            table_name="violations",
            embedding_column="embedding",
            top_k=top_k
        )

        return results

    def find_similar_exemptions(
        self,
        query: str,
        top_k: int = 3
    ) -> list[dict[str, Any]]:
        """
        Find similar approved exemptions (Phase 3: Learning from history)

        Args:
            query: Query describing the scenario
            top_k: Number of similar exemptions

        Returns:
            List of similar exemption cases
        """
        if not self.exemption_repo:
            logger.warning("Exemption repository not available")
            return []

        logger.info("Finding similar exemptions (Phase 3)")

        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)

        # Search exemptions table (only approved)
        results = self.vector_searcher.search(
            query_vector=query_embedding.tolist(),
            table_name="violation_exemptions",
            embedding_column="embedding",
            top_k=top_k,
            filters={"status": "APPROVED"}
        )

        return results

    def get_contextual_knowledge(
        self,
        violation_description: str,
        user_context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Get contextual knowledge combining rules, historical violations, and exemptions

        This is the "Phase 3 Ground Truth" - combining all learned knowledge

        Args:
            violation_description: Description of current violation
            user_context: User context (job function, department, etc.)

        Returns:
            Dictionary with relevant context from all sources
        """
        logger.info("Gathering contextual knowledge (Phase 1-3 combined)")

        context = {
            'similar_rules': [],
            'similar_violations': [],
            'similar_exemptions': [],
            'timestamp': datetime.utcnow().isoformat()
        }

        # 1. Find similar rules (Phase 1: Ground Truth)
        context['similar_rules'] = self.search_similar_rules(
            query=violation_description,
            top_k=3,
            min_similarity=0.4
        )

        # 2. Find similar historical violations (Phase 2: Step 8)
        context['similar_violations'] = self.find_similar_violations(
            violation_description=violation_description,
            top_k=3
        )

        # 3. Find similar approved exemptions (Phase 3: Learning)
        context['similar_exemptions'] = self.find_similar_exemptions(
            query=f"{violation_description} {user_context.get('job_function', '')}",
            top_k=3
        )

        return context

    def explain_rule_with_ai(self, rule_id: str) -> dict[str, Any]:
        """
        Use LLM to provide detailed explanation of a rule

        Args:
            rule_id: Rule ID to explain

        Returns:
            AI-generated explanation
        """
        if not self.ai_enabled:
            return {
                'success': False,
                'error': 'AI explanations not available'
            }

        rule = self.sod_rule_repo.get_rule_by_id(rule_id)
        if not rule:
            return {
                'success': False,
                'error': f"Rule {rule_id} not found"
            }

        logger.info(f"Generating AI explanation for rule: {rule_id}")

        system_message = """You are a compliance expert explaining SOD (Segregation of Duties) rules.
Provide clear, practical explanations that help both technical and non-technical audiences understand:
1. What the rule prevents
2. Why it matters (risk/impact)
3. Real-world scenarios where violations occur
4. Best practices for compliance
5. Common exceptions or compensating controls

Be concise but thorough."""

        user_message = f"""Explain this SOD rule:

Rule ID: {rule.rule_id}
Rule Name: {rule.rule_name}
Type: {rule.category}
Description: {rule.description}

Provide explanation in this format:
- What it prevents: [explanation]
- Why it matters: [risk and impact]
- Real-world scenario: [example]
- Compliance approach: [best practices]
- Exceptions: [when compensating controls might be acceptable]"""

        try:
            messages = [
                LLMMessage(role="system", content=system_message),
                LLMMessage(role="user", content=user_message)
            ]

            response = self.llm.generate(messages)

            return {
                'success': True,
                'rule_id': rule_id,
                'explanation': response.content,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_knowledge_base_stats(self) -> dict[str, Any]:
        """Get statistics about the knowledge base"""
        stats = {
            'total_rules': 0,
            'rules_with_embeddings': 0,
            'total_violations_embedded': 0,
            'total_exemptions': 0,
            'embedding_provider': self.embedding_service.provider.value,
            'embedding_dimension': self.embedding_service.dimension
        }

        # Count rules
        result = self.session.execute(text("SELECT COUNT(*) FROM sod_rules"))
        stats['total_rules'] = result.scalar()

        result = self.session.execute(text("SELECT COUNT(*) FROM sod_rules WHERE embedding IS NOT NULL"))
        stats['rules_with_embeddings'] = result.scalar()

        # Count violations with embeddings
        result = self.session.execute(text("SELECT COUNT(*) FROM violations WHERE embedding IS NOT NULL"))
        stats['total_violations_embedded'] = result.scalar()

        # Count exemptions
        if self.exemption_repo:
            result = self.session.execute(text("SELECT COUNT(*) FROM violation_exemptions"))
            stats['total_exemptions'] = result.scalar()

        return stats


# Factory function
def create_knowledge_base(
    session: Session,
    sod_rule_repo: SODRuleRepository,
    exemption_repo: ExemptionRepository | None = None,
    sod_rules_path: str | None = None
) -> KnowledgeBaseAgentPgvector:
    """Create a configured Knowledge Base Agent with pgvector"""
    if sod_rules_path is None:
        sod_rules_path = str(Path(__file__).parent.parent / "database" / "seed_data" / "sod_rules.json")

    return KnowledgeBaseAgentPgvector(
        session=session,
        sod_rule_repo=sod_rule_repo,
        exemption_repo=exemption_repo,
        sod_rules_path=sod_rules_path
    )
