#!/usr/bin/env python3
"""
Phase C backfill script — embed_corrections.py

Reads all existing NEGATIVE rows from answer_feedback that have a correction
but no embedding yet in correction_embeddings, then calls CorrectionService
to embed and store them.

Usage:
    cd compliance-agent
    python3 scripts/embed_corrections.py

    # Dry run (shows count without writing):
    python3 scripts/embed_corrections.py --dry-run

    # Limit (first N rows, for testing):
    python3 scripts/embed_corrections.py --limit 10
"""
import sys
import os
import argparse
import logging

# Make compliance-agent the working module root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Backfill correction embeddings")
    parser.add_argument("--dry-run", action="store_true", help="Print count, do not write")
    parser.add_argument("--limit", type=int, default=0, help="Max rows to process (0=all)")
    args = parser.parse_args()

    from models.database_config import DatabaseConfig
    from sqlalchemy import text as sqla_text

    session = DatabaseConfig().get_session()

    # Find answer_feedback rows that have a correction but no entry in correction_embeddings
    q = """
        SELECT
            af.run_id,
            af.user_email,
            af.query_preview,
            af.correction,
            af.tool_called
        FROM answer_feedback af
        WHERE
            af.correction IS NOT NULL
            AND af.correction != ''
            AND NOT EXISTS (
                SELECT 1 FROM correction_embeddings ce
                WHERE ce.run_id = af.run_id
            )
        ORDER BY af.created_at ASC
    """
    if args.limit > 0:
        q += f"\nLIMIT {args.limit}"

    rows = session.execute(sqla_text(q)).fetchall()
    session.close()

    logger.info(f"Found {len(rows)} corrections to embed")

    if args.dry_run:
        for r in rows:
            print(f"  run_id={r.run_id}  user={r.user_email}  preview={r.query_preview[:60]!r}")
        print(f"\nDry run complete — {len(rows)} row(s) would be embedded.")
        return

    from services.correction_service import store_correction

    ok = 0
    fail = 0
    for r in rows:
        try:
            store_correction(
                run_id=r.run_id or "",
                user_email=r.user_email,
                query_preview=r.query_preview or "",
                correction=r.correction,
                tool_called=r.tool_called,
            )
            ok += 1
            logger.info(f"  Embedded run={r.run_id} user={r.user_email}")
        except Exception as e:
            fail += 1
            logger.warning(f"  Failed run={r.run_id}: {e}")

    print(f"\nBackfill complete — {ok} embedded, {fail} failed.")


if __name__ == "__main__":
    main()
