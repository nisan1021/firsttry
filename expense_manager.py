#!/usr/bin/env python3
"""
Expense Manager - אפליקציה לניהול הוצאות עם Google Sheets
==========================================================
אפליקציה מקיפה לניהול הוצאות המשתמשת ב-Google Sheets כבסיס נתונים.
כוללת: הוספה, עריכה, מחיקה, סינון, דשבורדים וניתוח הוצאות.

דרישות:
    pip install gspread google-auth rich

הגדרה:
    1. צור פרויקט ב-Google Cloud Console
    2. הפעל את Google Sheets API ו-Google Drive API
    3. צור Service Account והורד את קובץ ה-credentials.json
    4. שתף את ה-Google Sheet עם כתובת ה-email של ה-Service Account
    5. הרץ: python expense_manager.py
"""

import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("חסרות ספריות נדרשות. התקן עם:")
    print("  pip install gspread google-auth")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
    from rich.layout import Layout
    from rich.text import Text
    from rich.bar import Bar
    from rich import box
    from rich.columns import Columns
    from rich.align import Align
except ImportError:
    print("חסרה ספריית rich. התקן עם:")
    print("  pip install rich")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CREDENTIALS_FILE = "credentials.json"

CATEGORIES = [
    "מזון ומשקאות",
    "דיור ומשכנתא",
    "חשבונות (חשמל/מים/גז)",
    "תחבורה ורכב",
    "בריאות",
    "ביגוד והנעלה",
    "בילויים ופנאי",
    "חינוך",
    "ביטוח",
    "חסכון והשקעות",
    "מתנות ותרומות",
    "אחר",
]

PAYMENT_METHODS = [
    "מזומן",
    "כרטיס אשראי",
    "העברה בנקאית",
    "ביט/פייבוקס",
    "צ'ק",
    "אחר",
]

HEADER_ROW = [
    "מזהה",
    "תאריך",
    "קטגוריה",
    "תיאור",
    "סכום",
    "אמצעי תשלום",
    "הערות",
    "נוצר בתאריך",
]

MONTHS_HEB = {
    1: "ינואר",
    2: "פברואר",
    3: "מרץ",
    4: "אפריל",
    5: "מאי",
    6: "יוני",
    7: "יולי",
    8: "אוגוסט",
    9: "ספטמבר",
    10: "אוקטובר",
    11: "נובמבר",
    12: "דצמבר",
}

console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# Google Sheets Connection
# ─────────────────────────────────────────────────────────────────────────────


