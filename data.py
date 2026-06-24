import json
import os
from datetime import date, datetime

DATA_FILE = "expenses.json"
SETTINGS_FILE = "settings.json"


# ── File I/O ──────────────────────────────────────────────────────────────────

def load_expenses():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_expenses(expenses):
    with open(DATA_FILE, "w") as f:
        json.dump(expenses, f, indent=4)

def load_settings():
    defaults = {"salary": 0.0, "budgets": {}}
    if not os.path.exists(SETTINGS_FILE):
        return defaults
    with open(SETTINGS_FILE, "r") as f:
        return {**defaults, **json.load(f)}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)


# ── Expenses ──────────────────────────────────────────────────────────────────

def add_expense(category: str, amount: float, expense_date: date):
    expenses = load_expenses()
    expenses.append({
        "category": category,
        "amount": round(amount, 2),
        "date": str(expense_date),
    })
    save_expenses(expenses)


# ── Search ────────────────────────────────────────────────────────────────────

def search_expenses(category="", amount=None, date_from=None, date_to=None):
    results = []
    for e in load_expenses():
        if category and category.lower() not in e["category"].lower():
            continue
        if amount is not None and e["amount"] != amount:
            continue
        expense_date = datetime.strptime(e["date"], "%Y-%m-%d").date()
        if date_from and expense_date < (date_from if isinstance(date_from, date) else datetime.strptime(str(date_from), "%Y-%m-%d").date()):
            continue
        if date_to and expense_date > (date_to if isinstance(date_to, date) else datetime.strptime(str(date_to), "%Y-%m-%d").date()):
            continue
        results.append(e)
    return results


# ── Aggregation ───────────────────────────────────────────────────────────────

def aggregate_by(field: str, expenses=None):
    if expenses is None:
        expenses = load_expenses()
    totals = {}
    for e in expenses:
        key = e[field]
        totals[key] = totals.get(key, 0) + e["amount"]
    return totals

def monthly_summary(year: int, month: int):
    expenses = [e for e in load_expenses()
                if e["date"].startswith(f"{year}-{month:02d}")]
    total = sum(e["amount"] for e in expenses)
    return {
        "expenses": expenses,
        "total": total,
        "by_category": aggregate_by("category", expenses),
        "count": len(expenses),
    }

def aggregate_by_week(year: int, month: int):
    """Sum expenses by week within a month. Returns {Week 1: total, Week 2: ...}"""
    expenses = monthly_summary(year, month)["expenses"]
    totals = {"Week 1": 0, "Week 2": 0, "Week 3": 0, "Week 4": 0}
    for e in expenses:
        day = datetime.strptime(e["date"], "%Y-%m-%d").day
        if day <= 7:
            totals["Week 1"] += e["amount"]
        elif day <= 14:
            totals["Week 2"] += e["amount"]
        elif day <= 21:
            totals["Week 3"] += e["amount"]
        else:
            totals["Week 4"] += e["amount"]
    # Remove weeks with no spending
    return {k: round(v, 2) for k, v in totals.items() if v > 0}

def cumulative_spending(year: int, month: int):
    """Return {day: cumulative_total} for every day that has spending in the month."""
    expenses = sorted(
        monthly_summary(year, month)["expenses"],
        key=lambda e: e["date"]
    )
    result = {}
    running = 0
    for e in expenses:
        day = int(e["date"].split("-")[2])
        running += e["amount"]
        result[day] = round(running, 2)
    return result


# ── Budget & Savings ──────────────────────────────────────────────────────────

def budget_status(year: int, month: int):
    settings = load_settings()
    budgets  = settings.get("budgets", {})
    by_cat   = monthly_summary(year, month)["by_category"]
    all_cats = set(budgets) | set(by_cat)
    status   = []
    for cat in sorted(all_cats):
        spent = by_cat.get(cat, 0)
        limit = budgets.get(cat)
        status.append({
            "category":   cat,
            "spent":      spent,
            "limit":      limit,
            "remaining":  round(limit - spent, 2) if limit else None,
            "over_budget": (spent > limit) if limit else False,
        })
    return status

def savings_rate(year: int, month: int):
    settings = load_settings()
    salary   = settings.get("salary", 0)
    spent    = monthly_summary(year, month)["total"]
    saved    = max(salary - spent, 0)
    rate     = round(saved / salary * 100, 1) if salary > 0 else None
    return {"salary": salary, "spent": spent, "saved": saved, "savings_rate": rate}