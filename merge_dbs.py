"""
One-time DB merge utility for VoiceSQL.

Usage (from project root, with venv active):

    python merge_dbs.py

This copies customer / analytics tables from the trends DB
(TRENDS_DB_PATH, usually kirana.db) into the core DB
(DB_PATH, usually kirana_trends.db), without touching
inventory or transactions.

Run this once, verify things look correct, then you can
point both DB_PATH and TRENDS_DB_PATH at the same file
(e.g. kirana_trends.db) in your .env.
"""

import sqlite3
from pathlib import Path

from config import DB_PATH, TRENDS_DB_PATH


TABLES_TO_COPY = [
    # Customer master + orders
    "customers",
    "orders",
    # Analytics / predictions
    "predicted_orders",
    "customer_segments",
    "basket_pairs",
]


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute("PRAGMA table_info(%s)" % table)
    cols = cur.fetchall()
    return bool(cols)


def clone_table_schema(src: sqlite3.Connection, dst: sqlite3.Connection, table: str) -> None:
    """Create table in dst using the CREATE TABLE from src, if needed."""
    if table_exists(dst, table):
        return

    cur = src.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    row = cur.fetchone()
    if not row or not row[0]:
        return

    dst.execute(row[0])


def copy_table(src: sqlite3.Connection, dst: sqlite3.Connection, table: str) -> int:
    """Copy all rows from src.table into dst.table using INSERT OR IGNORE.

    Returns number of rows inserted into dst.
    """
    if not table_exists(src, table):
        print(f"⚠️  Source DB has no table '{table}', skipping.")
        return 0

    # Ensure destination has the schema
    clone_table_schema(src, dst, table)

    # Get column list from source
    cur = src.execute("PRAGMA table_info(%s)" % table)
    cols = [r[1] for r in cur.fetchall()]
    col_list = ", ".join(cols)

    sql = f"INSERT OR IGNORE INTO {table} ({col_list}) SELECT {col_list} FROM main.{table}"

    # Attach source as "main" and destination as current connection
    # (we're using src as a separate connection, so run the SELECT on src
    # and bulk-insert into dst).
    src_cur = src.execute(f"SELECT {col_list} FROM {table}")
    rows = src_cur.fetchall()
    if not rows:
        print(f"ℹ️  No rows to copy for '{table}'.")
        return 0

    placeholders = ", ".join(["?"] * len(cols))
    insert_sql = f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})"

    dst.executemany(insert_sql, rows)
    return dst.total_changes


def main() -> None:
    src_path = Path(TRENDS_DB_PATH)
    dst_path = Path(DB_PATH)

    print(f"Source (trends) DB:      {src_path}")
    print(f"Destination (core) DB:  {dst_path}")

    if not src_path.exists():
        raise SystemExit(f"Source DB not found: {src_path}")
    if not dst_path.exists():
        raise SystemExit(f"Destination DB not found: {dst_path}")

    src = sqlite3.connect(str(src_path))
    dst = sqlite3.connect(str(dst_path))

    try:
        total_inserted = 0
        # Copy in dependency-safe order: customers → orders → analytics tables
        for table in TABLES_TO_COPY:
            print(f"\n→ Copying table '{table}'...")
            inserted = copy_table(src, dst, table)
            dst.commit()
            print(f"   Inserted {inserted} rows into '{table}'.")
            total_inserted += inserted

        print("\n✅ Merge complete. Total rows inserted:", total_inserted)
        print("You can now optionally point TRENDS_DB_PATH to the same file as DB_PATH in .env.")
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    main()
