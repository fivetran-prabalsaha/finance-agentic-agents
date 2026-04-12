# Database Seeding: SOD Configurations

**Date**: 2026-02-12
**Status**: ✅ Complete

---

## Overview

This document describes the database seeding process for SOD (Segregation of Duties) configurations, compensating controls, job role mappings, and knowledge base embeddings.

All configuration data from JSON files has been loaded into PostgreSQL with pgvector embeddings for semantic search.

---

## What Was Seeded

### 1. **SOD Rules** → `sod_rules` table
- **Count**: 6 level-based conflict rules
- **Source**: `data/netsuite_sod_config_unified.json`
- **Key Features**:
  - Level-based conflict matrices (5×5 for each rule)
  - Resolution strategies for each severity (OK, LOW, MED, HIGH, CRIT)
  - Principle descriptions (e.g., "SOD-001: Maker-Checker Segregation")
  - Category mappings (transaction_entry vs transaction_approval)

**Example Rules**:
- `SOD-RULE-001`: Transaction Entry vs Transaction Approval
- `SOD-RULE-002`: Transaction Entry vs Payment Processing
- `SOD-RULE-003`: Payment Processing vs Bank Reconciliation
- `SOD-RULE-004`: Vendor Setup vs Payment Processing
- `SOD-RULE-005`: User Administration vs Transaction Processing
- `SOD-RULE-006`: User Admin vs Role Admin (Privilege Escalation)

### 2. **Compensating Controls** → `compensating_controls` table
- **Count**: 12 individual controls
- **Source**: `data/compensating_controls.json`
- **Key Features**:
  - Risk reduction percentages (30%-80%)
  - Control types (PREVENTIVE, DETECTIVE)
  - Implementation steps and requirements
  - Annual cost estimates

**Example Controls**:
- Segregated Workflows (70% risk reduction, $5K/year)
- Dual Approval Workflow (60% risk reduction, $15K/year)
- Transaction Limits (40% risk reduction, $2K/year)
- Real-Time Monitoring (50% risk reduction, $20K/year)
- CEO/CFO Approval (50% risk reduction, $10K/year)

### 3. **Control Packages** → `control_packages` table
- **Count**: 6 pre-configured packages
- **Source**: `data/compensating_controls.json`
- **Key Features**:
  - Bundled controls for different risk levels
  - Total risk reduction calculations
  - Cost estimates and implementation time

**Packages**:
- Low Risk Package (70% reduction, $3K/year)
- Medium Risk Package (80% reduction, $15K/year)
- High Risk Package (85% reduction, $45K/year)
- Critical Risk Package (90% reduction, $100K/year)
- Executive Access Package (85% reduction, $80K/year)
- Developer Access Package (85% reduction, $30K/year)

### 4. **Job Role Mappings** → `job_role_mappings` table
- **Count**: 10 job roles
- **Source**: `data/job_role_mappings.json`
- **Key Features**:
  - Typical NetSuite role combinations
  - Acceptable role combinations with business justifications
  - Typical resolution strategies
  - Required controls for each role

**Job Roles**:
1. Revenue Director
2. Accounts Payable Manager
3. Accounts Receivable Manager
4. Controller
5. Senior Accountant
6. Tax Manager
7. Financial Analyst
8. Billing Specialist
9. Accounting Manager
10. System Administrator

### 5. **Permission Categories** → `permission_categories` table
- **Count**: 7 categories
- **Source**: `data/netsuite_sod_config_unified.json`
- **Key Features**:
  - Base risk scores for each category
  - Level-specific risk adjustments

**Categories**:
- transaction_entry
- transaction_approval
- transaction_payment
- bank_reconciliation
- vendor_setup
- user_admin
- role_admin

### 6. **Knowledge Base Documents** → `knowledge_base_documents` table with pgvector embeddings
- **Count**: 49 documents with 384-dimensional embeddings
- **Purpose**: Enable semantic search for the Knowledge Base Agent
- **Embedding Model**: HuggingFace `sentence-transformers/all-MiniLM-L6-v2`

**Document Types**:
- `SOD_RULE` (6 docs): Complete rule descriptions with principles
- `COMPENSATING_CONTROL` (12 docs): Control descriptions and effectiveness
- `JOB_ROLE` (10 docs): Job role mappings and typical roles
- `RESOLUTION_STRATEGY` (21 docs): Strategies for each severity level

---

## Seeding Script

**Location**: `scripts/seed_sod_configurations.py`

### Usage

