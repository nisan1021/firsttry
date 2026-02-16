# CLAUDE.md

This file provides guidance for AI assistants working with this repository.

## Project Overview

Couples expense tracking system with two separate applications:

1. **BeeWare/Toga Desktop App** (`src/couples_expenses/`) — Cross-platform GUI targeting macOS, Linux, Windows, iOS, Android
2. **Standalone CLI App** (`expense_manager.py`) — Rich terminal interface backed by Google Sheets

Both apps are fully localized in Hebrew with Israeli Shekel (₪) currency.

## Repository Structure

```
├── expense_manager.py             # Standalone CLI app (Google Sheets backend)
├── src/couples_expenses/          # BeeWare/Toga GUI app
│   ├── app.py                     # App entry point and navigation
│   ├── core/
│   │   ├── analytics.py           # KPI calculations and formatting
│   │   ├── charts.py              # Canvas-based chart rendering
│   │   ├── constants.py           # Categories, partners, colors, date formats
│   │   ├── db.py                  # SQLite data layer
│   │   └── export.py              # CSV/JSON export
│   └── screens/
│       ├── add_expense.py         # Expense entry form
│       ├── dashboard.py           # KPIs, charts, export controls
│       └── expense_list.py        # Filterable expense table with delete
├── tests/
│   └── test_analytics.py          # Unit tests for db and analytics modules
├── index.html / style.css         # GitHub Pages static site
├── pyproject.toml                 # Briefcase build config + pytest settings
├── requirements.txt               # CLI app dependencies (gspread, google-auth, rich)
└── SETUP.md                       # Setup guide (Hebrew)
```

## Development Commands

### Running Tests

```bash
pytest
# or explicitly:
python -m pytest tests/
```

Tests use temporary SQLite databases via `tempfile`/`tmp_path` fixtures. No external services required.

### Running the Desktop App

```bash
briefcase dev
```

Requires Toga installed for your platform (toga-gtk on Linux, toga-cocoa on macOS, toga-winforms on Windows).

### Running the CLI App

```bash
pip install -r requirements.txt
python expense_manager.py
```

Requires environment variables:
- `EXPENSE_CREDENTIALS` — path to Google Cloud service account JSON key
- `EXPENSE_SHEET_NAME` — name of the Google Sheet to use

### Building for Distribution

```bash
briefcase build
briefcase package
```

## Architecture Notes

### Desktop App (src/couples_expenses/)

- **UI Framework**: Toga (BeeWare) — native widgets, no web views
- **Data Storage**: SQLite via stdlib `sqlite3` (no ORM)
- **Charts**: Custom canvas rendering in `charts.py` (pie and bar charts)
- **Analytics**: Pure Python aggregations in `analytics.py` (no numpy/pandas)
- **Screen navigation**: Button-based switching between AddExpenseBox, ExpenseListBox, DashboardBox

### SQLite Schema

Single `expenses` table:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `amount_cents` INTEGER NOT NULL (stored as cents)
- `description` TEXT NOT NULL
- `category` TEXT NOT NULL
- `is_essential` INTEGER (boolean, default 0)
- `paid_by` TEXT NOT NULL
- `expense_ts` TEXT NOT NULL (ISO format)
- `created_at` TEXT NOT NULL (ISO format)

### CLI App (expense_manager.py)

- Self-contained single file (~1100 lines)
- Uses Rich for terminal UI
- Google Sheets as backend via gspread
- Auto-creates worksheets ("Expenses" and "Budget")

## Key Conventions

- **Language**: All user-facing strings are in Hebrew
- **Currency**: Amounts displayed as ₪X.XX, stored as integer cents in SQLite
- **Categories**: Defined in `constants.py` — רכב, קניות אוכל, קניות ביגוד, אחרים
- **Partners**: בן/בת זוג A and בן/בת זוג B
- **Date formats**: ISO (`%Y-%m-%dT%H:%M:%S`) for storage, `%Y-%m-%d %H:%M` for input
- **Type hints**: Used in function signatures
- **Docstrings**: Present on public functions

## Testing Conventions

- Test file: `tests/test_analytics.py`
- Test classes: `TestDb`, `TestMonthSummary`, `TestAnalytics`
- Fixtures create isolated temp databases — no shared state between tests
- Test data uses Hebrew categories and partner names matching production constants
- Pytest is configured in `pyproject.toml` under `[tool.pytest.ini_options]`
