"""Add Expense screen."""

from datetime import datetime

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER

from couples_expenses.core.constants import (
    CATEGORIES,
    PARTNERS,
    DATE_INPUT_FMT,
    ISO_FMT,
)
from couples_expenses.core.db import add_expense


def build_add_expense_box(app: toga.App, navigate_to_list) -> toga.Box:
    """Return a Box containing the Add Expense form."""

    amount_input = toga.TextInput(
        placeholder="Amount (e.g. 49.90)",
        style=Pack(flex=1, padding=5),
    )
    desc_input = toga.TextInput(
        placeholder="Description",
        style=Pack(flex=1, padding=5),
    )
    category_select = toga.Selection(
        items=CATEGORIES,
        style=Pack(flex=1, padding=5),
    )
    essential_switch = toga.Switch(
        text="הוצאה נצרכת",
        style=Pack(padding=5),
    )
    paid_by_select = toga.Selection(
        items=PARTNERS,
        style=Pack(flex=1, padding=5),
    )
    date_input = toga.TextInput(
        value=datetime.now().strftime(DATE_INPUT_FMT),
        style=Pack(flex=1, padding=5),
    )

    status_label = toga.Label("", style=Pack(padding=5, color="#cc0000"))

    def on_save(widget):
        # Validate amount
        raw = amount_input.value.strip()
        if not raw:
            status_label.text = "Amount is required."
            return
        try:
            amount_float = float(raw)
        except ValueError:
            status_label.text = "Amount must be a number."
            return
        if amount_float <= 0:
            status_label.text = "Amount must be > 0."
            return

        amount_cents = round(amount_float * 100)

        # Validate description
        desc = desc_input.value.strip()
        if not desc:
            status_label.text = "Description is required."
            return

        # Parse date
        raw_date = date_input.value.strip()
        try:
            dt = datetime.strptime(raw_date, DATE_INPUT_FMT)
        except ValueError:
            status_label.text = "Date format must be YYYY-MM-DD HH:MM"
            return

        expense_ts = dt.strftime(ISO_FMT)

        db_path = app.paths.data / "expenses.db"
        add_expense(
            db_path,
            amount_cents=amount_cents,
            description=desc,
            category=category_select.value,
            is_essential=bool(essential_switch.value),
            paid_by=paid_by_select.value,
            expense_ts=expense_ts,
        )

        app.main_window.info_dialog("Saved", "Expense saved successfully!")

        # Reset form
        amount_input.value = ""
        desc_input.value = ""
        date_input.value = datetime.now().strftime(DATE_INPUT_FMT)
        status_label.text = ""

        navigate_to_list()

    save_btn = toga.Button(
        "Save",
        on_press=on_save,
        style=Pack(padding=10, width=200, alignment=CENTER),
    )

    box = toga.Box(
        style=Pack(direction=COLUMN, padding=10),
        children=[
            toga.Label("Add Expense", style=Pack(font_size=18, padding_bottom=10)),
            toga.Label("Amount (₪):", style=Pack(padding=(5, 5, 0, 5))),
            amount_input,
            toga.Label("Description:", style=Pack(padding=(5, 5, 0, 5))),
            desc_input,
            toga.Label("Category:", style=Pack(padding=(5, 5, 0, 5))),
            category_select,
            essential_switch,
            toga.Label("Paid by:", style=Pack(padding=(5, 5, 0, 5))),
            paid_by_select,
            toga.Label("Date/Time (YYYY-MM-DD HH:MM):", style=Pack(padding=(5, 5, 0, 5))),
            date_input,
            status_label,
            save_btn,
        ],
    )
    return box
