#!/usr/bin/env python3
"""
Ingest Role Internal Conflicts into Knowledge Base

Reads the role conflict analysis JSON and:
1. Inserts structured data into role_internal_conflicts table
2. Creates embeddings and stores in vector DB for semantic search
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from models.database_config import DatabaseConfig
from services.embedding_service import EmbeddingService


class RoleConflictIngestion:
    """Ingests role conflict data into database and vector store"""

    def __init__(self):
        self.db_config = DatabaseConfig()
        self.session = self.db_config.get_session()
        self.embedding_service = EmbeddingService()

    def ingest_from_json(self, json_file_path: str):
        """
        Ingest role conflicts from JSON analysis file

        Args:
            json_file_path: Path to the analysis JSON file
        """
        print("=" * 80)
        print("ROLE CONFLICT INGESTION TO KNOWLEDGE BASE")
        print("=" * 80)
        print()

        # Read JSON file
        print(f"📖 Reading analysis from: {json_file_path}")
        with open(json_file_path) as f:
            analysis_data = json.load(f)

        print(f"   Found {len(analysis_data)} roles in analysis")
        print()

        # Filter to roles with conflicts
        roles_with_conflicts = [r for r in analysis_data if r['conflicts']]
        print(f"   {len(roles_with_conflicts)} roles have conflicts")
        print()

        # Step 1: Insert structured data into database
        print("📊 Step 1: Inserting structured data into database...")
        self._insert_structured_data(roles_with_conflicts)
        print()

        # Step 2: Create and insert embeddings for vector search
        print("🧠 Step 2: Creating embeddings for vector search...")
        self._insert_vector_embeddings(roles_with_conflicts, analysis_data)
        print()

        print("=" * 80)
        print("✅ INGESTION COMPLETE")
        print("=" * 80)

    def _insert_structured_data(self, roles_with_conflicts: list[dict]):
        """Insert conflict data into role_internal_conflicts table"""

        # Clear existing data
        print("   Clearing existing conflict data...")
        self.session.execute(text("DELETE FROM role_internal_conflicts"))
        self.session.commit()

        # Insert new data
        insert_query = text("""
            INSERT INTO role_internal_conflicts
            (role_id, role_name, conflict_category, conflict_name, severity,
             pattern_description, permissions_involved, analysis_timestamp)
            VALUES
            (:role_id, :role_name, :conflict_category, :conflict_name, :severity,
             :pattern_description, :permissions_involved, :analysis_timestamp)
        """)

        total_conflicts = 0
        for role in roles_with_conflicts:
            for conflict in role['conflicts']:
                self.session.execute(insert_query, {
                    'role_id': role['role_id'],
                    'role_name': role['role_name'],
                    'conflict_category': conflict['category'],
                    'conflict_name': conflict['name'],
                    'severity': conflict['severity'],
                    'pattern_description': conflict['pattern'],
                    'permissions_involved': json.dumps({'pattern': conflict['pattern']}),
                    'analysis_timestamp': datetime.now()
                })
                total_conflicts += 1

        self.session.commit()
        print(f"   ✅ Inserted {total_conflicts} conflict records for {len(roles_with_conflicts)} roles")

    def _insert_vector_embeddings(self, roles_with_conflicts: list[dict], all_roles: list[dict]):
        """Create and insert embeddings into knowledge_base table"""

        documents = []

        # 1. Create embeddings for each role with conflicts
        print("   Creating role-level embeddings...")
        for role in roles_with_conflicts:
            # Create detailed description
            conflict_descriptions = []
            critical_count = sum(1 for c in role['conflicts'] if c['severity'] == 'CRITICAL')
            high_count = sum(1 for c in role['conflicts'] if c['severity'] == 'HIGH')

            severity_summary = []
            if critical_count > 0:
                severity_summary.append(f"{critical_count} CRITICAL")
            if high_count > 0:
                severity_summary.append(f"{high_count} HIGH")

            for conflict in role['conflicts']:
                conflict_descriptions.append(
                    f"- {conflict['name']} ({conflict['severity']}): {conflict['pattern']}"
                )

            doc_text = f"""Role: {role['role_name']}
Permission Count: {role['permission_count']}
Internal SOD Conflicts: {len(role['conflicts'])} ({', '.join(severity_summary)})

Conflicts Found:
{chr(10).join(conflict_descriptions)}

Risk Assessment: This role violates segregation of duties principles by combining conflicting permissions within a single role. Users assigned this role can perform actions that should require multiple people for proper controls.