```bash
# Seed all configurations (safe - uses ON CONFLICT for updates)
python3 scripts/seed_sod_configurations.py

# Reset configuration tables and seed fresh
python3 scripts/seed_sod_configurations.py --reset
```

### What the Script Does

1. **Connects to PostgreSQL** using credentials from `.env`
2. **Applies schema extensions** if not already applied
3. **Seeds data** from JSON configuration files:
   - Permission categories
   - SOD rules with level-based matrices
   - Compensating controls
   - Control packages
   - Job role mappings
4. **Generates embeddings** using HuggingFace sentence-transformers
5. **Creates knowledge base documents** with vector embeddings for semantic search

### Features

- **Idempotent**: Safe to run multiple times (uses `ON CONFLICT` for upserts)
- **Transactional**: Rolls back on errors
- **Logged**: Comprehensive logging at each step
- **Cached**: Embeddings are cached during generation
- **UUID Generation**: Automatically generates UUIDs for all records

---

## Verification

### Quick Check

```bash
python3 -c "
import psycopg2
conn = psycopg2.connect('postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db')
cursor = conn.cursor()

tables = [
    'sod_rules',
    'compensating_controls',
    'control_packages',
    'job_role_mappings',
    'permission_categories',
    'knowledge_base_documents'
]

print('=== Database Contents ===')
for table in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    print(f'{table:30s}: {count:3d} records')

conn.close()
"
```

**Expected Output**:
```
=== Database Contents ===
sod_rules                     :   6 records
compensating_controls         :  12 records
control_packages              :   6 records
job_role_mappings             :  10 records
permission_categories         :   7 records
knowledge_base_documents      :  49 records
```

### Detailed Verification

```bash
# Check SOD rules with level matrices
psql postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db -c \
  "SELECT rule_id, rule_name, principle, category1, category2 FROM sod_rules WHERE rule_id LIKE 'SOD-RULE-%'"

# Check compensating controls
psql postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db -c \
  "SELECT control_id, name, control_type, risk_reduction_percentage, annual_cost_estimate FROM compensating_controls"

# Check job roles
psql postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db -c \
  "SELECT job_title, department, typical_resolution_strategy FROM job_role_mappings"

# Check knowledge base documents by type
psql postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db -c \
  "SELECT doc_type, COUNT(*) as count FROM knowledge_base_documents GROUP BY doc_type"
```

---

## Using the Seeded Data

### 1. Query SOD Rules

```sql
-- Get all level-based SOD rules
SELECT
    rule_id,
    rule_name,
    principle,
    category1,
    category2,
    base_risk_score,
    jsonb_pretty(level_conflict_matrix) as matrix
FROM sod_rules
WHERE level_conflict_matrix IS NOT NULL;

-- Get resolution strategies for CRITICAL conflicts
SELECT
    rule_id,
    rule_name,
    resolution_strategies->'CRIT' as critical_resolution
FROM sod_rules
WHERE resolution_strategies ? 'CRIT';
```

### 2. Query Compensating Controls

```sql
-- Get most effective controls
SELECT
    control_id,
    name,
    control_type,
    risk_reduction_percentage,
    annual_cost_estimate
FROM compensating_controls
ORDER BY risk_reduction_percentage DESC;

-- Get preventive controls
SELECT name, description, risk_reduction_percentage
FROM compensating_controls
WHERE control_type = 'PREVENTIVE'
ORDER BY risk_reduction_percentage DESC;
```

### 3. Query Control Packages

```sql
-- Get package for specific severity
SELECT
    package_name,
    included_control_ids,
    total_risk_reduction,
    estimated_annual_cost
FROM control_packages
WHERE severity_level = 'CRITICAL';
```

### 4. Query Job Role Mappings

```sql
-- Get roles requiring compensating controls
SELECT
    job_title,
    department,
    typical_resolution_strategy,
    typical_required_controls
FROM job_role_mappings
WHERE typical_resolution_strategy = 'compensating_controls';

-- Get acceptable role combinations for a job
SELECT
    job_title,
    jsonb_pretty(acceptable_role_combinations) as combos
FROM job_role_mappings
WHERE job_title = 'Revenue Director';
```

### 5. Semantic Search with pgvector

```sql
-- Find similar SOD rules (requires query embedding)
SELECT
    doc_type,
    title,
    content,
    1 - (embedding <=> '[your_query_embedding]') as similarity
FROM knowledge_base_documents
WHERE doc_type = 'SOD_RULE'
ORDER BY embedding <=> '[your_query_embedding]'
LIMIT 5;

-- Get all documents for a specific category
SELECT doc_type, title
FROM knowledge_base_documents
WHERE category = 'transaction_entry'
ORDER BY doc_type, title;
```