class SheetsManager:
    """Manages all Google Sheets operations."""

    def __init__(self, spreadsheet_name: str, credentials_path: str = CREDENTIALS_FILE):
        self.spreadsheet_name = spreadsheet_name
        self.credentials_path = credentials_path
        self.client = None
        self.spreadsheet = None
        self.worksheet = None

    def connect(self) -> bool:
        """Connect to Google Sheets."""
        try:
            creds = Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES
            )
            self.client = gspread.authorize(creds)

            # Try to open existing spreadsheet
            try:
                self.spreadsheet = self.client.open(self.spreadsheet_name)
            except gspread.SpreadsheetNotFound:
                console.print(
                    f"[yellow]הגיליון '{self.spreadsheet_name}' לא נמצא. יוצר חדש...[/yellow]"
                )
                self.spreadsheet = self.client.create(self.spreadsheet_name)
                console.print(
                    f"[green]הגיליון נוצר! שתף אותו עם המשתמשים הרלוונטיים.[/green]"
                )
                console.print(
                    f"[dim]קישור: {self.spreadsheet.url}[/dim]"
                )

            self._init_worksheets()
            return True

        except FileNotFoundError:
            console.print(
                f"[red]קובץ credentials לא נמצא: {self.credentials_path}[/red]"
            )
            console.print("[yellow]ראה הוראות הגדרה ב-README.md[/yellow]")
            return False
        except Exception as e:
            console.print(f"[red]שגיאת התחברות: {e}[/red]")
            return False

    def _init_worksheets(self):
        """Initialize worksheets with headers if needed."""
        # Main expenses worksheet
        try:
            self.worksheet = self.spreadsheet.worksheet("הוצאות")
        except gspread.WorksheetNotFound:
            self.worksheet = self.spreadsheet.add_worksheet(
                title="הוצאות", rows=1000, cols=10
            )
            self.worksheet.append_row(HEADER_ROW)
            self.worksheet.format("1", {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.7},
                "horizontalAlignment": "CENTER",
            })

        # Budget worksheet
        try:
            self.spreadsheet.worksheet("תקציב")
        except gspread.WorksheetNotFound:
            budget_ws = self.spreadsheet.add_worksheet(
                title="תקציב", rows=20, cols=3
            )
            budget_ws.append_row(["קטגוריה", "תקציב חודשי", "הערות"])
            for cat in CATEGORIES:
                budget_ws.append_row([cat, 0, ""])

        # Remove default Sheet1 if it exists and we have other sheets
        try:
            default = self.spreadsheet.worksheet("Sheet1")
            if len(self.spreadsheet.worksheets()) > 1:
                self.spreadsheet.del_worksheet(default)
        except (gspread.WorksheetNotFound, gspread.exceptions.APIError):
            pass

    def get_next_id(self) -> int:
        """Get the next available expense ID."""
        records = self.worksheet.get_all_values()
        if len(records) <= 1:
            return 1
        try:
            ids = [int(row[0]) for row in records[1:] if row[0].isdigit()]
            return max(ids) + 1 if ids else 1
        except (ValueError, IndexError):
            return len(records)

    def add_expense(self, date: str, category: str, description: str,
                    amount: float, payment_method: str, notes: str = "") -> int:
        """Add a new expense row."""
        expense_id = self.get_next_id()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            expense_id,
            date,
            category,
            description,
            amount,
            payment_method,
            notes,
            created_at,
        ]
        self.worksheet.append_row(row, value_input_option="USER_ENTERED")
        return expense_id

    def get_all_expenses(self) -> list[dict]:
        """Get all expenses as list of dicts."""
        records = self.worksheet.get_all_records()
        return records

    def update_expense(self, expense_id: int, field: str, new_value) -> bool:
        """Update a specific field of an expense."""
        try:
            col_map = {h: i + 1 for i, h in enumerate(HEADER_ROW)}
            if field not in col_map:
                return False

            cell = self.worksheet.find(str(expense_id), in_column=1)
            if cell is None:
                return False

            self.worksheet.update_cell(
                cell.row, col_map[field], new_value
            )
            return True
        except Exception as e:
            console.print(f"[red]שגיאה בעדכון: {e}[/red]")
            return False

    def delete_expense(self, expense_id: int) -> bool:
        """Delete an expense by ID."""
        try:
            cell = self.worksheet.find(str(expense_id), in_column=1)
            if cell is None:
                return False
            self.worksheet.delete_rows(cell.row)
            return True
        except Exception as e:
            console.print(f"[red]שגיאה במחיקה: {e}[/red]")
            return False

    def get_budgets(self) -> dict[str, float]:
        """Get budget amounts per category."""
        try:
            budget_ws = self.spreadsheet.worksheet("תקציב")
            records = budget_ws.get_all_records()
            return {
                r["קטגוריה"]: float(r.get("תקציב חודשי", 0))
                for r in records
                if r.get("קטגוריה")
            }
        except Exception:
            return {}

    def set_budget(self, category: str, amount: float) -> bool:
        """Set budget for a category."""
        try:
            budget_ws = self.spreadsheet.worksheet("תקציב")
            cell = budget_ws.find(category, in_column=1)
            if cell:
                budget_ws.update_cell(cell.row, 2, amount)
                return True
            else:
                budget_ws.append_row([category, amount, ""])
                return True
        except Exception as e:
            console.print(f"[red]שגיאה בעדכון תקציב: {e}[/red]")
            return False


# ─────────────────────────────────────────────────────────────────────────────
# Analytics & Dashboard
# ─────────────────────────────────────────────────────────────────────────────


def parse_amount(val) -> float:
    """Safely parse amount to float."""
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "").replace("₪", "").strip())
    except (ValueError, TypeError):
        return 0.0


