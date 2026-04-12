#!/usr/bin/env python3
"""
Knowledge Base Enrichment Script

Enriches the vector database (pgvector) with embeddings from:
1. SOD rules and descriptions
2. Compensating controls and effectiveness
3. Job role mappings and business justifications
4. Permission conflict analysis results
5. Compliance policies and remediation guidance

This script should be executed by the data collection agent after syncs
to ensure the knowledge base is always up-to-date for semantic search.

Usage:
    python3 scripts/enrich_knowledge_base.py [--force-refresh]

Options:
    --force-refresh  Force regeneration of all embeddings (default: only new/updated)
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.embedding_service import create_embedding_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db')


class KnowledgeBaseEnricher:
    """Enriches knowledge base with embeddings from compliance data"""

    def __init__(self, database_url: str, force_refresh: bool = False):
        """
        Initialize enricher

        Args:
            database_url: PostgreSQL connection string
            force_refresh: Force regeneration of all embeddings
        """
        self.database_url = database_url
        self.force_refresh = force_refresh
        self.conn = None
        self.embedding_service = None
        self.stats = {
            'sod_rules': 0,
            'compensating_controls': 0,
            'control_packages': 0,
            'job_role_mappings': 0,
            'permission_categories': 0,
            'conflicts': 0,
            'total': 0
        }

    def connect(self):
        """Connect to PostgreSQL and initialize embedding service"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.conn.autocommit = False
            logger.info("✓ Connected to database")

            # Initialize embedding service (use HuggingFace for local embeddings)
            self.embedding_service = create_embedding_service(provider='huggingface')
            logger.info("✓ Embedding service initialized")
        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("✓ Database connection closed")

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding vector for text

        Args:
            text: Text to embed

        Returns:
            List of floats (384-dimension vector)
        """
        try:
            # Use the model's embed_query method
            embedding = self.embedding_service.model.embed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"✗ Failed to generate embedding: {e}")
            raise

    def upsert_document(self, doc_data: dict[str, Any]):
        """
        Upsert document to knowledge_base_documents table

        Args:
            doc_data: Document data with keys:
                - doc_id: Unique document ID
                - doc_type: Type of document (sod_rule, control, etc.)
                - title: Document title
                - content: Document content
                - embedding: Vector embedding
                - tags: Optional tags
                - category: Optional category
                - reference_id: Optional reference to source table
                - reference_table: Optional source table name
                - metadata: Optional JSON metadata
        """
        cursor = self.conn.cursor()

        sql = """
        INSERT INTO knowledge_base_documents (
            doc_id, doc_type, title, content, embedding,
            tags, category, reference_id, reference_table, metadata
        ) VALUES (
            %s, %s, %s, %s, %s::vector,
            %s, %s, %s, %s, %s
        )
        ON CONFLICT (doc_id) DO UPDATE SET
            title = EXCLUDED.title,
            content = EXCLUDED.content,
            embedding = EXCLUDED.embedding,
            tags = EXCLUDED.tags,
            category = EXCLUDED.category,
            reference_id = EXCLUDED.reference_id,
            reference_table = EXCLUDED.reference_table,
            metadata = EXCLUDED.metadata,
            updated_at = CURRENT_TIMESTAMP;
        """

        cursor.execute(sql, (
            doc_data['doc_id'],
            doc_data['doc_type'],
            doc_data['title'],
            doc_data['content'],
            doc_data['embedding'],
            doc_data.get('tags'),
            doc_data.get('category'),
            doc_data.get('reference_id'),
            doc_data.get('reference_table'),
            Json(doc_data.get('metadata', {}))
        ))

        self.conn.commit()
        cursor.close()

    def enrich_sod_rules(self):
        """Enrich SOD rules from database"""
        logger.info("=" * 80)
        logger.info("ENRICHING SOD RULES")
        logger.info("=" * 80)

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT rule_id, rule_name, description, severity,
                   category, conflicting_permissions, principle
            FROM sod_rules
            WHERE is_active = true
        """)

        rules = cursor.fetchall()
        logger.info(f"Found {len(rules)} active SOD rules")

        for rule in rules:
            rule_id, rule_name, description, severity, category, \
                conflicting_perms, principle = rule
            metadata = {}

            # Build content for embedding
            content = f"""
SOD Rule: {rule_name}
Severity: {severity}
Category: {category or 'N/A'}
Principle: {principle or 'N/A'}

Description: {description or 'N/A'}

Conflicting Permissions: {', '.join(conflicting_perms) if conflicting_perms else 'N/A'}
            """.strip()

            # Generate embedding
            embedding = self.generate_embedding(content)

            # Upsert to knowledge base
            self.upsert_document({
                'doc_id': f'sod_rule_{rule_id}',
                'doc_type': 'sod_rule',
                'title': rule_name,
                'content': content,
                'embedding': embedding,
                'tags': [severity.lower() if severity else 'medium', category.lower() if category else 'general'],
                'category': 'compliance',
                'reference_id': rule_id,
                'reference_table': 'sod_rules',
                'metadata': metadata or {}
            })

            self.stats['sod_rules'] += 1

        cursor.close()
        logger.info(f"✓ Enriched {self.stats['sod_rules']} SOD rules")

    def enrich_compensating_controls(self):
        """Enrich compensating controls from database"""
        logger.info("\n" + "=" * 80)
        logger.info("ENRICHING COMPENSATING CONTROLS")
        logger.info("=" * 80)

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT control_id, name, description, control_type,
                   risk_reduction_percentage, implementation_time_hours,
                   annual_cost_estimate, metadata
            FROM compensating_controls
            WHERE is_active = true
        """)

        controls = cursor.fetchall()
        logger.info(f"Found {len(controls)} active compensating controls")

        for control in controls:
            control_id, name, description, control_type, risk_reduction, \
                impl_time, cost, metadata = control

            # Build content for embedding
            content = f"""
