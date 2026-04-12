"""
Seed Job Role Mappings

Seeds the job_role_mappings table with data from data/job_role_mappings.json
"""

import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_config import DatabaseConfig
from repositories.job_role_mapping_repository import JobRoleMappingRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_job_role_mappings_json():
    """Load job role mappings from JSON file"""
    json_path = Path(__file__).parent.parent / "data" / "job_role_mappings.json"

    if not json_path.exists():
        raise FileNotFoundError(f"Job role mappings file not found: {json_path}")

    with open(json_path) as f:
        data = json.load(f)

    return data


def seed_job_role_mappings():
    """Seed job role mappings table from JSON"""
    logger.info("=" * 80)
    logger.info("SEEDING JOB ROLE MAPPINGS")
    logger.info("=" * 80)

    # Initialize database
    db_config = DatabaseConfig()
    session = db_config.get_session()
    repo = JobRoleMappingRepository(session)

    # Load JSON data
    data = load_job_role_mappings_json()
    job_roles = data.get('job_roles', {})

    logger.info(f"Found {len(job_roles)} job role definitions in JSON")

    seeded_count = 0
    updated_count = 0
    skipped_count = 0

    for role_key, role_data in job_roles.items():
        try:
            job_title = role_data.get('title')
            department = role_data.get('department', '')
            description = role_data.get('description', '')

            if not job_title:
                logger.warning(f"Skipping {role_key}: No job title")
                skipped_count += 1
                continue

            # Extract acceptable role combinations
            acceptable_combos = role_data.get('acceptable_role_combinations', [])
            typical_roles = role_data.get('typical_netsuite_roles', [])

            # Find first combination that requires controls (for typical_controls)
            typical_controls = []
            business_justification = ""
            requires_controls = False

            if acceptable_combos:
                for combo in acceptable_combos:
                    if combo.get('requires_compensating_controls'):
                        typical_controls = combo.get('typical_controls', [])
                        business_justification = combo.get('business_justification', '')
                        requires_controls = True
                        break

                # If no combo requires controls, use first combo's justification
                if not business_justification and acceptable_combos:
                    business_justification = acceptable_combos[0].get('business_justification', '')

            # Check if already exists
            existing = repo.get_by_job_title(job_title)

            if existing:
                logger.info(f"✅ Job role mapping already exists: {job_title}")
                # Update it
                repo.update(str(existing.id), {
                    'department': department,
                    'acceptable_role_combinations': acceptable_combos,
                    'business_justification': business_justification,
                    'requires_compensating_controls': requires_controls,
                    'typical_controls': typical_controls,
                    'metadata': {
                        'typical_netsuite_roles': typical_roles,
                        'source_key': role_key
                    }
                })
                updated_count += 1
            else:
                # Create new mapping
                mapping_data = {
                    'job_role_id': f"jr_{role_key}",
                    'job_title': job_title,
                    'department': department,
                    'typical_netsuite_roles': typical_roles,  # Add this for NOT NULL constraint
                    'acceptable_role_combinations': acceptable_combos,
                    'business_justification': business_justification,
                    'requires_compensating_controls': requires_controls,
                    'typical_controls': typical_controls,
                    'is_active': True,
                    'metadata_col': {  # Use metadata_col to match model
                        'source_key': role_key,
                        'level': role_data.get('level', ''),
                        'reports_to': role_data.get('reports_to', ''),
                        'description': description
                    }
                }

                repo.create(mapping_data)
                logger.info(f"✅ Created job role mapping: {job_title}")
                seeded_count += 1

        except Exception as e:
            logger.error(f"❌ Error processing {role_key}: {str(e)}")
            skipped_count += 1
            continue

    logger.info("=" * 80)
    logger.info("JOB ROLE MAPPING SEED COMPLETE")
    logger.info(f"✅ Created: {seeded_count}")
    logger.info(f"🔄 Updated: {updated_count}")
    logger.info(f"⏭️  Skipped: {skipped_count}")
    logger.info(f"📊 Total: {seeded_count + updated_count + skipped_count}")
    logger.info("=" * 80)

    # Verify seeding
    all_mappings = repo.get_all_active()
    logger.info(f"\n✅ Verification: {len(all_mappings)} active job role mappings in database")

    # Show what we seeded
    logger.info("\nSeeded Job Titles:")
    for mapping in all_mappings:
        logger.info(f"  • {mapping.job_title} ({mapping.department})")

    return seeded_count, updated_count


if __name__ == "__main__":
    try:
        seeded, updated = seed_job_role_mappings()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error during seeding: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