---

## Knowledge Base Agent Integration

The knowledge base agent can now query the seeded data using semantic search:

### Example Queries

**Query**: "What controls mitigate maker-checker conflicts?"

The agent will:
1. Generate embedding for the query
2. Search `knowledge_base_documents` for similar content
3. Return relevant SOD rules, controls, and resolution strategies

**Query**: "What roles does a Revenue Director typically need?"

The agent will:
1. Search job role mappings
2. Return typical NetSuite roles and business justifications
3. Suggest appropriate compensating controls if conflicts exist

**Query**: "How do I resolve a CRITICAL conflict?"

The agent will:
1. Find resolution strategies for CRITICAL severity
2. Return recommended control packages
3. Suggest alternative approaches (reduce levels, split roles, reject)

---

## Schema Details

### Extended Tables

The following tables were created by `database/schema_extensions.sql`:

1. **`compensating_controls`**
   - Individual controls with risk reduction percentages
   - Implementation guidance and costs

2. **`control_packages`**
   - Pre-configured bundles of controls
   - Mapped to severity levels

3. **`job_role_mappings`**
   - Job titles to NetSuite roles
   - Business justifications and typical controls

4. **`permission_categories`**
   - Categories with base risk scores
   - Level-specific risk adjustments

5. **`permission_levels`**
   - Level definitions (None=0, View=1, Create=2, Edit=3, Full=4)
   - Risk multipliers for each level

6. **`knowledge_base_documents`**
   - Documents with pgvector embeddings
   - Supports semantic search for Knowledge Base Agent

### Extended Columns on `sod_rules`

The existing `sod_rules` table was extended with:
- `principle`: SOD principle description
- `category1`, `category2`: Permission categories in conflict
- `base_risk_score`: Base risk score (0-100)
- `level_conflict_matrix`: 5×5 matrix with severity for each level combination
- `resolution_strategies`: Strategies for OK, LOW, MED, HIGH, CRIT

---

## Troubleshooting

### Issue: Script fails with "module not found"

**Solution**: Install dependencies
```bash
pip install psycopg2-binary sentence-transformers langchain-huggingface
```

### Issue: "relation already exists"

**Solution**: Schema extensions already applied. The script will automatically skip.

### Issue: Database connection refused

**Solution**: Check PostgreSQL is running and credentials in `.env` are correct
```bash
# Test connection
psql postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db -c "SELECT 1"
```

### Issue: Embedding generation is slow

**Solution**: This is normal for first run. HuggingFace downloads the model (~90MB) once.
- Model is cached in `~/.cache/huggingface/`
- Subsequent runs are much faster (~2-3 seconds)

---

## Re-seeding

To update configurations after changing JSON files:

```bash
# Just re-run the seeding script
python3 scripts/seed_sod_configurations.py

# The script uses ON CONFLICT DO UPDATE, so it will update existing records
```

To completely reset and re-seed:

```bash
# Drop configuration tables and re-seed
python3 scripts/seed_sod_configurations.py --reset
```

**Warning**: `--reset` will delete all existing data in configuration tables!

---

## Performance

- **Initial seeding**: ~10-15 seconds (including model loading and embedding generation)
- **Re-seeding**: ~3-5 seconds (model already loaded)
- **Embedding generation**: ~100ms per document (49 documents = ~5 seconds)
- **Database writes**: ~1-2 seconds total

---

## Next Steps

1. **Test Knowledge Base Agent**: Query the knowledge base using semantic search
2. **Run Level-Based Analysis**: Use seeded SOD rules for conflict detection
3. **Test Resolution Generation**: Generate compensating controls for detected conflicts
4. **Validate Job Role Mappings**: Ensure typical role combinations are accurate

---

## Related Documentation

- [`USAGE_GUIDE.md`](../USAGE_GUIDE.md): How to use level-based SOD analysis
- [`IMPLEMENTATION_COMPLETE.md`](../IMPLEMENTATION_COMPLETE.md): Complete implementation summary
- [`docs/ARCHITECTURE_LEVEL_BASED_SOD.md`](./ARCHITECTURE_LEVEL_BASED_SOD.md): Level-based architecture
- [`database/schema_extensions.sql`](../database/schema_extensions.sql): Database schema

---

**Status**: ✅ **Complete - All configurations seeded successfully!**