Remediation: This role should be split into separate roles, each handling distinct responsibilities. Ensure different users are assigned to maker vs. checker roles."""

            documents.append({
                'content': doc_text,
                'metadata': {
                    'type': 'role_conflict_analysis',
                    'role_id': role['role_id'],
                    'role_name': role['role_name'],
                    'conflict_count': len(role['conflicts']),
                    'has_critical': critical_count > 0,
                    'severity_max': 'CRITICAL' if critical_count > 0 else 'HIGH'
                }
            })

        print(f"   Created {len(documents)} role-level embeddings")

        # 2. Create embeddings for conflict patterns (grouped)
        print("   Creating conflict pattern embeddings...")
        conflict_patterns = self._group_conflicts_by_pattern(roles_with_conflicts)

        for pattern_key, pattern_info in conflict_patterns.items():
            affected_roles = ", ".join(pattern_info['roles'][:5])
            if len(pattern_info['roles']) > 5:
                affected_roles += f", and {len(pattern_info['roles']) - 5} more"

            doc_text = f"""Conflict Pattern: {pattern_info['name']}
Category: {pattern_info['category']}
Severity: {pattern_info['severity']}
Pattern: {pattern_key}

Description: {self._get_pattern_description(pattern_info)}

Affected Roles ({len(pattern_info['roles'])}): {affected_roles}

Control Weakness: This pattern represents a fundamental segregation of duties violation where a single role can perform actions that should be separated across different individuals.

Remediation Strategy: {self._get_remediation_strategy(pattern_info['category'])}"""

            documents.append({
                'content': doc_text,
                'metadata': {
                    'type': 'conflict_pattern',
                    'category': pattern_info['category'],
                    'severity': pattern_info['severity'],
                    'pattern': pattern_key,
                    'affected_role_count': len(pattern_info['roles'])
                }
            })

        print(f"   Created {len(conflict_patterns)} conflict pattern embeddings")

        # 3. Create summary embedding
        print("   Creating summary embedding...")
        roles_with_no_conflicts = [r for r in all_roles if not r['conflicts']]

        summary_text = f"""Internal SOD Conflict Analysis Summary