Compensating Control: {name}
Type: {control_type or 'N/A'}
Risk Reduction: {risk_reduction}%

Description: {description}

Implementation Time: {impl_time or 'N/A'} hours
Annual Cost: {cost or 'N/A'}
            """.strip()

            # Generate embedding
            embedding = self.generate_embedding(content)

            # Upsert to knowledge base
            self.upsert_document({
                'doc_id': f'control_{control_id}',
                'doc_type': 'compensating_control',
                'title': name,
                'content': content,
                'embedding': embedding,
                'tags': [control_type.lower() if control_type else 'control'],
                'category': 'controls',
                'reference_id': control_id,
                'reference_table': 'compensating_controls',
                'metadata': metadata or {}
            })

            self.stats['compensating_controls'] += 1

        cursor.close()
        logger.info(f"✓ Enriched {self.stats['compensating_controls']} compensating controls")

    def enrich_control_packages(self):
        """Enrich control packages from database"""
        logger.info("\n" + "=" * 80)
        logger.info("ENRICHING CONTROL PACKAGES")
        logger.info("=" * 80)

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT package_id, package_name, description, total_risk_reduction,
                   included_control_ids, estimated_annual_cost,
                   implementation_time_hours, severity_level, metadata
            FROM control_packages
            WHERE is_active = true
        """)

        packages = cursor.fetchall()
        logger.info(f"Found {len(packages)} active control packages")

        for package in packages:
            package_id, name, description, risk_reduction, control_ids, \
                cost, impl_time, severity, metadata = package

            # Build content for embedding
            content = f"""
Control Package: {name}
Target Severity: {severity or 'N/A'}
Total Risk Reduction: {risk_reduction}%

Description: {description or 'N/A'}

Included Controls: {', '.join(control_ids) if control_ids else 'N/A'}

Estimated Annual Cost: {cost or 'N/A'}
Implementation Time: {impl_time or 'N/A'} hours
            """.strip()

            # Generate embedding
            embedding = self.generate_embedding(content)

            # Upsert to knowledge base
            self.upsert_document({
                'doc_id': f'package_{package_id}',
                'doc_type': 'control_package',
                'title': name,
                'content': content,
                'embedding': embedding,
                'tags': [severity.lower() if severity else 'package'],
                'category': 'controls',
                'reference_id': package_id,
                'reference_table': 'control_packages',
                'metadata': metadata or {}
            })

            self.stats['control_packages'] += 1

        cursor.close()
        logger.info(f"✓ Enriched {self.stats['control_packages']} control packages")

    def enrich_job_role_mappings(self):
        """Enrich job role mappings from database"""
        logger.info("\n" + "=" * 80)
        logger.info("ENRICHING JOB ROLE MAPPINGS")
        logger.info("=" * 80)

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT job_role_id, job_title, department,
                   typical_netsuite_roles, business_justification,
                   requires_compensating_controls, typical_controls,
                   metadata
            FROM job_role_mappings
            WHERE is_active = true
        """)

        mappings = cursor.fetchall()
        logger.info(f"Found {len(mappings)} active job role mappings")

        for mapping in mappings:
            job_role_id, job_title, department, typical_roles, \
                business_just, requires_controls, controls, metadata = mapping

            # Build content for embedding
            role_list = []
            if typical_roles:
                for role_data in typical_roles:
                    if isinstance(role_data, dict):
                        role_list.append(role_data.get('role', ''))
                    else:
                        role_list.append(str(role_data))

            content = f"""
