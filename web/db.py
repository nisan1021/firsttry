"""SQLite data layer for the web app."""

import sqlite3
from datetime import datetime

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

CATEGORIES = ["רכב", "קניות אוכל", "קניות ביגוד", "אחרים"]
PARTNERS = ["בן/בת זוג A", "בן/בת זוג B"]

CATEGORY_COLORS = {
    "רכב": "#4e79a7",
    "קניות אוכל": "#f28e2b",
    "קניות ביגוד": "#e15759",
    "אחרים": "#76b7b2",
}

PARTNER_COLORS = {
    "בן/בת זוג A": "#59a14f",
    "בן/בת זוג B": "#edc948",
}


def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    conn = get_conn(db_path)
    try:
        conn.execute(_CREATE_TABLE)
        conn.commit()
    finally:
        conn.close()


def add_expense(db_path, amount_cents, description, category, is_essential, paid_by, expense_ts):
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    conn = get_conn(db_path)
    try:
        conn.execute(
            "INSERT INTO expenses "
            "(amount_cents, description, category, is_essential, paid_by, expense_ts, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (amount_cents, description, category, int(is_essential), paid_by, expense_ts, now),
        )
        conn.commit()
    finally:
        conn.close()


def list_expenses(db_path, year_month=None, category=None, paid_by=None):
    clauses = []
    params = []
    if year_month:
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
    conn = get_conn(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_expense(db_path, expense_id):
    conn = get_conn(db_path)
    try:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
    finally:
        conn.close()


def get_month_summary(db_path, year_month):
    rows = list_expenses(db_path, year_month=year_month)
    total_cents = 0
    by_category = {}
    by_partner = {}
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


def get_available_months(db_path):
    """Return list of YYYY-MM months that have expenses, newest first."""
    conn = get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT DISTINCT substr(expense_ts, 1, 7) as ym FROM expenses ORDER BY ym DESC"
        ).fetchall()
        return [r["ym"] for r in rows]
    finally:
        conn.close()
