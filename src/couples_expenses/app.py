"""Couples Expenses – main application entry point."""

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER

from couples_expenses.core.db import init_db
from couples_expenses.screens.add_expense import build_add_expense_box
from couples_expenses.screens.expense_list import build_expense_list_box
from couples_expenses.screens.dashboard import build_dashboard_box


class CouplesExpenses(toga.App):
    def startup(self):
        # Ensure data directory and database exist
        self.paths.data.mkdir(parents=True, exist_ok=True)
        db_path = self.paths.data / "expenses.db"
        init_db(db_path)

        # Build screen containers
        self._list_box = build_expense_list_box(self)
        self._dashboard_box = build_dashboard_box(self)
        self._add_box = build_add_expense_box(self, navigate_to_list=self._show_list)

        # Navigation bar
        nav_bar = toga.Box(
            style=Pack(direction=ROW, padding=5, alignment=CENTER),
            children=[
                toga.Button("Add Expense", on_press=self._show_add, style=Pack(padding=5, flex=1)),
                toga.Button("Expense List", on_press=self._show_list, style=Pack(padding=5, flex=1)),
                toga.Button("Dashboard", on_press=self._show_dashboard, style=Pack(padding=5, flex=1)),
            ],
        )

        # Content area
        self._content_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        self._content_box.add(self._add_box)

        # Main layout
        main_box = toga.Box(
            style=Pack(direction=COLUMN),
            children=[nav_bar, self._content_box],
        )

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

    def _clear_content(self):
        while self._content_box.children:
            self._content_box.remove(self._content_box.children[0])

    def _show_add(self, widget=None):
        self._clear_content()
        self._content_box.add(self._add_box)

    def _show_list(self, widget=None):
        self._clear_content()
        self._content_box.add(self._list_box)
        if hasattr(self._list_box, "_refresh"):
            self._list_box._refresh()

    def _show_dashboard(self, widget=None):
        self._clear_content()
        self._content_box.add(self._dashboard_box)
        if hasattr(self._dashboard_box, "_refresh"):
            self._dashboard_box._refresh()


def main():
    return CouplesExpenses(
        "couples_expenses",
        formal_name="Couples Expenses",
    )
