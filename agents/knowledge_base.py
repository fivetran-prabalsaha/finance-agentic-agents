"""
Knowledge Base Agent - Manages SOD rules with vector embeddings

This agent is responsible for:
1. Loading and managing SOD rules
2. Creating vector embeddings for semantic search
3. Finding similar violations
4. Recommending relevant rules
5. Rule matching and retrieval
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from langchain_anthropic import ChatAnthropic

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    # Fallback to old import for backward compatibility
    from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate

from repositories.role_repository import RoleRepository

logger = logging.getLogger(__name__)


class KnowledgeBaseAgent:
    """Agent for managing SOD rules knowledge base with semantic search"""

    def __init__(
        self,
        role_repo: RoleRepository,
        sod_rules_path: str | None = None,
        llm_model: str = "claude-sonnet-4.5-20250929",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize Knowledge Base Agent

        Args:
            role_repo: Role repository instance
            sod_rules_path: Path to SOD rules JSON file
            llm_model: Claude model for intelligent queries
            embedding_model: HuggingFace model for embeddings
        """
        self.role_repo = role_repo
        self.llm = ChatAnthropic(model=llm_model, temperature=0)

        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

        # Load SOD rules
        if sod_rules_path is None:
            sod_rules_path = Path(__file__).parent.parent / "database" / "seed_data" / "sod_rules.json"

        self.sod_rules = self._load_sod_rules(sod_rules_path)
        self.rule_embeddings = self._create_rule_embeddings()

        logger.info(f"Knowledge Base Agent initialized with {len(self.sod_rules)} rules")
        logger.info(f"Created {len(self.rule_embeddings)} rule embeddings")

    def _load_sod_rules(self, rules_path: str) -> list[dict[str, Any]]:
        """Load SOD rules from JSON file"""
        try:
            with open(rules_path) as f:
                rules = json.load(f)
            logger.info(f"Loaded {len(rules)} SOD rules from {rules_path}")
            return rules
        except Exception as e:
            logger.error(f"Failed to load SOD rules: {str(e)}")
            return []

    def _create_rule_embeddings(self) -> dict[str, np.ndarray]:
        """
        Create vector embeddings for all SOD rules

        Returns:
            Dictionary mapping rule_id to embedding vector
        """
        rule_embeddings = {}

        for rule in self.sod_rules:
            # Create rich text representation of rule
            rule_text = self._rule_to_text(rule)

            # Generate embedding
            embedding = self.embeddings.embed_query(rule_text)

            rule_embeddings[rule['rule_id']] = np.array(embedding)

        logger.info(f"Created embeddings for {len(rule_embeddings)} rules")
        return rule_embeddings

    def _rule_to_text(self, rule: dict[str, Any]) -> str:
        """
        Convert rule to rich text representation for embedding

        Args:
            rule: SOD rule dictionary

        Returns:
            Text representation of rule
        """
        text_parts = [
            f"Rule: {rule['rule_name']}",
            f"Type: {rule['rule_type']}",
            f"Description: {rule['description']}",
            f"Severity: {rule['severity']}",
            f"Framework: {rule.get('regulatory_framework', 'INTERNAL')}"
        ]

        # Add conflicting permissions
        conflicts = rule.get('conflicting_permissions', {}).get('conflicts', [])
        if conflicts:
            conflict_text = ", ".join([" and ".join(pair) for pair in conflicts])
            text_parts.append(f"Conflicts: {conflict_text}")

        return " | ".join(text_parts)

    def search_similar_rules(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> list[dict[str, Any]]:
        """
        Find SOD rules similar to a query using semantic search

        Args:
            query: Search query (e.g., "financial approval conflicts")
            top_k: Number of results to return
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of similar rules with similarity scores
        """
        logger.info(f"Searching for rules similar to: '{query}'")

        # Generate query embedding
        query_embedding = np.array(self.embeddings.embed_query(query))

        # Calculate similarities
        similarities = []
        for rule in self.sod_rules:
            rule_id = rule['rule_id']
            rule_embedding = self.rule_embeddings[rule_id]

            # Cosine similarity
            similarity = np.dot(query_embedding, rule_embedding)

            if similarity >= min_similarity:
                similarities.append({
                    'rule': rule,
                    'similarity': float(similarity),
                    'rule_id': rule_id
                })

        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)

        results = similarities[:top_k]
        logger.info(f"Found {len(results)} similar rules")

        return results

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

        applicable_rules = []

        for rule in self.sod_rules:
            conflicts = rule.get('conflicting_permissions', {}).get('conflicts', [])

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
                        'rule_id': rule['rule_id']
                    })
                    break

        logger.info(f"Found {len(applicable_rules)} applicable rules")
        return applicable_rules

    def get_rules_by_type(self, rule_type: str) -> list[dict[str, Any]]:
        """
        Get all rules of a specific type

        Args:
            rule_type: FINANCIAL, IT_ACCESS, PROCUREMENT, COMPLIANCE, SALES

        Returns:
            List of rules matching the type
        """
        rules = [r for r in self.sod_rules if r['rule_type'] == rule_type]
        logger.info(f"Found {len(rules)} rules of type {rule_type}")
        return rules

    def get_rules_by_severity(self, severity: str) -> list[dict[str, Any]]:
        """
        Get all rules of a specific severity

        Args:
            severity: CRITICAL, HIGH, MEDIUM, LOW

        Returns:
            List of rules matching the severity
        """
        rules = [r for r in self.sod_rules if r['severity'] == severity]
        logger.info(f"Found {len(rules)} rules with severity {severity}")
        return rules

    def get_rule_by_id(self, rule_id: str) -> dict[str, Any] | None:
        """
        Get a specific rule by ID

        Args:
            rule_id: Rule ID (e.g., SOD-FIN-001)

        Returns:
            Rule dictionary or None
        """
        for rule in self.sod_rules:
            if rule['rule_id'] == rule_id:
                return rule
        return None

    def explain_rule_with_ai(self, rule_id: str) -> dict[str, Any]:
        """
        Use Claude to provide detailed explanation of a rule

        Args:
            rule_id: Rule ID to explain

        Returns:
            AI-generated explanation with context and examples
        """
        rule = self.get_rule_by_id(rule_id)
        if not rule:
            return {
                'success': False,
                'error': f"Rule {rule_id} not found"
            }

        logger.info(f"Generating AI explanation for rule: {rule_id}")

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a compliance expert explaining SOD (Segregation of Duties) rules.
Provide clear, practical explanations that help both technical and non-technical audiences understand:
1. What the rule prevents
2. Why it matters (risk/impact)
3. Real-world scenarios where violations occur
4. Best practices for compliance
5. Common exceptions or compensating controls

