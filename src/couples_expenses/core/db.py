"""SQLite data layer – no ORM, stdlib sqlite3 only."""

import sqlite3
from datetime import datetime
from pathlib import Path

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    amount_cents INTEGER NOT NULL,
    description TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    is_essential INTEGER NOT NULL DEFAULT 0,
    paid_by     TEXT    NOT NULL,
    expense_ts  TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    """Create the expenses table if it doesn't exist."""
    conn = _connect(db_path)
    try:
        conn.execute(_CREATE_TABLE)
        conn.commit()
    finally:
        conn.close()


def add_expense(
    db_path: Path,
    amount_cents: int,
    description: str,
    category: str,
    is_essential: bool,
    paid_by: str,
    expense_ts: str,
) -> int:
    """Insert an expense row. Returns the new row id."""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO expenses "
            "(amount_cents, description, category, is_essential, paid_by, expense_ts, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (amount_cents, description, category, int(is_essential), paid_by, expense_ts, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_expenses(
    db_path: Path,
    year_month: str | None = None,
    category: str | None = None,
    paid_by: str | None = None,
) -> list[dict]:
    """Return expenses matching optional filters, newest first."""
    clauses: list[str] = []
    params: list[str] = []

    if year_month:
        # year_month like '2026-02'
        clauses.append("substr(expense_ts, 1, 7) = ?")
        params.append(year_month)
    if category:
        clauses.append("category = ?")
        params.append(category)
    if paid_by:
        clauses.append("paid_by = ?")
        params.append(paid_by)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM expenses{where} ORDER BY expense_ts DESC"

    conn = _connect(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_expense(db_path: Path, expense_id: int) -> None:
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
    finally:
        conn.close()


def get_month_summary(db_path: Path, year_month: str) -> dict:
    """Return summary dict for a given YYYY-MM month."""
    rows = list_expenses(db_path, year_month=year_month)

    total_cents = 0
    by_category: dict[str, int] = {}
    by_partner: dict[str, int] = {}

    for r in rows:
        amt = r["amount_cents"]
        total_cents += amt
        cat = r["category"]
        by_category[cat] = by_category.get(cat, 0) + amt
        p = r["paid_by"]
        by_partner[p] = by_partner.get(p, 0) + amt

    return {
        "total_cents": total_cents,
        "by_category_cents": by_category,
        "by_partner_cents": by_partner,
    }
