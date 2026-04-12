"""
Risk Assessment Agent - Advanced risk scoring and trend analysis

This agent is responsible for:
1. Historical pattern analysis
2. Severity scoring refinement
3. Business impact assessment
4. Trend detection and prediction
5. Risk level calculation with context
"""

import logging
import os
from datetime import datetime
from typing import Any

from langchain_anthropic import ChatAnthropic

from models.database import (
    User,
    Violation,
    ViolationSeverity,
    ViolationStatus,
)
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository
from utils.langchain_callback import TokenTrackingCallback

logger = logging.getLogger(__name__)


class RiskAssessmentAgent:
    """Agent for advanced risk assessment and scoring"""

    def __init__(
        self,
        violation_repo: ViolationRepository,
        user_repo: UserRepository,
        llm_model: str = "claude-opus-4.6"
    ):
        """
        Initialize Risk Assessment Agent

        Args:
            violation_repo: Violation repository instance
            user_repo: User repository instance
            llm_model: Claude model for risk analysis
        """
        self.violation_repo = violation_repo
        self.user_repo = user_repo
        self._token_callback = TokenTrackingCallback(agent_name="risk_assessor", operation="risk_scoring")
        self.llm = ChatAnthropic(
            model=llm_model,
            temperature=0,
            max_tokens=1024,
            callbacks=[self._token_callback]
        )

        logger.info(f"Risk Assessment Agent initialized with model: {llm_model}")

    def calculate_user_risk_score(
        self,
        user_id: str,
        include_historical: bool = True
    ) -> dict[str, Any]:
        """
        Calculate comprehensive risk score for a user

        Args:
            user_id: User UUID
            include_historical: Include historical violation patterns

        Returns:
            Risk assessment with detailed breakdown
        """
        logger.info(f"Calculating risk score for user: {user_id}")

        # Try to get user by UUID first, then by NetSuite ID
        user = self.user_repo.get_user_by_uuid(user_id)
        if not user:
            user = self.user_repo.get_user_by_id(user_id)

        if not user:
            return {
                'success': False,
                'error': 'User not found'
            }

        # Get current violations (use UUID)
        violations = self.violation_repo.get_violations_by_user(
            str(user.id),  # Use UUID for violations lookup
            status=ViolationStatus.OPEN
        )

        # Calculate base risk score
        base_score = self._calculate_base_risk_score(user, violations)

        # Historical analysis
        historical_score = 0
        if include_historical:
            historical_score = self._calculate_historical_risk(str(user.id))

        # Trend analysis
        trend = self._analyze_violation_trend(str(user.id))

        # Business impact
        business_impact = self._assess_business_impact(user, violations)

        # Combine scores
        final_score = min(
            base_score + historical_score + trend['risk_adjustment'],
            100
        )

        risk_level = self._determine_risk_level(final_score, violations)

        return {
            'success': True,
            'user_id': user_id,
            'user_email': user.email,
            'risk_score': round(final_score, 2),
            'risk_level': risk_level,
            'breakdown': {
                'base_score': base_score,
                'historical_score': historical_score,
                'trend_adjustment': trend['risk_adjustment'],
                'business_impact': business_impact
            },
            'violations': {
                'total': len(violations),
                'critical': sum(1 for v in violations if v.severity == ViolationSeverity.CRITICAL),
                'high': sum(1 for v in violations if v.severity == ViolationSeverity.HIGH),
                'medium': sum(1 for v in violations if v.severity == ViolationSeverity.MEDIUM)
            },
            'trend': trend,
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_base_risk_score(
        self,
        user: User,
        violations: list[Violation]
    ) -> float:
        """Calculate base risk score from current state"""
        score = 0

        # Score from violations
        for violation in violations:
            if violation.severity == ViolationSeverity.CRITICAL:
                score += 25
            elif violation.severity == ViolationSeverity.HIGH:
                score += 15
            elif violation.severity == ViolationSeverity.MEDIUM:
                score += 8
            else:
                score += 3

        # Role count factor
        role_count = len(user.user_roles)
        if role_count >= 4:
            score += 15
        elif role_count >= 3:
            score += 10

        # Department factor
        if user.department and user.department.upper() in ['FINANCE', 'ACCOUNTING', 'IT', 'HR']:
            score += 10

        return min(score, 100)

    def _calculate_historical_risk(self, user_id: str) -> float:
        """Calculate risk score from historical patterns"""
        # Get all violations (including resolved)
        all_violations = self.violation_repo.get_violations_by_user(user_id)

        if not all_violations:
            return 0

        # Count repeat violations
        resolved_violations = [v for v in all_violations if v.status == ViolationStatus.RESOLVED]
        open_violations = [v for v in all_violations if v.status == ViolationStatus.OPEN]

        # If violations keep coming back
        repeat_penalty = 0
        if len(resolved_violations) > 0 and len(open_violations) > 0:
            repeat_penalty = min(len(resolved_violations) * 3, 15)

        # Time to resolution factor
        slow_resolution_penalty = 0
        for violation in resolved_violations:
            if violation.resolved_at and violation.detected_at:
                days_open = (violation.resolved_at - violation.detected_at).days
                if days_open > 30:
                    slow_resolution_penalty += 2

        return min(repeat_penalty + slow_resolution_penalty, 20)

    def _analyze_violation_trend(self, user_id: str) -> dict[str, Any]:
        """
        Analyze violation trends over time

        Returns:
            Trend analysis with risk adjustment
        """
        # Get violations from last 90 days
        recent_violations = self.violation_repo.get_violations_by_user(user_id)

        if not recent_violations:
            return {
                'trend': 'STABLE',
                'risk_adjustment': 0,
                'description': 'No violations detected'
            }

        # Count violations by time period
        now = datetime.now()
        last_30_days = sum(
            1 for v in recent_violations
            if v.detected_at and (now - v.detected_at).days <= 30
        )
        prev_30_days = sum(
            1 for v in recent_violations
            if v.detected_at and 30 < (now - v.detected_at).days <= 60
        )

        # Determine trend
        if last_30_days > prev_30_days * 1.5:
            trend = 'INCREASING'
            risk_adjustment = 10
            description = f'Violations increasing: {prev_30_days} → {last_30_days}'
        elif last_30_days < prev_30_days * 0.5:
            trend = 'DECREASING'
            risk_adjustment = -5
            description = f'Violations decreasing: {prev_30_days} → {last_30_days}'
        else:
            trend = 'STABLE'
            risk_adjustment = 0
            description = f'Violations stable: ~{last_30_days} per month'

        return {
            'trend': trend,
            'risk_adjustment': risk_adjustment,
            'description': description,
            'last_30_days': last_30_days,
            'prev_30_days': prev_30_days
        }

    def _assess_business_impact(
        self,
        user: User,
        violations: list[Violation]
    ) -> dict[str, Any]:
        """
        Assess potential business impact of user's violations

        Returns:
            Business impact assessment
        """
        impact_score = 0
        impact_factors = []

        # Check for SOX-related violations
        sox_violations = [
            v for v in violations
            if v.violation_metadata and
            v.violation_metadata.get('regulatory_framework') == 'SOX'
        ]

        if sox_violations:
            impact_score += 30
            impact_factors.append(f"{len(sox_violations)} SOX compliance violations")

        # Check for financial access
        if user.department and 'FINANCE' in user.department.upper():
            financial_violations = [
                v for v in violations
                if v.rule and 'FIN' in v.rule.rule_id
            ]
            if financial_violations:
                impact_score += 20
                impact_factors.append("Financial controls compromised")

        # Check for admin access violations
        admin_violations = [
            v for v in violations
            if v.conflicting_roles and any('Admin' in r for r in v.conflicting_roles)
        ]
        if admin_violations:
            impact_score += 15
            impact_factors.append("Administrator privilege conflicts")

        # Critical violations
        critical_count = sum(1 for v in violations if v.severity == ViolationSeverity.CRITICAL)
        if critical_count > 0:
            impact_score += critical_count * 10
            impact_factors.append(f"{critical_count} critical severity violations")

        impact_level = 'LOW'
        if impact_score >= 40:
            impact_level = 'CRITICAL'
        elif impact_score >= 25:
            impact_level = 'HIGH'
        elif impact_score >= 10:
            impact_level = 'MEDIUM'

        return {
            'impact_score': min(impact_score, 100),
            'impact_level': impact_level,
            'factors': impact_factors,
            'sox_violations': len(sox_violations)
        }

    def _determine_risk_level(
        self,
        risk_score: float,
        violations: list[Violation]
    ) -> str:
        """Determine risk level category"""
        critical_count = sum(1 for v in violations if v.severity == ViolationSeverity.CRITICAL)

        if risk_score >= 80 or critical_count >= 3:
            return 'CRITICAL'
        elif risk_score >= 60 or critical_count >= 2:
            return 'HIGH'
        elif risk_score >= 40:
            return 'MEDIUM'
        else:
            return 'LOW'

    def assess_organization_risk(self) -> dict[str, Any]:
        """
        Assess overall organization-wide risk

        Returns:
            Organization risk assessment
        """
        logger.info("Assessing organization-wide risk")

        # Get all users
        all_users = self.user_repo.get_all_users()

        # Get violation summary
        violation_summary = self.violation_repo.get_violation_summary()

        # Calculate risk distribution
        risk_distribution = {
            'CRITICAL': 0,
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0
        }

        high_risk_users = []

        batch_size = int(os.getenv('RISK_ASSESSMENT_BATCH_SIZE', '0')) or len(all_users)
        for user in all_users[:batch_size]:
            risk_result = self.calculate_user_risk_score(
                str(user.id),
                include_historical=False  # Skip for performance
            )

            if risk_result['success']:
                risk_level = risk_result['risk_level']
                risk_distribution[risk_level] += 1

                if risk_level in ['CRITICAL', 'HIGH']:
                    high_risk_users.append({
                        'user_id': str(user.id),
                        'email': user.email,
                        'risk_score': risk_result['risk_score'],
                        'risk_level': risk_level
                    })

        # Calculate overall risk score
        total_violations = violation_summary.get('total_open', 0)
        critical_violations = violation_summary.get('severity_counts', {}).get('CRITICAL', 0)

        org_risk_score = min(
            (critical_violations * 5) + (total_violations * 2),
            100
        )

        org_risk_level = 'LOW'
        if org_risk_score >= 70:
            org_risk_level = 'CRITICAL'
        elif org_risk_score >= 50:
            org_risk_level = 'HIGH'
        elif org_risk_score >= 30:
            org_risk_level = 'MEDIUM'

        return {
            'success': True,
            'organization_risk_score': round(org_risk_score, 2),
            'organization_risk_level': org_risk_level,
            'total_users': len(all_users),
            'risk_distribution': risk_distribution,
            'high_risk_users': sorted(
                high_risk_users,
                key=lambda x: x['risk_score'],
                reverse=True
            )[:10],
            'violations': violation_summary,
            'recommendations': self._generate_org_recommendations(
                org_risk_level,
                risk_distribution,
                violation_summary
            ),
            'timestamp': datetime.now().isoformat()
        }

    def _generate_org_recommendations(
        self,
        risk_level: str,
        risk_distribution: dict[str, int],
        violation_summary: dict[str, Any]
    ) -> list[str]:
        """Generate organization-level recommendations"""
        recommendations = []

        if risk_level in ['CRITICAL', 'HIGH']:
            recommendations.append("🚨 Immediate action required: Address critical violations within 24 hours")

        if risk_distribution['CRITICAL'] > 5:
            recommendations.append(
                f"⚠️  {risk_distribution['CRITICAL']} users at critical risk - review access immediately"
            )

        critical_violations = violation_summary.get('severity_counts', {}).get('CRITICAL', 0)
        if critical_violations > 10:
            recommendations.append(
                f"📋 Create remediation project for {critical_violations} critical violations"
            )

        if risk_distribution['HIGH'] + risk_distribution['CRITICAL'] > 20:
            recommendations.append(
                "🔍 Conduct comprehensive access review across organization"
            )

        if not recommendations:
            recommendations.append("✅ Risk levels acceptable - maintain current monitoring")

        return recommendations

    def predict_future_risk(
        self,
        user_id: str,
        days_ahead: int = 30
    ) -> dict[str, Any]:
        """
        Predict future risk based on current trends

        Args:
            user_id: User UUID
            days_ahead: Number of days to predict

        Returns:
            Risk prediction
        """
        logger.info(f"Predicting risk for user {user_id} - {days_ahead} days ahead")

        # Get current risk
        current_risk = self.calculate_user_risk_score(user_id, include_historical=True)

        if not current_risk['success']:
            return current_risk

        # Get trend
        trend = current_risk['trend']

        # Simple linear prediction based on trend
        current_score = current_risk['risk_score']
        trend_direction = trend['trend']

        if trend_direction == 'INCREASING':
            predicted_increase = (days_ahead / 30) * 15  # 15 points per month
            predicted_score = min(current_score + predicted_increase, 100)
            confidence = 'MEDIUM'
        elif trend_direction == 'DECREASING':
            predicted_decrease = (days_ahead / 30) * 10  # 10 points per month
            predicted_score = max(current_score - predicted_decrease, 0)
            confidence = 'MEDIUM'
        else:
            predicted_score = current_score
            confidence = 'HIGH'

        predicted_level = self._determine_risk_level(predicted_score, [])

        return {
            'success': True,
            'user_id': user_id,
            'current_risk_score': current_score,
            'current_risk_level': current_risk['risk_level'],
            'predicted_risk_score': round(predicted_score, 2),
            'predicted_risk_level': predicted_level,
            'prediction_horizon_days': days_ahead,
            'confidence': confidence,
            'trend': trend_direction,
            'recommendation': self._generate_prediction_recommendation(
                current_score,
                predicted_score,
                trend_direction
            ),
            'timestamp': datetime.now().isoformat()
        }

    def _generate_prediction_recommendation(
        self,
        current_score: float,
        predicted_score: float,
        trend: str
    ) -> str:
        """Generate recommendation based on prediction"""
        if trend == 'INCREASING' and predicted_score > 80:
            return "⚠️  Urgent: Risk increasing rapidly. Immediate intervention required."
        elif trend == 'INCREASING' and predicted_score > 60:
            return "⚠️  Risk trending upward. Schedule access review within 2 weeks."
        elif trend == 'DECREASING':
            return "✅ Risk decreasing. Continue current remediation efforts."
        else:
            return "📊 Risk stable. Maintain current monitoring."

    def compare_user_risks(
        self,
        user_ids: list[str]
    ) -> dict[str, Any]:
        """
        Compare risk scores across multiple users

        Args:
            user_ids: List of user UUIDs

        Returns:
            Comparison results
        """
        logger.info(f"Comparing risks for {len(user_ids)} users")

        comparisons = []

        for user_id in user_ids:
            risk_result = self.calculate_user_risk_score(user_id)
            if risk_result['success']:
                comparisons.append(risk_result)

        # Sort by risk score
        comparisons.sort(key=lambda x: x['risk_score'], reverse=True)

        return {
            'success': True,
            'total_users': len(comparisons),
            'highest_risk': comparisons[0] if comparisons else None,
            'lowest_risk': comparisons[-1] if comparisons else None,
            'comparisons': comparisons,
            'timestamp': datetime.now().isoformat()
        }


# Factory function
def create_risk_assessor(
    violation_repo: ViolationRepository,
    user_repo: UserRepository
) -> RiskAssessmentAgent:
    """Create a configured Risk Assessment Agent instance"""
    return RiskAssessmentAgent(
        violation_repo=violation_repo,
        user_repo=user_repo
    )
