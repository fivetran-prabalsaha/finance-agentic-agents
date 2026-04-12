#!/usr/bin/env python3
"""
Seed SOD Configurations to PostgreSQL and pgvector

Loads SOD rules, compensating controls, job role mappings, and permission
configurations from JSON files and seeds them to the database.

Also creates vector embeddings for knowledge base agent semantic search.

Usage:
    python3 scripts/seed_sod_configurations.py [--reset]

Options:
    --reset     Drop and recreate all configuration tables before seeding
"""

import json
import logging
import os
import sys
import uuid
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.embedding_service import create_embedding_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db')

# Data file paths
DATA_DIR = Path(__file__).parent.parent / 'data'
SOD_CONFIG_FILE = DATA_DIR / 'netsuite_sod_config_unified.json'
CONTROLS_FILE = DATA_DIR / 'compensating_controls.json'
JOB_ROLES_FILE = DATA_DIR / 'job_role_mappings.json'


class SODConfigSeeder:
    """Seeds SOD configurations to PostgreSQL and pgvector"""

    def __init__(self, database_url: str):
        """Initialize seeder with database connection"""
        self.database_url = database_url
        self.conn = None
        self.embedding_service = None  # Will be initialized after DB connection

    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.conn.autocommit = False
            logger.info("✓ Connected to database")

            # Initialize embedding service (use HuggingFace by default for free local embeddings)
            self.embedding_service = create_embedding_service(provider='huggingface')
            logger.info("✓ Embedding service initialized")
        except Exception as e:
            logger.error(f"✗ Database connection failed: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("✓ Database connection closed")

    def load_json_file(self, filepath: Path) -> dict:
        """Load JSON configuration file"""
        try:
            with open(filepath) as f:
                data = json.load(f)
            logger.info(f"✓ Loaded {filepath.name}")
            return data
        except Exception as e:
            logger.error(f"✗ Failed to load {filepath}: {e}")
            raise

    def execute_schema_extensions(self):
        """Execute schema extensions SQL"""
        schema_file = Path(__file__).parent.parent / 'database' / 'schema_extensions.sql'
        try:
            # Check if compensating_controls table exists
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'compensating_controls'
                )
            """)
            tables_exist = cursor.fetchone()[0]

            if not tables_exist:
                with open(schema_file) as f:
                    schema_sql = f.read()

                cursor.execute(schema_sql)
                self.conn.commit()
                logger.info("✓ Schema extensions applied")
            else:
                logger.info("✓ Schema extensions already applied (skipping)")

        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ Failed to apply schema extensions: {e}")
            raise

    def reset_configuration_tables(self):
        """Drop and recreate configuration tables"""
        logger.warning("Resetting configuration tables...")

        tables = [
            'access_request_analyses',
            'knowledge_base_documents',
            'permission_categories',
            'job_role_mappings',
            'control_packages',
            'compensating_controls'
        ]

        cursor = self.conn.cursor()
        try:
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                logger.info(f"  Dropped table: {table}")

            self.conn.commit()
            logger.info("✓ Configuration tables reset")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ Failed to reset tables: {e}")
            raise

    def seed_permission_categories(self, sod_config: dict):
        """Seed permission categories to database"""
        logger.info("Seeding permission categories...")

        categories = sod_config.get('permission_categories', {})
        cursor = self.conn.cursor()

        try:
            for category_id, category_data in categories.items():
                cursor.execute("""
                    INSERT INTO permission_categories (
                        category_id, category_name, description,
                        base_risk_score, level_risk_adjustments
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (category_id) DO UPDATE SET
                        category_name = EXCLUDED.category_name,
                        description = EXCLUDED.description,
                        base_risk_score = EXCLUDED.base_risk_score,
                        level_risk_adjustments = EXCLUDED.level_risk_adjustments,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    category_id,
                    category_data.get('name', category_id),
                    category_data.get('description', ''),
                    category_data.get('base_risk_score', 50),
                    Json(category_data.get('level_risk_adjustments', {}))
                ))

            self.conn.commit()
            logger.info(f"✓ Seeded {len(categories)} permission categories")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ Failed to seed permission categories: {e}")
            raise

    def seed_sod_rules(self, sod_config: dict):
        """Seed SOD rules with level-based conflict matrices"""
        logger.info("Seeding SOD rules...")

        conflict_rules = sod_config.get('conflict_rules', {})
        cursor = self.conn.cursor()

        try:
            for rule_key, rule_data in conflict_rules.items():
                rule_id = rule_data.get('rule_id', f"SOD-{rule_key.upper()}")

                cursor.execute("""
                    INSERT INTO sod_rules (
                        id, rule_id, rule_name, description, category,
                        principle, category1, category2,
                        base_risk_score, severity, conflicting_permissions,
                        level_conflict_matrix, resolution_strategies,
                        is_active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (rule_id) DO UPDATE SET
                        rule_name = EXCLUDED.rule_name,
                        description = EXCLUDED.description,
                        category = EXCLUDED.category,
                        principle = EXCLUDED.principle,
                        category1 = EXCLUDED.category1,
                        category2 = EXCLUDED.category2,
                        base_risk_score = EXCLUDED.base_risk_score,
                        level_conflict_matrix = EXCLUDED.level_conflict_matrix,
                        resolution_strategies = EXCLUDED.resolution_strategies,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    str(uuid.uuid4()),  # Generate UUID for id column
                    rule_id,
                    rule_data.get('name', rule_key.replace('_', ' ').title()),
                    rule_data.get('description', ''),
                    'FINANCIAL',  # category column
                    rule_data.get('principle', ''),
                    rule_data.get('category1', ''),
                    rule_data.get('category2', ''),
                    rule_data.get('base_risk_score', 50),
                    'CRITICAL',
                    Json(rule_data.get('conflicting_permissions', {})),
                    Json(rule_data.get('level_conflict_matrix', {})),
                    Json(rule_data.get('resolution_strategies', {})),
                    True
                ))

            self.conn.commit()
            logger.info(f"✓ Seeded {len(conflict_rules)} SOD rules")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ Failed to seed SOD rules: {e}")
            raise

    def seed_compensating_controls(self, controls_data: dict):
        """Seed compensating controls to database"""
        logger.info("Seeding compensating controls...")

        controls = controls_data.get('controls', {})
        cursor = self.conn.cursor()

        try:
            for control_id, control_data in controls.items():
                effectiveness = control_data.get('effectiveness', {})
                implementation = control_data.get('implementation', {})
                costs = control_data.get('costs', {})

                cursor.execute("""
                    INSERT INTO compensating_controls (
                        id, control_id, name, control_type, description,
                        risk_reduction_percentage,
                        implementation_steps, implementation_time_hours,
                        technical_requirements,
                        annual_cost_estimate, setup_cost_estimate,
                        is_active, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (control_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        control_type = EXCLUDED.control_type,
                        description = EXCLUDED.description,
                        risk_reduction_percentage = EXCLUDED.risk_reduction_percentage,
                        implementation_steps = EXCLUDED.implementation_steps,
                        implementation_time_hours = EXCLUDED.implementation_time_hours,
                        annual_cost_estimate = EXCLUDED.annual_cost_estimate,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    str(uuid.uuid4()),  # Generate UUID for id column
                    control_id,
                    control_data.get('name', control_id),
                    control_data.get('type', 'PREVENTIVE'),
                    control_data.get('description', ''),
                    effectiveness.get('risk_reduction_percentage', 0),
                    implementation.get('steps', []),
                    implementation.get('estimated_time_hours', 0),
                    implementation.get('technical_requirements', ''),
                    costs.get('annual_cost_estimate', '$0'),
                    costs.get('setup_cost_estimate', '$0'),
                    True,
                    Json(control_data)
                ))

            self.conn.commit()
            logger.info(f"✓ Seeded {len(controls)} compensating controls")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ Failed to seed compensating controls: {e}")
            raise

    def seed_control_packages(self, controls_data: dict):
        """Seed control packages to database"""
        logger.info("Seeding control packages...")

        packages = controls_data.get('control_packages', {})
        cursor = self.conn.cursor()

        try:
            for package_id, package_data in packages.items():
                cursor.execute("""
                    INSERT INTO control_packages (
                        id, package_id, package_name, severity_level, description,
                        included_control_ids, total_risk_reduction,
                        estimated_annual_cost, implementation_time_hours,
                        is_active, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (package_id) DO UPDATE SET
                        package_name = EXCLUDED.package_name,
                        severity_level = EXCLUDED.severity_level,
                        included_control_ids = EXCLUDED.included_control_ids,
                        total_risk_reduction = EXCLUDED.total_risk_reduction,
                        estimated_annual_cost = EXCLUDED.estimated_annual_cost,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    str(uuid.uuid4()),  # Generate UUID for id column
                    package_id,
                    package_data.get('name', package_id),
                    package_data.get('applicable_severity', ['MEDIUM'])[0],  # Get first severity from array
                    package_data.get('description', ''),
                    package_data.get('included_controls', []),
                    package_data.get('total_risk_reduction', 0),
                    package_data.get('estimated_annual_cost', '$0'),
                    package_data.get('implementation_time_hours', 0),
                    True,
                    Json(package_data)
                ))

            self.conn.commit()
            logger.info(f"✓ Seeded {len(packages)} control packages")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ Failed to seed control packages: {e}")
            raise

    def seed_job_role_mappings(self, job_roles_data: dict):
        """Seed job role mappings to database"""
        logger.info("Seeding job role mappings...")

        job_roles = job_roles_data.get('job_roles', {})
        cursor = self.conn.cursor()

        try:
            for job_role_id, role_data in job_roles.items():
                # Extract typical required controls from acceptable_role_combinations
                typical_controls = []
                typical_resolution_strategy = 'approve'

                acceptable_combos = role_data.get('acceptable_role_combinations', [])
                if acceptable_combos:
                    first_combo = acceptable_combos[0]
                    typical_controls = first_combo.get('typical_controls', [])
                    if first_combo.get('requires_compensating_controls', False):
                        typical_resolution_strategy = 'compensating_controls'

                # Determine approval requirements based on role level
                role_level = role_data.get('level', 'Manager')
                requires_executive = role_level in ['Director', 'VP', 'C-Level']
                default_approval_level = role_data.get('reports_to', 'Manager')

                cursor.execute("""
                    INSERT INTO job_role_mappings (
                        id, job_role_id, job_title, department,
                        typical_netsuite_roles, acceptable_role_combinations,
                        not_recommended_combinations,
                        typical_resolution_strategy, typical_required_controls,
                        requires_manager_approval, requires_executive_approval,
                        requires_audit_review, default_approval_level,
                        business_justification, restrictions,
                        is_active, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (job_role_id) DO UPDATE SET
                        job_title = EXCLUDED.job_title,
                        typical_netsuite_roles = EXCLUDED.typical_netsuite_roles,
                        acceptable_role_combinations = EXCLUDED.acceptable_role_combinations,
                        typical_resolution_strategy = EXCLUDED.typical_resolution_strategy,
                        typical_required_controls = EXCLUDED.typical_required_controls,
                        business_justification = EXCLUDED.business_justification,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    str(uuid.uuid4()),  # Generate UUID for id column
                    job_role_id,
                    role_data.get('title', job_role_id.replace('_', ' ').title()),
                    role_data.get('department', ''),
                    Json(role_data.get('typical_netsuite_roles', [])),
                    Json(role_data.get('acceptable_role_combinations', [])),
                    Json([]),  # not_recommended_combinations
                    typical_resolution_strategy,
                    typical_controls,
                    True,  # requires_manager_approval
                    requires_executive,
                    False,  # requires_audit_review
                    default_approval_level,
                    role_data.get('description', ''),
                    [],  # restrictions
                    True,
                    Json(role_data)
                ))

            self.conn.commit()
            logger.info(f"✓ Seeded {len(job_roles)} job role mappings")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ Failed to seed job role mappings: {e}")
            raise

    def create_knowledge_base_embeddings(self, sod_config: dict, controls_data: dict, job_roles_data: dict):
        """Create vector embeddings for knowledge base"""
        logger.info("Creating knowledge base embeddings...")

        cursor = self.conn.cursor()
        documents = []

        try:
            # 1. SOD Rules
            for rule_key, rule_data in sod_config.get('conflict_rules', {}).items():
                rule_id = rule_data.get('rule_id', f"SOD-{rule_key.upper()}")
                content = f"""
SOD Rule: {rule_data.get('name', rule_key)}
Principle: {rule_data.get('principle', '')}
Description: {rule_data.get('description', '')}
Categories: {rule_data.get('category1', '')} vs {rule_data.get('category2', '')}

This rule detects conflicts between permissions in these categories based on access levels.
The conflict severity varies by level combination (View, Create, Edit, Full).
"""
                documents.append({
                    'doc_id': f'sod_rule_{rule_id}',
                    'doc_type': 'SOD_RULE',
                    'title': rule_data.get('name', rule_key),
                    'content': content.strip(),
                    'reference_id': rule_id,
                    'reference_table': 'sod_rules',
                    'category': rule_data.get('category1', '')
                })

            # 2. Compensating Controls
            for control_id, control_data in controls_data.get('controls', {}).items():
                content = f"""
Compensating Control: {control_data.get('name', control_id)}
Type: {control_data.get('type', '')}
Description: {control_data.get('description', '')}

Effectiveness: {control_data.get('effectiveness', {}).get('risk_reduction_percentage', 0)}% risk reduction
Annual Cost: {control_data.get('costs', {}).get('annual_cost_estimate', 'N/A')}

This control helps mitigate SOD conflicts by {control_data.get('description', '').lower()}
"""
                documents.append({
                    'doc_id': f'control_{control_id}',
                    'doc_type': 'COMPENSATING_CONTROL',
                    'title': control_data.get('name', control_id),
                    'content': content.strip(),
                    'reference_id': control_id,
                    'reference_table': 'compensating_controls',
                    'category': control_data.get('type', '')
                })

            # 3. Job Role Mappings
            for job_role_id, role_data in job_roles_data.get('job_roles', {}).items():
                content = f"""
Job Role: {role_data.get('title', job_role_id)}
Department: {role_data.get('department', '')}
Business Justification: {role_data.get('business_justifications', '')}

Typical NetSuite Roles: {', '.join([r.get('role', '') for r in role_data.get('typical_netsuite_roles', [])])}

This job role typically requires these NetSuite roles to perform their duties.
Conflicts may be acceptable with appropriate compensating controls.
"""
                documents.append({
                    'doc_id': f'job_role_{job_role_id}',
                    'doc_type': 'JOB_ROLE',
                    'title': role_data.get('title', job_role_id),
                    'content': content.strip(),
                    'reference_id': job_role_id,
                    'reference_table': 'job_role_mappings',
                    'category': role_data.get('department', '')
                })

            # 4. Resolution Strategies
            for rule_key, rule_data in sod_config.get('conflict_rules', {}).items():
                for severity, strategy in rule_data.get('resolution_strategies', {}).items():
                    if severity == 'OK':
                        continue

                    content = f"""
Resolution Strategy for {severity} Severity Conflicts
Rule: {rule_data.get('name', rule_key)}

Action: {strategy.get('action', '')}
Required Controls: {', '.join(strategy.get('required_controls', []))}
Alternative Strategies: {', '.join(strategy.get('alternative_strategies', []))}

{strategy.get('description', '')}
"""
                    documents.append({
                        'doc_id': f'resolution_{rule_key}_{severity}',
                        'doc_type': 'RESOLUTION_STRATEGY',
                        'title': f"{severity} Resolution for {rule_data.get('name', rule_key)}",
                        'content': content.strip(),
                        'reference_id': rule_data.get('rule_id', f"SOD-{rule_key.upper()}"),
                        'reference_table': 'sod_rules',
                        'category': severity
                    })

            logger.info(f"Generating embeddings for {len(documents)} documents...")

            # Generate embeddings and insert
            for doc in documents:
                # Create embedding using embedding service
                embedding_array = self.embedding_service.embed_text(doc['content'], cache_key=doc['doc_id'])
                embedding = embedding_array.tolist()  # Convert to list for PostgreSQL

                cursor.execute("""
                    INSERT INTO knowledge_base_documents (
                        id, doc_id, doc_type, title, content,
                        reference_id, reference_table,
                        embedding, category
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    str(uuid.uuid4()),  # Generate UUID for id column
                    doc['doc_id'],
                    doc['doc_type'],
                    doc['title'],
                    doc['content'],
                    doc['reference_id'],
                    doc['reference_table'],
                    embedding,
                    doc['category']
                ))

                if len(documents) <= 10 or documents.index(doc) % 10 == 0:
                    logger.info(f"  Generated embedding for: {doc['title']}")

            self.conn.commit()
            logger.info(f"✓ Created {len(documents)} knowledge base documents with embeddings")

        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ Failed to create knowledge base embeddings: {e}")
            raise

    def seed_all(self, reset: bool = False):
        """Seed all configurations to database"""
        logger.info("=" * 60)
        logger.info("SOD Configuration Seeding Started")
        logger.info("=" * 60)

        try:
            # Connect to database
            self.connect()

            # Apply schema extensions first
            self.execute_schema_extensions()

            # Reset tables if requested
            if reset:
                self.reset_configuration_tables()
                # Re-apply schema after reset
                self.execute_schema_extensions()

            # Load configuration files
            sod_config = self.load_json_file(SOD_CONFIG_FILE)
            controls_data = self.load_json_file(CONTROLS_FILE)
            job_roles_data = self.load_json_file(JOB_ROLES_FILE)

            # Seed data to PostgreSQL
            self.seed_permission_categories(sod_config)
            self.seed_sod_rules(sod_config)
            self.seed_compensating_controls(controls_data)
            self.seed_control_packages(controls_data)
            self.seed_job_role_mappings(job_roles_data)

            # Create knowledge base embeddings
            self.create_knowledge_base_embeddings(sod_config, controls_data, job_roles_data)

            logger.info("=" * 60)
            logger.info("✓ SOD Configuration Seeding Complete!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"✗ Seeding failed: {e}")
            raise
        finally:
            self.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Seed SOD configurations to database')
    parser.add_argument('--reset', action='store_true', help='Reset configuration tables before seeding')
    args = parser.parse_args()

    # Check configuration files exist
    for filepath in [SOD_CONFIG_FILE, CONTROLS_FILE, JOB_ROLES_FILE]:
        if not filepath.exists():
            logger.error(f"✗ Configuration file not found: {filepath}")
            sys.exit(1)

    # Create seeder and run
    seeder = SODConfigSeeder(DATABASE_URL)
    try:
        seeder.seed_all(reset=args.reset)
    except Exception as e:
        logger.error(f"✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
