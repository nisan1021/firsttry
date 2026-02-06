"""Tests for analytics and db modules – no Toga imports."""

import os
import tempfile
from pathlib import Path

import pytest

# Adjust path so we can import from src/
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from couples_expenses.core.db import init_db, add_expense, list_expenses, delete_expense, get_month_summary
from couples_expenses.core.analytics import month_kpis


@pytest.fixture
def db_path(tmp_path):
    p = tmp_path / "test_expenses.db"
    init_db(p)
    return p


def _add_sample(db_path, amount_cents=5000, category="רכב", paid_by="בן/בת זוג A",
                expense_ts="2026-01-15T10:30:00"):
    return add_expense(
        db_path,
        amount_cents=amount_cents,
        description="test",
        category=category,
        is_essential=True,
        paid_by=paid_by,
        expense_ts=expense_ts,
    )


class TestDb:
    def test_add_and_list(self, db_path):
        eid = _add_sample(db_path)
        assert eid is not None
        rows = list_expenses(db_path)
        assert len(rows) == 1
        assert rows[0]["amount_cents"] == 5000

    def test_filter_by_month(self, db_path):
        _add_sample(db_path, expense_ts="2026-01-15T10:00:00")
        _add_sample(db_path, expense_ts="2026-02-15T10:00:00")
        jan = list_expenses(db_path, year_month="2026-01")
        assert len(jan) == 1
        feb = list_expenses(db_path, year_month="2026-02")
        assert len(feb) == 1

    def test_filter_by_category(self, db_path):
        _add_sample(db_path, category="רכב")
        _add_sample(db_path, category="אחרים")
        rows = list_expenses(db_path, category="רכב")
        assert len(rows) == 1

    def test_filter_by_paid_by(self, db_path):
        _add_sample(db_path, paid_by="בן/בת זוג A")
        _add_sample(db_path, paid_by="בן/בת זוג B")
        rows = list_expenses(db_path, paid_by="בן/בת זוג B")
        assert len(rows) == 1

    def test_delete(self, db_path):
        eid = _add_sample(db_path)
        delete_expense(db_path, eid)
        rows = list_expenses(db_path)
        assert len(rows) == 0


class TestMonthSummary:
    def test_empty_month(self, db_path):
        s = get_month_summary(db_path, "2026-01")
        assert s["total_cents"] == 0
        assert s["by_category_cents"] == {}
        assert s["by_partner_cents"] == {}

    def test_totals(self, db_path):
        _add_sample(db_path, amount_cents=1000, category="רכב",
                     paid_by="בן/בת זוג A", expense_ts="2026-01-10T09:00:00")
        _add_sample(db_path, amount_cents=2000, category="אחרים",
                     paid_by="בן/בת זוג B", expense_ts="2026-01-20T09:00:00")
        s = get_month_summary(db_path, "2026-01")
        assert s["total_cents"] == 3000
        assert s["by_category_cents"]["רכב"] == 1000
        assert s["by_category_cents"]["אחרים"] == 2000
        assert s["by_partner_cents"]["בן/בת זוג A"] == 1000
        assert s["by_partner_cents"]["בן/בת זוג B"] == 2000


class TestAnalytics:
    def test_kpis_display_format(self, db_path):
        _add_sample(db_path, amount_cents=15050, expense_ts="2026-03-05T12:00:00")
        kpis = month_kpis(db_path, "2026-03")
        assert kpis["total_display"] == "₪150.50"
        assert "רכב" in kpis["category_display"]
        assert kpis["category_display"]["רכב"] == "₪150.50"

    def test_kpis_empty_month(self, db_path):
        kpis = month_kpis(db_path, "2099-12")
        assert kpis["total_cents"] == 0
        assert kpis["total_display"] == "₪0.00"