Total Roles Analyzed: {len(all_roles)}
Roles with Conflicts: {len(roles_with_conflicts)} ({len(roles_with_conflicts)*100//len(all_roles)}%)
Roles without Conflicts: {len(roles_with_no_conflicts)} ({len(roles_with_no_conflicts)*100//len(all_roles)}%)

Most Problematic Roles:
{self._get_top_roles_summary(roles_with_conflicts)}

Common Conflict Categories:
- Maker-Checker Violations: Roles can both create and approve transactions
- 3-Way Match Bypass: Roles control multiple steps in procurement cycle
- Full Transaction Cycle Control: Roles control entire business process
- Cash Handling Conflicts: Roles combine cash transaction and reconciliation
- Admin + Financial Access: Roles combine system administration with financial transactions

Safe Roles (No Internal Conflicts):
{self._get_safe_roles_summary(roles_with_no_conflicts)}

Analysis Date: {datetime.now().strftime('%Y-%m-%d')}
"""

        documents.append({
            'content': summary_text,
            'metadata': {
                'type': 'role_analysis_summary',
                'total_roles': len(all_roles),
                'roles_with_conflicts': len(roles_with_conflicts),
                'analysis_date': datetime.now().isoformat()
            }
        })

        print("   Created 1 summary embedding")
        print()

        # Generate embeddings and insert
        print(f"   Generating embeddings for {len(documents)} documents...")
        for i, doc in enumerate(documents, 1):
            if i % 5 == 0:
                print(f"   Processing {i}/{len(documents)}...")

            embedding = self.embedding_service.embed_text(doc['content'])

            # Convert numpy array to list for PostgreSQL
            embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)

            # Generate unique doc_id
            doc_type = doc['metadata']['type']
            if doc_type == 'role_conflict_analysis':
                doc_id = f"role_conflict_{doc['metadata']['role_id']}"
                title = f"Internal SOD Conflicts: {doc['metadata']['role_name']}"
            elif doc_type == 'conflict_pattern':
                doc_id = f"pattern_{doc['metadata']['category']}_{i}"
                title = f"{doc['metadata']['category'].replace('_', ' ').title()} Pattern"
            else:
                doc_id = f"summary_{i}"
                title = "Internal SOD Analysis Summary"

            # Insert into knowledge_base_documents table
            insert_query = text("""
                INSERT INTO knowledge_base_documents
                (doc_id, doc_type, title, content, embedding, metadata, category)
                VALUES
                (:doc_id, :doc_type, :title, :content, CAST(:embedding AS vector), :metadata, :category)
            """)

            self.session.execute(insert_query, {
                'doc_id': doc_id,
                'doc_type': doc_type,
                'title': title,
                'content': doc['content'],
                'embedding': str(embedding_list),
                'metadata': json.dumps(doc['metadata']),
                'category': doc['metadata'].get('category', 'role_analysis')
            })

        self.session.commit()
        print(f"   ✅ Inserted {len(documents)} documents into vector knowledge base")

    def _group_conflicts_by_pattern(self, roles_with_conflicts: list[dict]) -> dict:
        """Group conflicts by pattern to create pattern-level embeddings"""
        patterns = {}

        for role in roles_with_conflicts:
            for conflict in role['conflicts']:
                pattern_key = conflict['pattern']

                if pattern_key not in patterns:
                    patterns[pattern_key] = {
                        'name': conflict['name'],
                        'category': conflict['category'],
                        'severity': conflict['severity'],
                        'roles': []
                    }

                patterns[pattern_key]['roles'].append(role['role_name'])

        return patterns

    def _get_pattern_description(self, pattern_info: dict) -> str:
        """Get detailed description for a conflict pattern"""
        category = pattern_info['category']

        descriptions = {
            'maker_checker': 'This pattern violates the maker-checker principle by allowing a single role to both initiate and approve the same type of transaction. This creates opportunity for fraud or errors to go undetected.',
            'three_way_match': 'This pattern allows a single role to control multiple steps in the procurement three-way match process (Purchase Order, Receipt, Invoice). This bypasses the control that ensures goods received match what was ordered and invoiced.',
            'full_cycle': 'This pattern gives a single role control over an entire transaction lifecycle from initiation through completion and payment. This concentrates too much power and eliminates independent verification.',
            'cash_handling': 'This pattern combines cash-related transaction processing with reconciliation or verification duties, creating opportunities for misappropriation.',
            'admin_financial': 'This pattern combines system/user administration privileges with financial transaction authority, allowing potential manipulation of both access controls and financial data.'
        }

        return descriptions.get(category, 'This pattern represents a segregation of duties conflict.')

    def _get_remediation_strategy(self, category: str) -> str:
        """Get remediation strategy for a conflict category"""
        strategies = {
            'maker_checker': 'Split this role into two separate roles: a "Maker" role with create/edit permissions and a "Checker" role with approval/payment permissions. Ensure different users are assigned to each role.',
            'three_way_match': 'Separate procurement duties across three roles: one for Purchase Orders, one for Receiving, and one for Invoice Processing. This ensures independent verification at each step.',
            'full_cycle': 'Break down this role into separate roles for each major step in the transaction cycle. Assign different users to handle initiation, processing, approval, and payment stages.',
            'cash_handling': 'Separate cash handling from reconciliation duties. Create distinct roles for cash transaction processing and bank reconciliation, assigned to different users.',
            'admin_financial': 'Strictly separate administrative/IT functions from financial transaction processing. System administrators should not have access to create or approve financial transactions.'
        }

        return strategies.get(category, 'Split this role into separate functions and assign to different users.')

    def _get_top_roles_summary(self, roles_with_conflicts: list[dict]) -> str:
        """Generate summary of most problematic roles"""
        sorted_roles = sorted(roles_with_conflicts, key=lambda x: len(x['conflicts']), reverse=True)

        lines = []
        for role in sorted_roles[:5]:
            lines.append(f"- {role['role_name']}: {len(role['conflicts'])} conflicts")

        return "\n".join(lines)

    def _get_safe_roles_summary(self, safe_roles: list[dict]) -> str:
        """Generate summary of safe roles"""
        # Get roles sorted by permission count
        sorted_roles = sorted(safe_roles, key=lambda x: x['permission_count'], reverse=True)

        lines = []
        for role in sorted_roles[:10]:
            lines.append(f"- {role['role_name']} ({role['permission_count']} permissions)")

        return "\n".join(lines)


if __name__ == "__main__":
    # Find the most recent analysis file
    output_dir = Path("output/role_analysis")

    if not output_dir.exists():
        print("❌ Error: No analysis output directory found")
        print("   Run: python3 scripts/analyze_all_roles_internal_sod.py first")
        sys.exit(1)

    # Get most recent file
    analysis_files = list(output_dir.glob("all_roles_internal_sod_*.json"))

    if not analysis_files:
        print("❌ Error: No analysis files found")
        print("   Run: python3 scripts/analyze_all_roles_internal_sod.py first")
        sys.exit(1)

    most_recent = max(analysis_files, key=lambda p: p.stat().st_mtime)

    print(f"Using analysis file: {most_recent}")
    print()

    # Run ingestion
    ingestion = RoleConflictIngestion()
    ingestion.ingest_from_json(str(most_recent))
