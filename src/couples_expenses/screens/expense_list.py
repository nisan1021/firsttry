"""Expense List screen with filters and delete."""

from datetime import datetime, timedelta

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from couples_expenses.core.constants import CATEGORIES, PARTNERS
from couples_expenses.core.db import list_expenses, delete_expense


def _last_months(n: int = 18) -> list[str]:
    """Return list of YYYY-MM strings for the last *n* months, newest first."""
    today = datetime.now()
    months = []
    for i in range(n):
        d = today.replace(day=1) - timedelta(days=i * 28)
        ym = d.strftime("%Y-%m")
        if ym not in months:
            months.append(ym)
    # Ensure we have exactly n unique entries
    # Fill remaining if needed
    while len(months) < n:
        d = today.replace(day=1) - timedelta(days=len(months) * 28)
        ym = d.strftime("%Y-%m")
        if ym not in months:
            months.append(ym)
    return sorted(set(months), reverse=True)[:n]


def build_expense_list_box(app: toga.App) -> toga.Box:
    """Return a Box containing the filterable expense list."""

    month_items = _last_months()
    all_label = "All"

    month_select = toga.Selection(
        items=[all_label] + month_items,
        style=Pack(flex=1, padding=5),
    )
    cat_select = toga.Selection(
        items=[all_label] + CATEGORIES,
        style=Pack(flex=1, padding=5),
    )
    paid_select = toga.Selection(
        items=[all_label] + PARTNERS,
        style=Pack(flex=1, padding=5),
    )

    table = toga.Table(
        headings=["ID", "Date", "Amount", "Category", "Paid by", "Description"],
        style=Pack(flex=1, padding=5),
        accessors=["expense_id", "date", "amount", "category", "paid_by", "description"],
    )

    def refresh_table(widget=None):
        db_path = app.paths.data / "expenses.db"
        ym = None if month_select.value == all_label else month_select.value
        cat = None if cat_select.value == all_label else cat_select.value
        paid = None if paid_select.value == all_label else paid_select.value
        rows = list_expenses(db_path, year_month=ym, category=cat, paid_by=paid)

        table_data = []
        for r in rows:
            table_data.append({
                "expense_id": str(r["id"]),
                "date": r["expense_ts"][:16].replace("T", " "),
                "amount": f"\u20aa{r['amount_cents'] / 100:.2f}",
                "category": r["category"],
                "paid_by": r["paid_by"],
                "description": r["description"],
            })
        table.data = table_data

    month_select.on_change = refresh_table
    cat_select.on_change = refresh_table
    paid_select.on_change = refresh_table

    def on_delete(widget):
        if table.selection is None:
            app.main_window.info_dialog("Select", "Select an expense to delete.")
            return
        row = table.selection
        expense_id = int(row.expense_id)

        confirmed = app.main_window.confirm_dialog(
            "Delete?",
            f"Delete expense #{expense_id}?",
        )
        if confirmed:
            db_path = app.paths.data / "expenses.db"
            delete_expense(db_path, expense_id)
            refresh_table()

    delete_btn = toga.Button(
        "Delete Selected",
        on_press=on_delete,
        style=Pack(padding=5, width=160),
    )

    filter_row = toga.Box(
        style=Pack(direction=ROW, padding=5),
        children=[month_select, cat_select, paid_select],
    )

    box = toga.Box(
        style=Pack(direction=COLUMN, padding=10),
        children=[
            toga.Label("Expense List", style=Pack(font_size=18, padding_bottom=10)),
            filter_row,
            table,
            delete_btn,
        ],
    )

    # Store refresh function so it can be called externally
    box._refresh = refresh_table
    return box
