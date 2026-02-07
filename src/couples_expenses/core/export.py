"""Export expenses to CSV and JSON files."""

import csv
import json
from pathlib import Path
from couples_expenses.core.db import list_expenses


def _rows_for_month(db_path: Path, year_month: str) -> list[dict]:
    return list_expenses(db_path, year_month=year_month)


def export_csv(db_path: Path, year_month: str, out_dir: Path) -> Path:
    rows = _rows_for_month(db_path, year_month)
    filename = f"expenses_{year_month}.csv"
    out_path = out_dir / filename

    fieldnames = [
        "id", "amount_cents", "description", "category",
        "is_essential", "paid_by", "expense_ts", "created_at",
    ]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return out_path


def export_json(db_path: Path, year_month: str, out_dir: Path) -> Path:
    rows = _rows_for_month(db_path, year_month)
    filename = f"expenses_{year_month}.json"
    out_path = out_dir / filename

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    return out_path
