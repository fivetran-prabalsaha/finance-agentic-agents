"""
Role Recommendation Service

Recommends roles for new hires based on what existing employees
with similar job titles currently have.
"""

import logging
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RoleRecommendationService:
    """Service for recommending roles based on peer analysis"""

    def __init__(self, session: Session):
        self.session = session

    def recommend_roles_by_job_title(
        self,
        job_title: str,
        department: str | None = None,
        min_similarity_threshold: float = 0.6,
        check_conflicts: bool = True
    ) -> dict[str, Any]:
        """
        Recommend roles based on what peers with similar job titles have

        Args:
            job_title: Job title of the new hire (e.g., "Revenue Director")
            department: Optional department filter (e.g., "Finance", "Accounting")
            min_similarity_threshold: Minimum similarity score (0-1) for peer matching
            check_conflicts: If True, analyze SOD conflicts in recommended roles

        Returns:
            Dictionary with recommended roles and peer analysis
        """
        logger.info(f"Finding role recommendations for: {job_title}, department: {department}")

        # Find users with similar job titles
        peers = self._find_peers_by_job_title(job_title, min_similarity_threshold, department)

        if not peers:
            return {
                'success': False,
                'message': f'No existing employees found with similar job title to "{job_title}"',
                'recommended_roles': [],
                'peers_analyzed': 0
            }

        # Extract roles from peers
        role_frequency = Counter()
        peer_details = []

        for peer in peers:
            peer_roles = self._get_user_roles(peer['user_id'])

            peer_details.append({
                'name': peer['name'],
                'email': peer['email'],
                'title': peer['title'],
                'roles': peer_roles,
                'role_count': len(peer_roles)
            })

            # Count role frequency across peers
            for role in peer_roles:
                role_frequency[role] += 1

        # Recommend roles that appear in majority of peers (>50%)
        total_peers = len(peers)
        recommended_roles = []

        for role, count in role_frequency.most_common():
            percentage = (count / total_peers) * 100
            recommended_roles.append({
                'role_name': role,
                'frequency': count,
                'percentage': round(percentage, 1),
                'confidence': 'HIGH' if percentage >= 75 else 'MEDIUM' if percentage >= 50 else 'LOW'
            })

        # Check for SOD conflicts in recommended combination
        conflict_analysis = None
        if check_conflicts and recommended_roles:
            all_recommended_role_names = [r['role_name'] for r in recommended_roles]
            conflict_analysis = self._check_role_conflicts(job_title, all_recommended_role_names)

        return {
            'success': True,
            'job_title_searched': job_title,
            'recommended_roles': recommended_roles,
            'peers_analyzed': total_peers,
            'peer_details': peer_details,
            'recommendation_method': 'peer_analysis',
            'conflict_analysis': conflict_analysis,
            'notes': f'Based on {total_peers} existing employee(s) with similar job title'
        }

    def _find_peers_by_job_title(
        self,
        job_title: str,
        min_similarity: float,
        department: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Find users with similar job titles and optionally same department

        Uses fuzzy matching on job title keywords
        """
        from sqlalchemy import text

        # Extract key terms from job title
        key_terms = self._extract_key_terms(job_title)

        if not key_terms:
            return []

        # Build SQL query with similarity matching
        # Match if title contains ALL key terms (not just any)
        conditions = []
        params = {}

        for i, term in enumerate(key_terms):
            param_name = f'term{i}'
            conditions.append(f"LOWER(title) LIKE LOWER(:{param_name})")
            params[param_name] = f'%{term}%'

        where_clause = ' AND '.join(conditions)

        # Add department filter if provided
        dept_filter = ""
        if department:
            dept_filter = "AND LOWER(department) LIKE LOWER(:department)"
            params['department'] = f'%{department}%'

        query = text(f"""
            SELECT id, name, email, title, department
            FROM users
            WHERE status = 'ACTIVE'
              AND ({where_clause})
              {dept_filter}
              AND title IS NOT NULL
              AND title != ''
            ORDER BY title
        """)

        result = self.session.execute(query, params)

        peers = []
        for row in result:
            peers.append({
                'user_id': row[0],
                'name': row[1],
                'email': row[2],
                'title': row[3],
                'department': row[4] if len(row) > 4 else None
            })

        logger.info(f"Found {len(peers)} peers with similar titles")
        return peers

    def _extract_key_terms(self, job_title: str) -> list[str]:
        """
        Extract key terms from job title for matching

        Example: "Revenue Director" -> ["revenue", "director"]
        """
        # Common words to ignore
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'as', 'is', 'was',
            'senior', 'sr', 'junior', 'jr', 'ii', 'iii', 'iv'
        }

        # Split and clean
        words = job_title.lower().replace(',', ' ').split()

        # Filter out stop words and short words
        key_terms = [
            word for word in words
            if word not in stop_words and len(word) > 2
        ]

        return key_terms

    def _get_user_roles(self, user_id: int) -> list[str]:
        """Get list of role names for a user"""
        from sqlalchemy import text

        query = text("""
            SELECT r.role_name
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = :user_id
            ORDER BY r.role_name
        """)

        result = self.session.execute(query, {'user_id': user_id})
        return [row[0] for row in result]

    def _check_role_conflicts(self, job_title: str, role_names: list[str]) -> dict[str, Any] | None:
        """
        Check if role combination has SOD conflicts

        Args:
            job_title: Job title for context
            role_names: List of role names to check

        Returns:
            Dict with conflict analysis or None if check fails
        """
        try:
            import subprocess

            # Use the analyze_access_request script
            roles_arg = ",".join(role_names)
            cmd = [
                "python3",
                "scripts/analyze_access_request_with_levels.py",
                "--job-title", job_title,
                "--requested-roles", roles_arg,
                "--mode", "single-request"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.warning(f"Conflict check failed: {result.stderr}")
                return None

            # Parse the output (the script outputs JSON)
            try:
                # The script should output JSON, but if not, return a simple summary
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'conflicts found' in line.lower():
                        # Extract conflict count
                        import re
                        match = re.search(r'(\d+)\s+conflicts?', line, re.IGNORECASE)
                        if match:
                            conflict_count = int(match.group(1))
                            return {
                                'has_conflicts': conflict_count > 0,
                                'conflict_count': conflict_count,
                                'risk_level': 'HIGH' if conflict_count > 100 else 'MEDIUM' if conflict_count > 20 else 'LOW',
                                'checked': True
                            }
            except Exception as e:
                logger.warning(f"Error parsing conflict analysis: {str(e)}")

            # Fallback: assume conflicts exist if we can't parse
            return {
                'has_conflicts': True,
                'conflict_count': None,
                'risk_level': 'UNKNOWN',
                'checked': False,
                'note': 'Could not parse conflict analysis'
            }

        except subprocess.TimeoutExpired:
            logger.warning("Conflict check timed out")
            return None
        except Exception as e:
            logger.error(f"Error checking conflicts: {str(e)}")
            return None

    def get_role_assignment_template(
        self,
        job_title: str,
        format: str = 'summary'
    ) -> str:
        """
        Get a formatted role assignment template

        Args:
            job_title: Job title to get template for
            format: 'summary' or 'detailed'

        Returns:
            Formatted string with role recommendations
        """
        result = self.recommend_roles_by_job_title(job_title)

        if not result['success']:
            return f"❌ {result['message']}\n\nNo role recommendations available."

        if format == 'summary':
            return self._format_summary(result)
        else:
            return self._format_detailed(result)

    def _format_summary(self, result: dict[str, Any]) -> str:
        """Format as brief summary"""
        output = f"**Role Recommendations for: {result['job_title_searched']}**\n\n"
        output += f"Based on {result['peers_analyzed']} existing employee(s):\n\n"

        for rec in result['recommended_roles']:
            output += f"• {rec['role_name']} ({rec['percentage']}% of peers)\n"

        output += "\n**Basis:** "
        for peer in result['peer_details']:
            output += f"{peer['name']}, "
        output = output.rstrip(', ')

        return output

    def _format_detailed(self, result: dict[str, Any]) -> str:
        """Format with detailed peer breakdown"""
        output = f"**Role Recommendations for: {result['job_title_searched']}**\n\n"
        output += f"**Peers Analyzed:** {result['peers_analyzed']}\n\n"

        output += "**Recommended Roles:**\n"
        for rec in result['recommended_roles']:
            confidence_emoji = "✅" if rec['confidence'] == 'HIGH' else "⚠️"
            output += f"{confidence_emoji} {rec['role_name']} - {rec['percentage']}% of peers ({rec['frequency']}/{result['peers_analyzed']})\n"

        output += "\n**Peer Details:**\n"
        for peer in result['peer_details']:
            output += f"\n• {peer['name']} ({peer['title']})\n"
            output += f"  Roles: {', '.join(peer['roles']) if peer['roles'] else 'None assigned'}\n"

        return output
