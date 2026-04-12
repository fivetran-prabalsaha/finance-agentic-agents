"""
SOD Rule Repository - CRUD operations for SOD rules

Handles all database operations for SODRule model
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.database import SODRule, ViolationSeverity

logger = logging.getLogger(__name__)


class SODRuleRepository:
    """Repository for SODRule data access"""

    def __init__(self, session: Session):
        """
        Initialize repository with database session

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def create_rule(self, rule_data: dict[str, Any]) -> SODRule:
        """
        Create a new SOD rule

        Args:
            rule_data: Dictionary with rule fields

        Returns:
            Created SODRule object
        """
        rule = SODRule(
            rule_id=rule_data['rule_id'],
            rule_name=rule_data['rule_name'],
            category=rule_data.get('category', rule_data.get('rule_type')),
            description=rule_data.get('description'),
            conflicting_permissions=rule_data.get('conflicting_permissions', []),
            severity=ViolationSeverity[rule_data.get('severity', 'MEDIUM')],
            is_active=rule_data.get('is_active', True)
        )

        self.session.add(rule)
        self.session.commit()
        self.session.refresh(rule)

        logger.info(f"Created SOD rule: {rule.rule_name}")
        return rule

    def get_rule_by_id(self, rule_id: str) -> SODRule | None:
        """
        Get rule by rule_id (string identifier like "SOD-FIN-001")

        Args:
            rule_id: Rule string ID

        Returns:
            SODRule object or None
        """
        return self.session.query(SODRule).filter(SODRule.rule_id == rule_id).first()

    def get_rule_by_uuid(self, uuid: str) -> SODRule | None:
        """
        Get rule by UUID (database ID)

        Args:
            uuid: Rule UUID

        Returns:
            SODRule object or None
        """
        return self.session.query(SODRule).filter(SODRule.id == uuid).first()

    def get_all_rules(self, active_only: bool = True) -> list[SODRule]:
        """
        Get all SOD rules

        Args:
            active_only: Only return active rules

        Returns:
            List of SODRule objects
        """
        query = self.session.query(SODRule)

        if active_only:
            query = query.filter(SODRule.is_active)

        return query.order_by(SODRule.rule_id).all()

    def upsert_rule(self, rule_data: dict[str, Any]) -> SODRule:
        """
        Create or update an SOD rule

        Args:
            rule_data: Dictionary with rule fields

        Returns:
            SODRule object
        """
        existing = self.get_rule_by_id(rule_data['rule_id'])

        if existing:
            # Update existing rule
            existing.rule_name = rule_data['rule_name']
            existing.category = rule_data.get('category', rule_data.get('rule_type'))
            existing.description = rule_data.get('description')
            existing.conflicting_permissions = rule_data.get('conflicting_permissions', [])
            existing.severity = ViolationSeverity[rule_data.get('severity', 'MEDIUM')]
            existing.is_active = rule_data.get('is_active', True)
            existing.updated_at = datetime.utcnow()

            self.session.commit()
            self.session.refresh(existing)

            logger.info(f"Updated SOD rule: {existing.rule_name}")
            return existing
        else:
            # Create new rule
            return self.create_rule(rule_data)

    def bulk_upsert_rules(self, rules_data: list[dict[str, Any]]) -> int:
        """
        Bulk upsert SOD rules

        Args:
            rules_data: List of rule data dictionaries

        Returns:
            Number of rules processed
        """
        count = 0
        for rule_data in rules_data:
            try:
                self.upsert_rule(rule_data)
                count += 1
            except Exception as e:
                logger.error(f"Error upserting rule {rule_data.get('rule_id')}: {str(e)}")
                self.session.rollback()

        logger.info(f"Bulk upserted {count}/{len(rules_data)} SOD rules")
        return count

    def get_rules_by_category(self, category: str) -> list[SODRule]:
        """
        Get all rules in a specific category

        Args:
            category: Rule category

        Returns:
            List of SODRule objects
        """
        return (
            self.session.query(SODRule)
            .filter(SODRule.category == category)
            .filter(SODRule.is_active)
            .order_by(SODRule.rule_id)
            .all()
        )

    def get_rules_by_severity(self, severity: ViolationSeverity) -> list[SODRule]:
        """
        Get all rules with specific severity

        Args:
            severity: Violation severity

        Returns:
            List of SODRule objects
        """
        return (
            self.session.query(SODRule)
            .filter(SODRule.severity == severity)
            .filter(SODRule.is_active)
            .order_by(SODRule.rule_id)
            .all()
        )

    def deactivate_rule(self, rule_id: str) -> SODRule | None:
        """
        Deactivate a rule

        Args:
            rule_id: Rule string ID

        Returns:
            Updated SODRule object or None
        """
        rule = self.get_rule_by_id(rule_id)

        if not rule:
            logger.error(f"Rule not found: {rule_id}")
            return None

        rule.is_active = False
        rule.updated_at = datetime.utcnow()

        self.session.commit()
        self.session.refresh(rule)

        logger.info(f"Deactivated SOD rule: {rule_id}")
        return rule

    def activate_rule(self, rule_id: str) -> SODRule | None:
        """
        Activate a rule

        Args:
            rule_id: Rule string ID

        Returns:
            Updated SODRule object or None
        """
        rule = self.get_rule_by_id(rule_id)

        if not rule:
            logger.error(f"Rule not found: {rule_id}")
            return None

        rule.is_active = True
        rule.updated_at = datetime.utcnow()

        self.session.commit()
        self.session.refresh(rule)

        logger.info(f"Activated SOD rule: {rule_id}")
        return rule

    def delete_rule(self, rule_id: str):
        """
        Delete a rule

        Args:
            rule_id: Rule string ID
        """
        rule = self.get_rule_by_id(rule_id)
        if rule:
            self.session.delete(rule)
            self.session.commit()
            logger.info(f"Deleted SOD rule: {rule_id}")
