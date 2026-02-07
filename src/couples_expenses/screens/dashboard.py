"""Dashboard screen – KPIs, charts, and export."""

from datetime import datetime, timedelta

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from couples_expenses.core.constants import CATEGORY_COLORS, PARTNER_COLORS
from couples_expenses.core.analytics import month_kpis
from couples_expenses.core.charts import draw_pie_chart, draw_bar_chart
from couples_expenses.core.export import export_csv, export_json


def _last_months(n: int = 18) -> list[str]:
    today = datetime.now()
    months = []
    for i in range(n):
        d = today.replace(day=1) - timedelta(days=i * 28)
        ym = d.strftime("%Y-%m")
        if ym not in months:
            months.append(ym)
    return sorted(set(months), reverse=True)[:n]


def build_dashboard_box(app: toga.App) -> toga.Box:
    month_items = _last_months()

    month_select = toga.Selection(
        items=month_items,
        style=Pack(flex=1, padding=5),
    )

    kpi_label = toga.Label("", style=Pack(padding=10, font_size=13))

    pie_canvas = toga.Canvas(style=Pack(width=360, height=280, padding=5))
    bar_canvas = toga.Canvas(style=Pack(width=360, height=280, padding=5))

    def refresh(widget=None):
        ym = month_select.value
        if not ym:
            return
        db_path = app.paths.data / "expenses.db"
        kpis = month_kpis(db_path, ym)

        # Build KPI text
        lines = [f"Month: {ym}", f"Total: {kpis['total_display']}"]
        if kpis["category_display"]:
            lines.append("By category:")
            for k, v in kpis["category_display"].items():
                lines.append(f"  {k}: {v}")
        if kpis["partner_display"]:
            lines.append("By partner:")
            for k, v in kpis["partner_display"].items():
                lines.append(f"  {k}: {v}")
        kpi_label.text = "\n".join(lines)

        draw_pie_chart(
            pie_canvas, kpis["by_category_cents"], CATEGORY_COLORS, 360, 280
        )
        draw_bar_chart(
            bar_canvas, kpis["by_partner_cents"], PARTNER_COLORS, 360, 280
        )

    month_select.on_change = refresh

    def on_export(widget):
        ym = month_select.value
        if not ym:
            return
        db_path = app.paths.data / "expenses.db"
        out_dir = app.paths.data
        csv_path = export_csv(db_path, ym, out_dir)
        json_path = export_json(db_path, ym, out_dir)
        app.main_window.info_dialog(
            "Exported",
            f"CSV: {csv_path}\nJSON: {json_path}\n\n"
            "Files are stored in the app's private data directory.",
        )

    export_btn = toga.Button(
        "Export CSV & JSON",
        on_press=on_export,
        style=Pack(padding=10, width=200),
    )

    charts_row = toga.Box(
        style=Pack(direction=ROW, padding=5),
        children=[
            toga.Box(
                style=Pack(direction=COLUMN),
                children=[toga.Label("Spending by Category", style=Pack(padding=5)), pie_canvas],
            ),
            toga.Box(
                style=Pack(direction=COLUMN),
                children=[toga.Label("Spending by Partner", style=Pack(padding=5)), bar_canvas],
            ),
        ],
    )

    box = toga.Box(
        style=Pack(direction=COLUMN, padding=10),
        children=[
            toga.Label("Dashboard", style=Pack(font_size=18, padding_bottom=10)),
            month_select,
            kpi_label,
            charts_row,
            export_btn,
        ],
    )

    box._refresh = refresh
    return box
