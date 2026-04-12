#!/usr/bin/env python3
"""
Create Sanitized Demo User

Creates a test user based on Robin Turner's profile with sanitized data
for external demos (no Fivetran branding)
"""

import json
import os
import sys
import uuid
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from models.database import (
    Role,
    User,
    UserRole,
    UserStatus,
    Violation,
    ViolationStatus,
)
from models.database_config import get_db_config


def sanitize_text(text_value):
    """Remove Fivetran branding from text"""
    if not text_value:
        return text_value

    replacements = {
        'Fivetran - ': '',
        'Fivetran : ': '',
        'fivetran.com': 'xyz.com',
        'Fivetran': 'Company',
        'fivetran': 'company'
    }

    result = text_value
    for old, new in replacements.items():
        result = result.replace(old, new)

    return result


def sanitize_json_field(json_value):
    """Sanitize JSON arrays (for role names in violations)"""
    if not json_value:
        return json_value

    if isinstance(json_value, str):
        try:
            json_value = json.loads(json_value)
        except:
            return sanitize_text(json_value)

    if isinstance(json_value, list):
        return [sanitize_text(item) for item in json_value]
    elif isinstance(json_value, dict):
        return {k: sanitize_text(v) if isinstance(v, str) else v
                for k, v in json_value.items()}

    return json_value


def create_sanitized_roles(session, original_roles):
    """
    Create sanitized versions of roles if they don't exist

    Args:
        session: Database session
        original_roles: List of original role objects

    Returns:
        List of sanitized role objects
    """
    sanitized_roles = []

    for original_role in original_roles:
        # Sanitize role name
        sanitized_name = sanitize_text(original_role.role_name)

        # Check if sanitized role already exists
        existing_role = session.query(Role).filter(
            Role.role_name == sanitized_name
        ).first()

        if existing_role:
            sanitized_roles.append(existing_role)
            print(f"   Using existing sanitized role: {sanitized_name}")
        else:
            # Create new sanitized role
            new_role = Role(
                id=uuid.uuid4(),
                role_id=f"demo_{sanitized_name.lower().replace(' ', '_')}",
                role_name=sanitized_name,
                is_custom=original_role.is_custom,
                description=sanitize_text(original_role.description) if original_role.description else None,
                permission_count=original_role.permission_count,
                permissions=original_role.permissions
            )
            session.add(new_role)
            sanitized_roles.append(new_role)
            print(f"   Created sanitized role: {sanitized_name}")

    session.commit()
    return sanitized_roles


