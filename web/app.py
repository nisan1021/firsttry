"""Flask web app – Couples Expenses."""

import csv
import io
import json
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    Response,
)

from config import SECRET_KEY, APP_USERNAME, APP_PASSWORD, DB_PATH
from db import (
    CATEGORIES,
    PARTNERS,
    CATEGORY_COLORS,
    PARTNER_COLORS,
    init_db,
    add_expense,
    list_expenses,
    delete_expense,
    get_month_summary,
    get_available_months,
)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# --------------- Auth ---------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == APP_USERNAME and password == APP_PASSWORD:
            session["logged_in"] = True
            flash("ברוכים הבאים!", "success")
            return redirect(url_for("add_expense_route"))
        flash("שם משתמש או סיסמה שגויים", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --------------- Add Expense ---------------

@app.route("/", methods=["GET", "POST"])
@app.route("/add", methods=["GET", "POST"])
@login_required
def add_expense_route():
    if request.method == "POST":
        try:
            amount_float = float(request.form["amount"])
        except (ValueError, KeyError):
            flash("סכום לא תקין", "error")
            return redirect(url_for("add_expense_route"))

        if amount_float <= 0:
            flash("הסכום חייב להיות גדול מ-0", "error")
            return redirect(url_for("add_expense_route"))

        description = request.form.get("description", "").strip()
        if not description:
            flash("תיאור הוא שדה חובה", "error")
            return redirect(url_for("add_expense_route"))

        category = request.form.get("category", CATEGORIES[0])
        is_essential = request.form.get("is_essential") == "1"
        paid_by = request.form.get("paid_by", PARTNERS[0])

        raw_ts = request.form.get("expense_ts", "")
        try:
            dt = datetime.fromisoformat(raw_ts)
            expense_ts = dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            expense_ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        amount_cents = round(amount_float * 100)
        add_expense(DB_PATH, amount_cents, description, category, is_essential, paid_by, expense_ts)

        flash("ההוצאה נשמרה בהצלחה!", "success")
        return redirect(url_for("expense_list"))

    default_dt = datetime.now().strftime("%Y-%m-%dT%H:%M")
    return render_template(
        "add_expense.html",
        categories=CATEGORIES,
        partners=PARTNERS,
        default_datetime=default_dt,
    )


# --------------- Expense List ---------------

@app.route("/list")
@login_required
def expense_list():
    month = request.args.get("month", "")
    category = request.args.get("category", "")
    paid_by = request.args.get("paid_by", "")

    expenses = list_expenses(
        DB_PATH,
        year_month=month or None,
        category=category or None,
        paid_by=paid_by or None,
    )
    months = get_available_months(DB_PATH)

    return render_template(
        "expense_list.html",
        expenses=expenses,
        months=months,
        categories=CATEGORIES,
        partners=PARTNERS,
        selected_month=month,
        selected_category=category,
        selected_paid_by=paid_by,
    )


# --------------- Delete ---------------

@app.route("/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense_route(expense_id):
    delete_expense(DB_PATH, expense_id)
    flash("ההוצאה נמחקה", "success")
    return redirect(url_for("expense_list"))


# --------------- Dashboard ---------------

@app.route("/dashboard")
@login_required
def dashboard():
    months = get_available_months(DB_PATH)
    selected = request.args.get("month", "")

    summary = None
    cat_labels = cat_values = cat_colors = []
    part_labels = part_values = part_colors = []

    if selected:
        summary = get_month_summary(DB_PATH, selected)
        cat_labels = list(summary["by_category_cents"].keys())
        cat_values = list(summary["by_category_cents"].values())
        cat_colors = [CATEGORY_COLORS.get(c, "#999") for c in cat_labels]
        part_labels = list(summary["by_partner_cents"].keys())
        part_values = list(summary["by_partner_cents"].values())
        part_colors = [PARTNER_COLORS.get(p, "#999") for p in part_labels]

    return render_template(
        "dashboard.html",
        months=months,
        selected_month=selected,
        summary=summary,
        cat_labels=cat_labels,
        cat_values=cat_values,
        cat_colors=cat_colors,
        part_labels=part_labels,
        part_values=part_values,
        part_colors=part_colors,
    )


# --------------- Export ---------------

@app.route("/export")
@login_required
def export_data():
    month = request.args.get("month", "")
    fmt = request.args.get("format", "csv")

    if not month:
        flash("בחר חודש לייצוא", "error")
        return redirect(url_for("dashboard"))

    rows = list_expenses(DB_PATH, year_month=month)

    if fmt == "json":
        data = json.dumps(rows, ensure_ascii=False, indent=2)
        return Response(
            data,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename=expenses_{month}.json"},
        )

    # CSV
    output = io.StringIO()
    fieldnames = ["id", "amount_cents", "description", "category", "is_essential", "paid_by", "expense_ts", "created_at"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=expenses_{month}.csv"},
    )


# --------------- Init & Run ---------------

if __name__ == "__main__":
    init_db(DB_PATH)
    app.run(debug=True, host="0.0.0.0", port=5000)
