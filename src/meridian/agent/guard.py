"""SQL guardrails for model-generated queries.

Defence in depth:
1. Parse with sqlglot (DuckDB dialect). Unparseable SQL is rejected.
2. Exactly one statement, and it must be a read query (SELECT / UNION / WITH).
3. Every referenced table must be in the governed allowlist. CTE names are allowed.
4. Table functions and file access (read_csv, read_parquet, glob, ...) are rejected.
5. A LIMIT is enforced on the outer query.
6. The connection itself is opened read-only, so even a missed case cannot write.
"""
from __future__ import annotations

import sqlglot
from sqlglot import exp

from meridian.agent.catalog import TABLES

MAX_ROWS = 500
BLOCKED_FUNCTIONS = {
    "read_csv", "read_csv_auto", "read_parquet", "read_json", "read_json_auto", "read_text", "read_blob",
    "glob", "parquet_scan", "csv_scan", "sniff_csv", "query_table", "query", "getenv", "current_setting",
}


class GuardError(ValueError):
    """Raised when a query violates a guardrail. The message is safe to show to users."""


def validate_sql(sql: str, allowed_tables: set[str] | None = None, max_rows: int = MAX_ROWS) -> str:
    allowed = {t.lower() for t in (allowed_tables or TABLES)}
    try:
        statements = [s for s in sqlglot.parse(sql, read="duckdb") if s is not None]
    except sqlglot.errors.ParseError as err:
        raise GuardError(f"Query could not be parsed: {str(err).splitlines()[0]}") from err
    if len(statements) != 1:
        raise GuardError("Exactly one SQL statement is allowed.")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise GuardError(f"Only read queries are allowed, got {tree.key.upper()}.")

    cte_names = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if table.args.get("db") or table.args.get("catalog"):
            raise GuardError(f"Schema-qualified table '{table.sql()}' is not allowed.")
        if not name and isinstance(table.this, exp.Func):
            raise GuardError("Table functions are not allowed.")
        if name and name not in allowed and name not in cte_names:
            raise GuardError(f"Table '{name}' is not in the governed catalog.")
    for func in tree.find_all(exp.Func):
        fname = (func.sql_name() if not isinstance(func, exp.Anonymous) else func.name).lower()
        if fname in BLOCKED_FUNCTIONS:
            raise GuardError(f"Function '{fname}' is not allowed.")
    for node in tree.find_all(exp.Literal):
        if node.is_string and any(s in node.this.lower() for s in ("://", "/etc/", ".csv", ".parquet", ".duckdb")):
            raise GuardError("File paths and URLs are not allowed in queries.")

    limit = tree.args.get("limit")
    if limit is None or int(limit.expression.this) > max_rows:
        tree = tree.limit(max_rows)
    return tree.sql(dialect="duckdb")
