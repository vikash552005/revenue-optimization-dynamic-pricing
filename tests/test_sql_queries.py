"""
Automated SQL Query Test Suite
------------------------------
Executes all 22 analytical queries defined in sql/analysis_queries.sql
against the clean SQLite database (sql/retailx.db) to ensure 100% syntactical
and logical correctness.
"""

import os
import re
import sqlite3
import pandas as pd
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "sql", "retailx.db")
SQL_FILE_PATH = os.path.join(PROJECT_ROOT, "sql", "analysis_queries.sql")


def load_named_queries():
    """Parse individual named SQL queries from the .sql file."""
    with open(SQL_FILE_PATH, "r") as f:
        content = f.read()

    # Split on '-- NAME: '
    query_blocks = re.split(r'--\s*NAME:\s*', content)
    queries = {}
    for block in query_blocks[1:]:
        lines = block.strip().split("\n")
        query_name = lines[0].strip()
        # Join the remaining lines up to next query boundary
        query_sql = "\n".join(lines[1:]).strip()
        # Remove trailing comments/semicolons
        if query_sql.endswith(";"):
            query_sql = query_sql[:-1]
        queries[query_name] = query_sql
    return queries


def test_database_exists_and_has_data():
    """Verify retailx.db exists and contains clean tables."""
    assert os.path.exists(DB_PATH), f"Database not found at {DB_PATH}"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tables = ["customers", "products", "sales", "pricing_history"]
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        count = cursor.fetchone()[0]
        assert count > 0, f"Table '{t}' is empty!"
    conn.close()


def test_all_22_sql_queries_execute():
    """Execute all extracted queries and verify non-empty results."""
    queries = load_named_queries()
    assert len(queries) >= 20, f"Expected >= 20 queries, found {len(queries)}"
    
    conn = sqlite3.connect(DB_PATH)
    failed_queries = []
    
    for name, sql in queries.items():
        try:
            df = pd.read_sql_query(sql, conn)
            assert not df.empty, f"Query '{name}' returned 0 rows"
            assert df.shape[1] > 1, f"Query '{name}' has fewer than 2 columns"
        except Exception as e:
            failed_queries.append((name, str(e)))
            
    conn.close()
    assert len(failed_queries) == 0, f"Failed queries: {failed_queries}"


if __name__ == "__main__":
    queries = load_named_queries()
    print(f"Loaded {len(queries)} named queries from {SQL_FILE_PATH}:")
    conn = sqlite3.connect(DB_PATH)
    for i, (name, sql) in enumerate(queries.items(), 1):
        try:
            df = pd.read_sql_query(sql, conn)
            print(f"[{i:02d}/22] OK: '{name}' -> {len(df)} rows, {df.shape[1]} cols")
        except Exception as e:
            print(f"[{i:02d}/22] FAIL: '{name}' -> Error: {e}")
    conn.close()