def parse_date(val: str) -> datetime | None:
    """Parse date string."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(val.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def filter_expenses_by_month(expenses: list[dict], year: int, month: int) -> list[dict]:
    """Filter expenses for a specific month."""
    result = []
    for e in expenses:
        d = parse_date(str(e.get("תאריך", "")))
        if d and d.year == year and d.month == month:
            result.append(e)
    return result


def filter_expenses_by_range(expenses: list[dict], start: datetime, end: datetime) -> list[dict]:
    """Filter expenses by date range."""
    result = []
    for e in expenses:
        d = parse_date(str(e.get("תאריך", "")))
        if d and start <= d <= end:
            result.append(e)
    return result


def calc_category_totals(expenses: list[dict]) -> dict[str, float]:
    """Calculate total spending per category."""
    totals = defaultdict(float)
    for e in expenses:
        cat = e.get("קטגוריה", "אחר")
        totals[cat] += parse_amount(e.get("סכום", 0))
    return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))


def calc_payment_method_totals(expenses: list[dict]) -> dict[str, float]:
    """Calculate total spending per payment method."""
    totals = defaultdict(float)
    for e in expenses:
        pm = e.get("אמצעי תשלום", "אחר")
        totals[pm] += parse_amount(e.get("סכום", 0))
    return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))


def calc_daily_totals(expenses: list[dict]) -> dict[str, float]:
    """Calculate total spending per day."""
    totals = defaultdict(float)
    for e in expenses:
        date_str = str(e.get("תאריך", ""))
        totals[date_str] += parse_amount(e.get("סכום", 0))
    return dict(sorted(totals.items()))


def make_bar_chart(data: dict[str, float], max_width: int = 40, color: str = "cyan") -> str:
    """Create a simple horizontal bar chart."""
    if not data:
        return "אין נתונים"
    max_val = max(data.values()) if data.values() else 1
    lines = []
    for label, val in data.items():
        bar_len = int((val / max_val) * max_width) if max_val > 0 else 0
        bar = "█" * bar_len
        lines.append(f"  {label:20s} [{color}]{bar}[/{color}] ₪{val:,.0f}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# UI Functions
# ─────────────────────────────────────────────────────────────────────────────


def show_main_menu():
    """Display the main menu."""
    console.print()
    console.print(
        Panel(
            "[bold cyan]מנהל ההוצאות[/bold cyan]\n"
            "[dim]ניהול הוצאות חכם עם Google Sheets[/dim]",
            box=box.DOUBLE,
            border_style="cyan",
        )
    )
    menu_items = [
        "[1] ➕  הוספת הוצאה",
        "[2] 📋  רשימת הוצאות",
        "[3] ✏️   עריכת הוצאה",
        "[4] 🗑️   מחיקת הוצאה",
        "[5] 🔍  חיפוש וסינון",
        "[6] 📊  דשבורד חודשי",
        "[7] 📈  דשבורד שנתי",
        "[8] 💰  ניהול תקציב",
        "[9] 📉  ניתוח מגמות",
        "[0] 🚪  יציאה",
    ]
    console.print(
        Panel("\n".join(menu_items), title="[bold]תפריט ראשי[/bold]", border_style="blue")
    )


def add_expense_ui(sheets: SheetsManager):
    """Interactive UI for adding a new expense."""
    console.print(Panel("[bold green]הוספת הוצאה חדשה[/bold green]", border_style="green"))

    # Date
    date_str = Prompt.ask(
        "תאריך (YYYY-MM-DD)",
        default=datetime.now().strftime("%Y-%m-%d"),
    )
    if not parse_date(date_str):
        console.print("[red]תאריך לא תקין[/red]")
        return

    # Category
    console.print("\n[bold]קטגוריות:[/bold]")
    for i, cat in enumerate(CATEGORIES, 1):
        console.print(f"  [{i}] {cat}")
    cat_idx = IntPrompt.ask("בחר קטגוריה", default=1)
    if not 1 <= cat_idx <= len(CATEGORIES):
        console.print("[red]בחירה לא תקינה[/red]")
        return
    category = CATEGORIES[cat_idx - 1]

    # Description
    description = Prompt.ask("תיאור")
    if not description:
        console.print("[red]תיאור נדרש[/red]")
        return

    # Amount
    amount = FloatPrompt.ask("סכום (₪)")
    if amount <= 0:
        console.print("[red]סכום חייב להיות חיובי[/red]")
        return

    # Payment method
    console.print("\n[bold]אמצעי תשלום:[/bold]")
    for i, pm in enumerate(PAYMENT_METHODS, 1):
        console.print(f"  [{i}] {pm}")
    pm_idx = IntPrompt.ask("בחר אמצעי תשלום", default=1)
    if not 1 <= pm_idx <= len(PAYMENT_METHODS):
        console.print("[red]בחירה לא תקינה[/red]")
        return
    payment_method = PAYMENT_METHODS[pm_idx - 1]

    # Notes
    notes = Prompt.ask("הערות (אופציונלי)", default="")

    # Confirm
    console.print()
    console.print(f"  תאריך: [cyan]{date_str}[/cyan]")
    console.print(f"  קטגוריה: [cyan]{category}[/cyan]")
    console.print(f"  תיאור: [cyan]{description}[/cyan]")
    console.print(f"  סכום: [cyan]₪{amount:,.2f}[/cyan]")
    console.print(f"  אמצעי תשלום: [cyan]{payment_method}[/cyan]")
    if notes:
        console.print(f"  הערות: [cyan]{notes}[/cyan]")

    if Confirm.ask("\nלשמור?", default=True):
        with console.status("[bold green]שומר...[/bold green]"):
            eid = sheets.add_expense(
                date_str, category, description, amount, payment_method, notes
            )
        console.print(f"[green]✓ הוצאה נשמרה בהצלחה! מזהה: {eid}[/green]")
    else:
        console.print("[yellow]בוטל[/yellow]")


def list_expenses_ui(sheets: SheetsManager, expenses: list[dict] | None = None):
    """Display expenses in a formatted table."""
    if expenses is None:
        with console.status("[bold cyan]טוען הוצאות...[/bold cyan]"):
            expenses = sheets.get_all_expenses()

    if not expenses:
        console.print("[yellow]אין הוצאות להצגה[/yellow]")
        return

    table = Table(
        title="רשימת הוצאות",
        box=box.ROUNDED,
        show_lines=True,
        border_style="blue",
    )
    table.add_column("מזהה", style="dim", justify="center", width=6)
    table.add_column("תאריך", style="cyan", justify="center", width=12)
    table.add_column("קטגוריה", style="magenta", width=18)
    table.add_column("תיאור", width=25)
    table.add_column("סכום", style="green", justify="right", width=12)
    table.add_column("אמצעי תשלום", style="yellow", width=15)
    table.add_column("הערות", style="dim", width=20)

    total = 0.0
    for e in expenses:
        amt = parse_amount(e.get("סכום", 0))
        total += amt
        table.add_row(
            str(e.get("מזהה", "")),
            str(e.get("תאריך", "")),
            str(e.get("קטגוריה", "")),
            str(e.get("תיאור", "")),
            f"₪{amt:,.2f}",
            str(e.get("אמצעי תשלום", "")),
            str(e.get("הערות", "")),
        )

    table.add_section()
    table.add_row("", "", "", "[bold]סה״כ[/bold]", f"[bold]₪{total:,.2f}[/bold]", "", "")

    console.print(table)
    console.print(f"  [dim]סה״כ {len(expenses)} הוצאות[/dim]")


def edit_expense_ui(sheets: SheetsManager):
    """Interactive UI for editing an expense."""
    console.print(Panel("[bold yellow]עריכת הוצאה[/bold yellow]", border_style="yellow"))

    expense_id = IntPrompt.ask("הכנס מזהה הוצאה לעריכה")

    fields = {
        "1": ("תאריך", "תאריך"),
        "2": ("קטגוריה", "קטגוריה"),
        "3": ("תיאור", "תיאור"),
        "4": ("סכום", "סכום"),
        "5": ("אמצעי תשלום", "אמצעי תשלום"),
        "6": ("הערות", "הערות"),
    }

    console.print("\n[bold]שדות לעריכה:[/bold]")
    for k, (label, _) in fields.items():
        console.print(f"  [{k}] {label}")

    choice = Prompt.ask("בחר שדה", choices=list(fields.keys()))
    field_label, field_name = fields[choice]

    if field_name == "קטגוריה":
        console.print("\n[bold]קטגוריות:[/bold]")
        for i, cat in enumerate(CATEGORIES, 1):
            console.print(f"  [{i}] {cat}")
        cat_idx = IntPrompt.ask("בחר קטגוריה")
        if 1 <= cat_idx <= len(CATEGORIES):
            new_value = CATEGORIES[cat_idx - 1]
        else:
            console.print("[red]בחירה לא תקינה[/red]")
            return
    elif field_name == "אמצעי תשלום":
        console.print("\n[bold]אמצעי תשלום:[/bold]")
        for i, pm in enumerate(PAYMENT_METHODS, 1):
            console.print(f"  [{i}] {pm}")
        pm_idx = IntPrompt.ask("בחר אמצעי תשלום")
        if 1 <= pm_idx <= len(PAYMENT_METHODS):
            new_value = PAYMENT_METHODS[pm_idx - 1]
        else:
            console.print("[red]בחירה לא תקינה[/red]")
            return
    elif field_name == "סכום":
        new_value = FloatPrompt.ask(f"ערך חדש ל{field_label}")
    else:
        new_value = Prompt.ask(f"ערך חדש ל{field_label}")

    with console.status("[bold yellow]מעדכן...[/bold yellow]"):
        success = sheets.update_expense(expense_id, field_name, new_value)

    if success:
        console.print(f"[green]✓ הוצאה {expense_id} עודכנה בהצלחה![/green]")
    else:
        console.print(f"[red]✗ לא נמצאה הוצאה עם מזהה {expense_id}[/red]")


def delete_expense_ui(sheets: SheetsManager):
    """Interactive UI for deleting an expense."""
    console.print(Panel("[bold red]מחיקת הוצאה[/bold red]", border_style="red"))

    expense_id = IntPrompt.ask("הכנס מזהה הוצאה למחיקה")

    if Confirm.ask(f"[red]בטוח שברצונך למחוק הוצאה {expense_id}?[/red]", default=False):
        with console.status("[bold red]מוחק...[/bold red]"):
            success = sheets.delete_expense(expense_id)
        if success:
            console.print(f"[green]✓ הוצאה {expense_id} נמחקה[/green]")
        else:
            console.print(f"[red]✗ לא נמצאה הוצאה עם מזהה {expense_id}[/red]")
    else:
        console.print("[yellow]בוטל[/yellow]")


def search_expenses_ui(sheets: SheetsManager):
    """Search and filter expenses."""
    console.print(Panel("[bold blue]חיפוש וסינון[/bold blue]", border_style="blue"))

    console.print("  [1] סינון לפי קטגוריה")
    console.print("  [2] סינון לפי טווח תאריכים")
    console.print("  [3] סינון לפי אמצעי תשלום")
    console.print("  [4] חיפוש חופשי בתיאור")
    console.print("  [5] סינון לפי סכום (מינימום-מקסימום)")

    choice = Prompt.ask("בחר סוג סינון", choices=["1", "2", "3", "4", "5"])

    with console.status("[bold cyan]טוען...[/bold cyan]"):
        all_expenses = sheets.get_all_expenses()

    if not all_expenses:
        console.print("[yellow]אין הוצאות[/yellow]")
        return

    filtered = all_expenses

    if choice == "1":
        console.print("\n[bold]קטגוריות:[/bold]")
        for i, cat in enumerate(CATEGORIES, 1):
            console.print(f"  [{i}] {cat}")
        cat_idx = IntPrompt.ask("בחר קטגוריה")
        if 1 <= cat_idx <= len(CATEGORIES):
            cat = CATEGORIES[cat_idx - 1]
            filtered = [e for e in all_expenses if e.get("קטגוריה") == cat]
        else:
            console.print("[red]בחירה לא תקינה[/red]")
            return

    elif choice == "2":
        start = Prompt.ask("תאריך התחלה (YYYY-MM-DD)")
        end = Prompt.ask("תאריך סיום (YYYY-MM-DD)")
        start_dt = parse_date(start)
        end_dt = parse_date(end)
        if start_dt and end_dt:
            filtered = filter_expenses_by_range(all_expenses, start_dt, end_dt)
        else:
            console.print("[red]תאריך לא תקין[/red]")
            return

    elif choice == "3":
        console.print("\n[bold]אמצעי תשלום:[/bold]")
        for i, pm in enumerate(PAYMENT_METHODS, 1):
            console.print(f"  [{i}] {pm}")
        pm_idx = IntPrompt.ask("בחר אמצעי תשלום")
        if 1 <= pm_idx <= len(PAYMENT_METHODS):
            pm = PAYMENT_METHODS[pm_idx - 1]
            filtered = [e for e in all_expenses if e.get("אמצעי תשלום") == pm]
        else:
            console.print("[red]בחירה לא תקינה[/red]")
            return

    elif choice == "4":
        query = Prompt.ask("הכנס מילת חיפוש")
        filtered = [
            e for e in all_expenses
            if query.lower() in str(e.get("תיאור", "")).lower()
            or query.lower() in str(e.get("הערות", "")).lower()
        ]

    elif choice == "5":
        min_amt = FloatPrompt.ask("סכום מינימלי", default=0.0)
        max_amt = FloatPrompt.ask("סכום מקסימלי", default=999999.0)
        filtered = [
            e for e in all_expenses
            if min_amt <= parse_amount(e.get("סכום", 0)) <= max_amt
        ]

    console.print(f"\n[bold]נמצאו {len(filtered)} תוצאות:[/bold]")
    list_expenses_ui(sheets, filtered)


def monthly_dashboard_ui(sheets: SheetsManager):
    """Display monthly expense dashboard."""
    console.print(Panel("[bold magenta]דשבורד חודשי[/bold magenta]", border_style="magenta"))

    now = datetime.now()
    year = IntPrompt.ask("שנה", default=now.year)
    month = IntPrompt.ask("חודש (1-12)", default=now.month)

    if not 1 <= month <= 12:
        console.print("[red]חודש לא תקין[/red]")
        return

    with console.status("[bold cyan]טוען נתונים...[/bold cyan]"):
        all_expenses = sheets.get_all_expenses()
        budgets = sheets.get_budgets()

    monthly = filter_expenses_by_month(all_expenses, year, month)

    if not monthly:
        console.print(f"[yellow]אין הוצאות ל{MONTHS_HEB[month]} {year}[/yellow]")
        return

    total = sum(parse_amount(e.get("סכום", 0)) for e in monthly)
    cat_totals = calc_category_totals(monthly)
    pm_totals = calc_payment_method_totals(monthly)
    daily = calc_daily_totals(monthly)

    # Header
    console.print()
    console.print(
        Panel(
            f"[bold]{MONTHS_HEB[month]} {year}[/bold]\n"
            f"סה״כ הוצאות: [bold green]₪{total:,.2f}[/bold green]\n"
            f"מספר הוצאות: [bold]{len(monthly)}[/bold]\n"
            f"ממוצע להוצאה: [bold]₪{total / len(monthly):,.2f}[/bold]",
            title="[bold]סיכום חודשי[/bold]",
            border_style="magenta",
        )
    )

    # Category breakdown
    console.print(
        Panel(
            make_bar_chart(cat_totals, color="magenta"),
            title="[bold]הוצאות לפי קטגוריה[/bold]",
            border_style="blue",
        )
    )

    # Budget comparison
    if budgets:
        budget_lines = []
        for cat, spent in cat_totals.items():
            budget = budgets.get(cat, 0)
            if budget > 0:
                pct = (spent / budget) * 100
                if pct > 100:
                    status = f"[red]⚠ {pct:.0f}% - חריגה![/red]"
                elif pct > 80:
                    status = f"[yellow]⚡ {pct:.0f}%[/yellow]"
                else:
                    status = f"[green]✓ {pct:.0f}%[/green]"
                bar_len = min(int(pct / 100 * 30), 35)
                bar_color = "red" if pct > 100 else "yellow" if pct > 80 else "green"
                bar = "█" * bar_len
                budget_lines.append(
                    f"  {cat:18s} ₪{spent:>8,.0f} / ₪{budget:>8,.0f}  "
                    f"[{bar_color}]{bar}[/{bar_color}] {status}"
                )
        if budget_lines:
            console.print(
                Panel(
                    "\n".join(budget_lines),
                    title="[bold]תקציב מול בפועל[/bold]",
                    border_style="yellow",
                )
            )

    # Payment method breakdown
    console.print(
        Panel(
            make_bar_chart(pm_totals, color="yellow"),
            title="[bold]הוצאות לפי אמצעי תשלום[/bold]",
            border_style="green",
        )
    )

    # Daily breakdown
    console.print(
        Panel(
            make_bar_chart(daily, max_width=30, color="cyan"),
            title="[bold]הוצאות יומיות[/bold]",
            border_style="cyan",
        )
    )

    # Top expenses
    top_expenses = sorted(monthly, key=lambda x: parse_amount(x.get("סכום", 0)), reverse=True)[:5]
    top_table = Table(title="5 ההוצאות הגדולות", box=box.SIMPLE, border_style="red")
    top_table.add_column("תאריך", style="cyan")
    top_table.add_column("תיאור")
    top_table.add_column("סכום", style="green", justify="right")
    top_table.add_column("קטגוריה", style="magenta")
    for e in top_expenses:
        top_table.add_row(
            str(e.get("תאריך", "")),
            str(e.get("תיאור", "")),
            f"₪{parse_amount(e.get('סכום', 0)):,.2f}",
            str(e.get("קטגוריה", "")),
        )
    console.print(top_table)


def yearly_dashboard_ui(sheets: SheetsManager):
    """Display yearly expense dashboard."""
    console.print(Panel("[bold blue]דשבורד שנתי[/bold blue]", border_style="blue"))

    year = IntPrompt.ask("שנה", default=datetime.now().year)

    with console.status("[bold cyan]טוען נתונים...[/bold cyan]"):
        all_expenses = sheets.get_all_expenses()

    yearly = []
    for e in all_expenses:
        d = parse_date(str(e.get("תאריך", "")))
        if d and d.year == year:
            yearly.append(e)

    if not yearly:
        console.print(f"[yellow]אין הוצאות לשנת {year}[/yellow]")
        return

    total = sum(parse_amount(e.get("סכום", 0)) for e in yearly)

    # Monthly totals
    monthly_totals = defaultdict(float)
    monthly_counts = defaultdict(int)
    for e in yearly:
        d = parse_date(str(e.get("תאריך", "")))
        if d:
            monthly_totals[d.month] += parse_amount(e.get("סכום", 0))
            monthly_counts[d.month] += 1

    monthly_chart_data = {}
    for m in range(1, 13):
        if m in monthly_totals:
            monthly_chart_data[MONTHS_HEB[m]] = monthly_totals[m]

    console.print()
    console.print(
        Panel(
            f"[bold]שנת {year}[/bold]\n"
            f"סה״כ הוצאות: [bold green]₪{total:,.2f}[/bold green]\n"
            f"מספר הוצאות: [bold]{len(yearly)}[/bold]\n"
            f"ממוצע חודשי: [bold]₪{total / 12:,.2f}[/bold]",
            title="[bold]סיכום שנתי[/bold]",
            border_style="blue",
        )
    )

    # Monthly trend
    console.print(
        Panel(
            make_bar_chart(monthly_chart_data, max_width=35, color="blue"),
            title="[bold]מגמת הוצאות חודשית[/bold]",
            border_style="cyan",
        )
    )

    # Category totals for the year
    cat_totals = calc_category_totals(yearly)
    console.print(
        Panel(
            make_bar_chart(cat_totals, color="magenta"),
            title="[bold]הוצאות שנתיות לפי קטגוריה[/bold]",
            border_style="magenta",
        )
    )

    # Monthly details table
    month_table = Table(
        title=f"פירוט חודשי - {year}", box=box.ROUNDED, border_style="blue"
    )
    month_table.add_column("חודש", style="cyan", width=12)
    month_table.add_column("מספר הוצאות", justify="center", width=14)
    month_table.add_column("סה״כ", style="green", justify="right", width=14)
    month_table.add_column("ממוצע להוצאה", justify="right", width=14)

    for m in range(1, 13):
        if m in monthly_totals:
            avg = monthly_totals[m] / monthly_counts[m] if monthly_counts[m] > 0 else 0
            month_table.add_row(
                MONTHS_HEB[m],
                str(monthly_counts[m]),
                f"₪{monthly_totals[m]:,.2f}",
                f"₪{avg:,.2f}",
            )

    console.print(month_table)


def budget_management_ui(sheets: SheetsManager):
    """Manage budgets per category."""
    console.print(Panel("[bold yellow]ניהול תקציב[/bold yellow]", border_style="yellow"))

    console.print("  [1] הצג תקציבים")
    console.print("  [2] עדכן תקציב לקטגוריה")

    choice = Prompt.ask("בחר פעולה", choices=["1", "2"])

    if choice == "1":
        with console.status("[bold cyan]טוען...[/bold cyan]"):
            budgets = sheets.get_budgets()

        table = Table(title="תקציב חודשי", box=box.ROUNDED, border_style="yellow")
        table.add_column("קטגוריה", style="cyan", width=20)
        table.add_column("תקציב חודשי", style="green", justify="right", width=15)

        total_budget = 0.0
        for cat in CATEGORIES:
            budget = budgets.get(cat, 0)
            total_budget += budget
            table.add_row(cat, f"₪{budget:,.2f}")

        table.add_section()
        table.add_row("[bold]סה״כ[/bold]", f"[bold]₪{total_budget:,.2f}[/bold]")
        console.print(table)

    elif choice == "2":
        console.print("\n[bold]קטגוריות:[/bold]")
        for i, cat in enumerate(CATEGORIES, 1):
            console.print(f"  [{i}] {cat}")
        cat_idx = IntPrompt.ask("בחר קטגוריה")
        if 1 <= cat_idx <= len(CATEGORIES):
            cat = CATEGORIES[cat_idx - 1]
            amount = FloatPrompt.ask(f"תקציב חודשי חדש ל{cat}")
            with console.status("[bold yellow]מעדכן...[/bold yellow]"):
                success = sheets.set_budget(cat, amount)
            if success:
                console.print(f"[green]✓ תקציב ל{cat} עודכן ל-₪{amount:,.2f}[/green]")
            else:
                console.print("[red]שגיאה בעדכון[/red]")
        else:
            console.print("[red]בחירה לא תקינה[/red]")


def trends_analysis_ui(sheets: SheetsManager):
    """Analyze spending trends."""
    console.print(Panel("[bold cyan]ניתוח מגמות[/bold cyan]", border_style="cyan"))

    with console.status("[bold cyan]טוען נתונים...[/bold cyan]"):
        all_expenses = sheets.get_all_expenses()

    if not all_expenses:
        console.print("[yellow]אין הוצאות לניתוח[/yellow]")
        return

    # Parse all dates and find range
    dated_expenses = []
    for e in all_expenses:
        d = parse_date(str(e.get("תאריך", "")))
        if d:
            dated_expenses.append((d, e))

    if not dated_expenses:
        console.print("[yellow]אין הוצאות עם תאריכים תקינים[/yellow]")
        return

    dated_expenses.sort(key=lambda x: x[0])
    first_date = dated_expenses[0][0]
    last_date = dated_expenses[-1][0]

    console.print(f"\n  טווח נתונים: {first_date.strftime('%Y-%m-%d')} עד {last_date.strftime('%Y-%m-%d')}")
    console.print(f"  סה״כ הוצאות: {len(dated_expenses)}")

    # Month-over-month comparison
    monthly_data = defaultdict(float)
    for d, e in dated_expenses:
        key = f"{d.year}-{d.month:02d}"
        monthly_data[key] += parse_amount(e.get("סכום", 0))

    sorted_months = sorted(monthly_data.keys())

    if len(sorted_months) >= 2:
        console.print("\n")
        trend_lines = []
        prev_val = None
        for m in sorted_months:
            val = monthly_data[m]
            if prev_val is not None:
                change = val - prev_val
                pct = (change / prev_val * 100) if prev_val > 0 else 0
                if change > 0:
                    indicator = f"[red]▲ +₪{change:,.0f} (+{pct:.1f}%)[/red]"
                elif change < 0:
                    indicator = f"[green]▼ ₪{change:,.0f} ({pct:.1f}%)[/green]"
                else:
                    indicator = "[dim]━ ללא שינוי[/dim]"
            else:
                indicator = ""
            trend_lines.append(f"  {m}  ₪{val:>10,.2f}  {indicator}")
            prev_val = val

        console.print(
            Panel(
                "\n".join(trend_lines),
                title="[bold]שינוי חודשי[/bold]",
                border_style="cyan",
            )
        )

    # Category trends - compare last 2 months
    if len(sorted_months) >= 2:
        last_month_key = sorted_months[-1]
        prev_month_key = sorted_months[-2]

        last_y, last_m = map(int, last_month_key.split("-"))
        prev_y, prev_m = map(int, prev_month_key.split("-"))

        last_month_exp = filter_expenses_by_month(all_expenses, last_y, last_m)
        prev_month_exp = filter_expenses_by_month(all_expenses, prev_y, prev_m)

        last_cats = calc_category_totals(last_month_exp)
        prev_cats = calc_category_totals(prev_month_exp)

        all_cats = set(list(last_cats.keys()) + list(prev_cats.keys()))

        comp_table = Table(
            title=f"השוואת קטגוריות: {prev_month_key} מול {last_month_key}",
            box=box.ROUNDED,
            border_style="cyan",
        )
        comp_table.add_column("קטגוריה", style="cyan", width=20)
        comp_table.add_column(prev_month_key, justify="right", width=12)
        comp_table.add_column(last_month_key, justify="right", width=12)
        comp_table.add_column("שינוי", justify="right", width=15)

        for cat in sorted(all_cats):
            prev_val = prev_cats.get(cat, 0)
            last_val = last_cats.get(cat, 0)
            change = last_val - prev_val
            if change > 0:
                change_str = f"[red]+₪{change:,.0f}[/red]"
            elif change < 0:
                change_str = f"[green]₪{change:,.0f}[/green]"
            else:
                change_str = "[dim]---[/dim]"
            comp_table.add_row(
                cat,
                f"₪{prev_val:,.0f}",
                f"₪{last_val:,.0f}",
                change_str,
            )

        console.print(comp_table)

    # Average daily spending
    total_days = (last_date - first_date).days + 1
    total_spent = sum(parse_amount(e.get("סכום", 0)) for _, e in dated_expenses)
    avg_daily = total_spent / total_days if total_days > 0 else 0

    console.print(
        Panel(
            f"  ממוצע יומי: [bold]₪{avg_daily:,.2f}[/bold]\n"
            f"  ממוצע שבועי: [bold]₪{avg_daily * 7:,.2f}[/bold]\n"
            f"  ממוצע חודשי: [bold]₪{avg_daily * 30:,.2f}[/bold]\n"
            f"  תחזית שנתית: [bold]₪{avg_daily * 365:,.2f}[/bold]",
            title="[bold]ממוצעים ותחזית[/bold]",
            border_style="green",
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main Application Loop
# ─────────────────────────────────────────────────────────────────────────────


def main():
    console.print(
        Panel(
            "[bold cyan]מנהל ההוצאות[/bold cyan]\n"
            "[dim]ניהול הוצאות מלא עם Google Sheets[/dim]",
            box=box.DOUBLE,
            border_style="cyan",
        )
    )

    # Configuration
    creds_path = os.environ.get("EXPENSE_CREDENTIALS", CREDENTIALS_FILE)
    sheet_name = os.environ.get("EXPENSE_SHEET_NAME", "")

    if not sheet_name:
        sheet_name = Prompt.ask(
            "שם הגיליון ב-Google Sheets",
            default="ניהול הוצאות",
        )

    sheets = SheetsManager(sheet_name, creds_path)

    console.print()
    with console.status("[bold cyan]מתחבר ל-Google Sheets...[/bold cyan]"):
        connected = sheets.connect()

    if not connected:
        console.print("[red]לא ניתן להתחבר. בדוק את ההגדרות ונסה שנית.[/red]")
        sys.exit(1)

    console.print("[green]✓ מחובר בהצלחה![/green]")

    # Main loop
    while True:
        try:
            show_main_menu()
            choice = Prompt.ask("בחר פעולה", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"])

            if choice == "1":
                add_expense_ui(sheets)
            elif choice == "2":
                list_expenses_ui(sheets)
            elif choice == "3":
                edit_expense_ui(sheets)
            elif choice == "4":
                delete_expense_ui(sheets)
            elif choice == "5":
                search_expenses_ui(sheets)
            elif choice == "6":
                monthly_dashboard_ui(sheets)
            elif choice == "7":
                yearly_dashboard_ui(sheets)
            elif choice == "8":
                budget_management_ui(sheets)
            elif choice == "9":
                trends_analysis_ui(sheets)
            elif choice == "0":
                console.print("[bold cyan]להתראות! 👋[/bold cyan]")
                break

        except KeyboardInterrupt:
            console.print("\n[bold cyan]להתראות![/bold cyan]")
            break
        except Exception as e:
            console.print(f"[red]שגיאה: {e}[/red]")
            if Confirm.ask("להמשיך?", default=True):
                continue
            break


if __name__ == "__main__":
    main()