Job Role: {job_title}
Department: {department or 'N/A'}

Typical NetSuite Roles: {', '.join(role_list) if role_list else 'N/A'}

Business Justification: {business_just or 'N/A'}

Requires Compensating Controls: {'Yes' if requires_controls else 'No'}

Typical Controls: {', '.join(controls) if controls else 'N/A'}
            """.strip()

            # Generate embedding
            embedding = self.generate_embedding(content)

            # Upsert to knowledge base
            self.upsert_document({
                'doc_id': f'job_role_{job_role_id}',
                'doc_type': 'job_role_mapping',
                'title': job_title,
                'content': content,
                'embedding': embedding,
                'tags': [department.lower() if department else 'general'],
                'category': 'job_roles',
                'reference_id': job_role_id,
                'reference_table': 'job_role_mappings',
                'metadata': metadata or {}
            })

            self.stats['job_role_mappings'] += 1

        cursor.close()
        logger.info(f"✓ Enriched {self.stats['job_role_mappings']} job role mappings")

    def enrich_permission_categories(self):
        """Enrich permission categories from database"""
        logger.info("\n" + "=" * 80)
        logger.info("ENRICHING PERMISSION CATEGORIES")
        logger.info("=" * 80)

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT category_id, category_name, description,
                   base_risk_score, level_risk_adjustments
            FROM permission_categories
        """)

        categories = cursor.fetchall()
        logger.info(f"Found {len(categories)} permission categories")

        for category in categories:
            category_id, category_name, description, risk_score, level_adjustments = category

            # Build content for embedding
            content = f"""
Permission Category: {category_name}
Base Risk Score: {risk_score or 50}/100

Description: {description or 'N/A'}

Level Risk Adjustments: {level_adjustments if level_adjustments else 'Standard'}
            """.strip()

            # Generate embedding
            embedding = self.generate_embedding(content)

            # Upsert to knowledge base
            self.upsert_document({
                'doc_id': f'perm_category_{category_id}',
                'doc_type': 'permission_category',
                'title': category_name,
                'content': content,
                'embedding': embedding,
                'tags': ['permissions'],
                'category': 'permissions',
                'reference_id': category_id,
                'reference_table': 'permission_categories',
                'metadata': {'risk_score': risk_score}
            })

            self.stats['permission_categories'] += 1

        cursor.close()
        logger.info(f"✓ Enriched {self.stats['permission_categories']} permission categories")

    def enrich_conflict_analysis(self):
        """
        Enrich with permission conflict analysis results
        (from output/permission_conflict_analysis.json if exists)
        """
        logger.info("\n" + "=" * 80)
        logger.info("ENRICHING CONFLICT ANALYSIS RESULTS")
        logger.info("=" * 80)

        conflict_file = Path(__file__).parent.parent / 'output' / 'permission_conflict_analysis.json'

        if not conflict_file.exists():
            logger.warning(f"⚠️  Conflict analysis file not found: {conflict_file}")
            logger.warning("   Run analyze_access_request_with_levels.py first to generate conflict data")
            return

        try:
            with open(conflict_file) as f:
                data = json.load(f)

            conflicts = data.get('conflicts', [])
            logger.info(f"Found {len(conflicts)} conflicts to enrich")

            # Group by severity for summary documents
            by_severity = {'CRIT': [], 'HIGH': [], 'MED': [], 'LOW': []}
            for conflict in conflicts:
                severity = conflict.get('severity', 'LOW')
                by_severity[severity].append(conflict)

            # Create summary document for each severity
            for severity, severity_conflicts in by_severity.items():
                if not severity_conflicts:
                    continue

                # Sample top 10 conflicts for this severity
                sample = severity_conflicts[:10]

                content = f"""
Permission Conflicts - {severity} Severity
Total Conflicts: {len(severity_conflicts)}

Top Conflict Examples:
"""
                for i, conflict in enumerate(sample, 1):
                    content += f"""
{i}. {conflict.get('role1', 'N/A')} + {conflict.get('role2', 'N/A')}
   Conflict: {conflict.get('permission1', 'N/A')} ({conflict.get('permission1_level', 'N/A')})
             vs {conflict.get('permission2', 'N/A')} ({conflict.get('permission2_level', 'N/A')})
   Risk Score: {conflict.get('inherent_risk', 0)}/100
   Principle: {conflict.get('principle', 'N/A')}
"""

                # Generate embedding
                embedding = self.generate_embedding(content)

                # Upsert to knowledge base
                self.upsert_document({
                    'doc_id': f'conflicts_{severity.lower()}',
                    'doc_type': 'conflict_analysis',
                    'title': f'Permission Conflicts - {severity} Severity',
                    'content': content,
                    'embedding': embedding,
                    'tags': [severity.lower(), 'conflicts'],
                    'category': 'analysis',
                    'reference_id': None,
                    'reference_table': None,
                    'metadata': {
                        'total_conflicts': len(severity_conflicts),
                        'severity': severity,
                        'generated_at': datetime.utcnow().isoformat()
                    }
                })

                self.stats['conflicts'] += 1

            logger.info(f"✓ Enriched {self.stats['conflicts']} conflict summary documents")

        except Exception as e:
            logger.error(f"✗ Failed to enrich conflict analysis: {e}")

    def run(self):
        """Run the complete enrichment process"""
        logger.info("=" * 80)
        logger.info("KNOWLEDGE BASE ENRICHMENT STARTED")
        logger.info("=" * 80)
        logger.info(f"Force Refresh: {self.force_refresh}")
        logger.info(f"Started at: {datetime.utcnow().isoformat()}")

        try:
            # Connect
            self.connect()

            # Enrich all data sources
            self.enrich_sod_rules()
            self.enrich_compensating_controls()
            self.enrich_control_packages()
            self.enrich_job_role_mappings()
            self.enrich_permission_categories()
            self.enrich_conflict_analysis()

            # Calculate total
            self.stats['total'] = sum([
                self.stats['sod_rules'],
                self.stats['compensating_controls'],
                self.stats['control_packages'],
                self.stats['job_role_mappings'],
                self.stats['permission_categories'],
                self.stats['conflicts']
            ])

            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("ENRICHMENT COMPLETE")
            logger.info("=" * 80)
            logger.info(f"✓ SOD Rules: {self.stats['sod_rules']}")
            logger.info(f"✓ Compensating Controls: {self.stats['compensating_controls']}")
            logger.info(f"✓ Control Packages: {self.stats['control_packages']}")
            logger.info(f"✓ Job Role Mappings: {self.stats['job_role_mappings']}")
            logger.info(f"✓ Permission Categories: {self.stats['permission_categories']}")
            logger.info(f"✓ Conflict Analysis: {self.stats['conflicts']}")
            logger.info("=" * 80)
            logger.info(f"✓ TOTAL DOCUMENTS ENRICHED: {self.stats['total']}")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"✗ Enrichment failed: {e}")
            import traceback
            traceback.print_exc()
            raise

        finally:
            self.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Enrich knowledge base with embeddings from compliance data'
    )
    parser.add_argument(
        '--force-refresh',
        action='store_true',
        help='Force regeneration of all embeddings (default: only new/updated)'
    )

    args = parser.parse_args()

    # Create enricher and run
    enricher = KnowledgeBaseEnricher(
        database_url=DATABASE_URL,
        force_refresh=args.force_refresh
    )

    try:
        enricher.run()
        logger.info("✅ Knowledge base enrichment completed successfully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Knowledge base enrichment failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
