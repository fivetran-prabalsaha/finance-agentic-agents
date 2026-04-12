# pgvector Setup Instructions

## Current Status

⚠️ **pgvector extension requires superuser privileges to install**

The migration script `004_pgvector_embeddings.sql` is ready but cannot be run without superuser access.

## Manual Installation Steps

### Option 1: Local Development (if you have superuser access)

```bash
# Connect as postgres superuser
psql -U postgres -d compliance_db

# Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

# Verify installation
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

# Exit
\q

# Run migration
python3 scripts/run_pgvector_migration.py
```

### Option 2: Request DBA to Install (Production)

Send this to your DBA:

```sql
-- Run as superuser on compliance_db database
CREATE EXTENSION IF NOT EXISTS vector;
```

Then run:
```bash
python3 scripts/run_pgvector_migration.py
```

### Option 3: Docker (Easiest for Development)

Use the provided docker-compose.yml which includes pgvector pre-installed:

```bash
# Start database with pgvector
docker-compose up -d postgres

# Run migration
python3 scripts/run_pgvector_migration.py
```

## Verification

Check if pgvector is installed:

```bash
python3 scripts/check_pgvector.py
```

## Fallback Mode

If pgvector cannot be installed, the system will work but with reduced functionality:
- ✓ All core features work (SOD detection, risk assessment, notifications)
- ✗ Semantic similarity search disabled
- ✗ Historical violation similarity disabled
- ✗ Exemption learning (Phase 3) disabled

## What the Migration Does

Once pgvector is enabled, the migration will:

1. **Enable pgvector extension**
2. **Add vector embedding columns** to:
   - `roles.embedding` (384 dimensions)
   - `sod_rules.embedding` (384 dimensions)
   - `violations.embedding` (384 dimensions)
3. **Create vector indexes** for fast similarity search (IVFFlat)
4. **Create `violation_exemptions` table** for Phase 3 learning loop
5. **Create helper functions** for similarity search
6. **Create `ground_truth_knowledge` view** combining rules and exemptions

## Next Steps

1. Install pgvector using one of the options above
2. Run the migration: `python3 scripts/run_pgvector_migration.py`
3. Initialize embeddings: `python3 scripts/initialize_embeddings.py` (to be created)
4. Run the enhanced demo: `python3 demos/demo_end_to_end.py`
