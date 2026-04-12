#!/usr/bin/env python3
"""Check if pgvector is installed"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
database_url = os.getenv('DATABASE_URL')

engine = create_engine(database_url)

with engine.connect() as connection:
    # Check for pgvector
    result = connection.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'"))
    row = result.fetchone()

    if row:
        print(f"✓ pgvector is installed: version {row[1]}")
        sys.exit(0)
    else:
        print("✗ pgvector extension not found")
        print("\nTo install pgvector, run as superuser:")
        print("  CREATE EXTENSION vector;")
        sys.exit(1)