Be concise but thorough."""),
            ("user", """Explain this SOD rule:

Rule ID: {rule_id}
Rule Name: {rule_name}
Type: {rule_type}
Severity: {severity}
Description: {description}
Regulatory Framework: {framework}
Remediation: {remediation}

Provide explanation in this format:
- What it prevents: [explanation]
- Why it matters: [risk and impact]
- Real-world scenario: [example]
- Compliance approach: [best practices]
- Exceptions: [when compensating controls might be acceptable]""")
        ])

        chain = prompt | self.llm

        try:
            explanation = chain.invoke({
                "rule_id": rule['rule_id'],
                "rule_name": rule['rule_name'],
                "rule_type": rule['rule_type'],
                "severity": rule['severity'],
                "description": rule['description'],
                "framework": rule.get('regulatory_framework', 'INTERNAL'),
                "remediation": rule.get('remediation_guidance', 'N/A')
            })

            return {
                'success': True,
                'rule_id': rule_id,
                'explanation': explanation.content,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def find_similar_violations(
        self,
        violation_description: str,
        top_k: int = 3
    ) -> list[dict[str, Any]]:
        """
        Find similar violations based on description using semantic search

        Args:
            violation_description: Description of a violation
            top_k: Number of similar rules to return

        Returns:
            List of similar rules that might apply
        """
        logger.info("Finding similar violations using semantic search")

        # Search for similar rules
        similar_rules = self.search_similar_rules(
            query=violation_description,
            top_k=top_k,
            min_similarity=0.3
        )

        return similar_rules

    def recommend_rules_for_role_combination(
        self,
        role_names: list[str]
    ) -> dict[str, Any]:
        """
        Recommend which SOD rules to check for a role combination

        Args:
            role_names: List of role names

        Returns:
            Dictionary with recommended rules and reasoning
        """
        logger.info(f"Recommending rules for role combination: {role_names}")

        # Create query from role names
        query = f"User has roles: {', '.join(role_names)}. What SOD rules might be violated?"

        # Search for relevant rules
        relevant_rules = self.search_similar_rules(
            query=query,
            top_k=10,
            min_similarity=0.3
        )

        # Check for admin + business role pattern
        has_admin = any('admin' in role.lower() for role in role_names)
        has_business = any(
            term in ' '.join(role_names).lower()
            for term in ['clerk', 'representative', 'finance', 'accounting']
        )

        recommendations = {
            'high_priority': [],
            'medium_priority': [],
            'low_priority': []
        }

        if has_admin and has_business:
            # Add IT_ACCESS rules
            it_rules = [r for r in relevant_rules if r['rule']['rule_type'] == 'IT_ACCESS']
            recommendations['high_priority'].extend(it_rules)

        # Categorize by severity and similarity
        for item in relevant_rules:
            rule = item['rule']
            similarity = item['similarity']

            if rule['severity'] == 'CRITICAL' and similarity > 0.5:
                recommendations['high_priority'].append(item)
            elif rule['severity'] in ['CRITICAL', 'HIGH'] and similarity > 0.4:
                recommendations['medium_priority'].append(item)
            else:
                recommendations['low_priority'].append(item)

        # Remove duplicates
        recommendations['high_priority'] = list({r['rule_id']: r for r in recommendations['high_priority']}.values())
        recommendations['medium_priority'] = list({r['rule_id']: r for r in recommendations['medium_priority']}.values())
        recommendations['low_priority'] = list({r['rule_id']: r for r in recommendations['low_priority']}.values())

        logger.info(
            f"Recommendations: {len(recommendations['high_priority'])} high, "
            f"{len(recommendations['medium_priority'])} medium, "
            f"{len(recommendations['low_priority'])} low priority"
        )

        return {
            'success': True,
            'role_names': role_names,
            'recommendations': recommendations,
            'total_rules': (
                len(recommendations['high_priority']) +
                len(recommendations['medium_priority']) +
                len(recommendations['low_priority'])
            ),
            'timestamp': datetime.now().isoformat()
        }

    def get_knowledge_base_stats(self) -> dict[str, Any]:
        """
        Get statistics about the knowledge base

        Returns:
            Statistics dictionary
        """
        rule_types = {}
        severities = {}
        frameworks = {}

        for rule in self.sod_rules:
            # Count by type
            rule_type = rule['rule_type']
            rule_types[rule_type] = rule_types.get(rule_type, 0) + 1

            # Count by severity
            severity = rule['severity']
            severities[severity] = severities.get(severity, 0) + 1

            # Count by framework
            framework = rule.get('regulatory_framework', 'INTERNAL')
            frameworks[framework] = frameworks.get(framework, 0) + 1

        return {
            'total_rules': len(self.sod_rules),
            'rules_by_type': rule_types,
            'rules_by_severity': severities,
            'rules_by_framework': frameworks,
            'embedding_dimension': len(list(self.rule_embeddings.values())[0]) if self.rule_embeddings else 0,
            'embedding_model': self.embeddings.model_name
        }


# Factory function
def create_knowledge_base(role_repo: RoleRepository) -> KnowledgeBaseAgent:
    """Create a configured Knowledge Base Agent instance"""
    return KnowledgeBaseAgent(role_repo=role_repo)
