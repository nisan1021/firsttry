"""Pure-Python analytics – no UI imports, no NumPy."""

from pathlib import Path
from couples_expenses.core.db import get_month_summary


def month_kpis(db_path: Path, year_month: str) -> dict:
    """Return KPI dict for dashboard display.

    Keys:
        total_cents          – int
        by_category_cents    – dict[str, int]
        by_partner_cents     – dict[str, int]
        total_display        – str  (formatted ₪X.XX)
        category_display     – dict[str, str]
        partner_display      – dict[str, str]
    """
    summary = get_month_summary(db_path, year_month)

    def fmt(cents: int) -> str:
        return f"\u20aa{cents / 100:.2f}"

    summary["total_display"] = fmt(summary["total_cents"])
    summary["category_display"] = {
        k: fmt(v) for k, v in summary["by_category_cents"].items()
    }
    summary["partner_display"] = {
        k: fmt(v) for k, v in summary["by_partner_cents"].items()
    }
    return summary