def create_demo_user(source_email='robin.turner@fivetran.com',
                     demo_email='test_user@xyz.com',
                     demo_name='Test User'):
    """
    Create a demo user based on an existing user with sanitized data

    Args:
        source_email: Email of user to copy from
        demo_email: Email for demo user
        demo_name: Name for demo user
    """
    session = get_db_config().get_session()

    try:
        print(f"\n{'='*60}")
        print(f"Creating Demo User: {demo_name} ({demo_email})")
        print(f"Source: {source_email}")
        print(f"{'='*60}\n")

        # 1. Get source user
        print("Step 1: Fetching source user...")
        source_user = session.query(User).filter(User.email == source_email).first()

        if not source_user:
            print(f"❌ Source user not found: {source_email}")
            return

        print(f"✅ Found source user: {source_user.name}")

        # 2. Check if demo user already exists
        print("\nStep 2: Checking for existing demo user...")
        existing_demo_user = session.query(User).filter(User.email == demo_email).first()

        if existing_demo_user:
            print("⚠️  Demo user already exists. Deleting old user...")
            # Delete old violations first (FK constraint)
            session.query(Violation).filter(Violation.user_id == existing_demo_user.id).delete()
            session.query(UserRole).filter(UserRole.user_id == existing_demo_user.id).delete()
            session.delete(existing_demo_user)
            session.commit()
            print("✅ Deleted old demo user")

        # 3. Create sanitized demo user
        print("\nStep 3: Creating sanitized demo user...")
        demo_user = User(
            id=uuid.uuid4(),
            user_id=f"demo_{uuid.uuid4().hex[:8]}",
            internal_id=f"DEMO{uuid.uuid4().hex[:6].upper()}",
            name=demo_name,
            email=demo_email,
            status=UserStatus.ACTIVE,
            department=sanitize_text(source_user.department),
            subsidiary=sanitize_text(source_user.subsidiary) if source_user.subsidiary else None,
            employee_id=f"DEMO{uuid.uuid4().hex[:4].upper()}",
            job_function=source_user.job_function,
            business_unit=sanitize_text(source_user.business_unit) if source_user.business_unit else None,
            title=source_user.title,  # Keep title as-is
            supervisor=sanitize_text(source_user.supervisor) if source_user.supervisor else None,
            location=source_user.location,
            synced_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        session.add(demo_user)
        session.commit()
        print(f"✅ Created demo user: {demo_user.name}")
        print(f"   Email: {demo_user.email}")
        print(f"   Department: {demo_user.department}")

        # 4. Get source user's roles
        print("\nStep 4: Copying and sanitizing roles...")
        source_roles = session.query(Role).join(
            UserRole, UserRole.role_id == Role.id
        ).filter(
            UserRole.user_id == source_user.id
        ).all()

        print(f"   Source has {len(source_roles)} roles:")
        for role in source_roles:
            print(f"   • {role.role_name}")

        # 5. Create/get sanitized roles
        sanitized_roles = create_sanitized_roles(session, source_roles)

        # 6. Assign sanitized roles to demo user
        print("\nStep 5: Assigning roles to demo user...")
        for role in sanitized_roles:
            user_role = UserRole(
                id=uuid.uuid4(),
                user_id=demo_user.id,
                role_id=role.id,
                assigned_at=datetime.utcnow(),
                assigned_by="demo_script"
            )
            session.add(user_role)
            print(f"   ✓ Assigned: {role.role_name}")

        session.commit()

        # 7. Copy and sanitize violations
        print("\nStep 6: Copying and sanitizing violations...")
        source_violations = session.query(Violation).filter(
            Violation.user_id == source_user.id,
            Violation.status == ViolationStatus.OPEN
        ).all()

        print(f"   Found {len(source_violations)} violations to copy")

        violation_count = 0
        for source_v in source_violations:
            # Sanitize violation data
            sanitized_violation = Violation(
                id=uuid.uuid4(),
                user_id=demo_user.id,
                rule_id=source_v.rule_id,
                scan_id=source_v.scan_id,
                severity=source_v.severity,
                status=source_v.status,
                risk_score=source_v.risk_score,
                title=sanitize_text(source_v.title),
                description=sanitize_text(source_v.description),
                conflicting_roles=sanitize_json_field(source_v.conflicting_roles),
                conflicting_permissions=sanitize_json_field(source_v.conflicting_permissions),
                detected_at=datetime.utcnow(),
                violation_metadata=source_v.violation_metadata
            )
            session.add(sanitized_violation)
            violation_count += 1

        session.commit()
        print(f"✅ Copied {violation_count} violations with sanitized data")

        # 8. Summary
        print(f"\n{'='*60}")
        print("✅ Demo User Created Successfully!")
        print(f"{'='*60}")
        print("\nDemo User Details:")
        print(f"  Name:       {demo_user.name}")
        print(f"  Email:      {demo_user.email}")
        print(f"  Department: {demo_user.department}")
        print(f"  Title:      {demo_user.title}")
        print(f"  Roles:      {len(sanitized_roles)}")
        for role in sanitized_roles:
            print(f"    • {role.role_name}")
        print(f"  Violations: {violation_count}")

        # Count by severity
        severity_counts = {}
        for v in session.query(Violation).filter(Violation.user_id == demo_user.id).all():
            sev = v.severity.value
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if severity_counts:
            print("\n  Severity Breakdown:")
            for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if sev in severity_counts:
                    print(f"    • {sev}: {severity_counts[sev]}")

        print(f"\n{'='*60}")
        print("Test Commands:")
        print(f"{'='*60}")
        print("\nIn Claude UI, try:")
        print('  "Show me violations for test_user@xyz.com"')
        print(f'  "Generate violation report for {demo_email}"')
        print('  "List users in Finance department"')
        print("\nAll data will be sanitized (no Fivetran branding)!")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"❌ Error creating demo user: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()


def delete_demo_user(demo_email='test_user@xyz.com'):
    """Delete demo user and associated data"""
    session = get_db_config().get_session()

    try:
        print(f"\nDeleting demo user: {demo_email}")

        demo_user = session.query(User).filter(User.email == demo_email).first()

        if not demo_user:
            print(f"❌ Demo user not found: {demo_email}")
            return

        # Delete violations
        violation_count = session.query(Violation).filter(
            Violation.user_id == demo_user.id
        ).delete()

        # Delete user roles
        role_count = session.query(UserRole).filter(
            UserRole.user_id == demo_user.id
        ).delete()

        # Delete user
        session.delete(demo_user)
        session.commit()

        print("✅ Deleted demo user")
        print(f"   • {violation_count} violations")
        print(f"   • {role_count} role assignments")

    except Exception as e:
        print(f"❌ Error deleting demo user: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Manage demo users for external presentations')
    parser.add_argument('--create', action='store_true', help='Create demo user')
    parser.add_argument('--delete', action='store_true', help='Delete demo user')
    parser.add_argument('--source', default='robin.turner@fivetran.com', help='Source user email')
    parser.add_argument('--email', default='test_user@xyz.com', help='Demo user email')
    parser.add_argument('--name', default='Test User', help='Demo user name')

    args = parser.parse_args()

    if args.delete:
        delete_demo_user(args.email)
    elif args.create:
        create_demo_user(args.source, args.email, args.name)
    else:
        parser.print_help()
