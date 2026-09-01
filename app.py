"""
app.py
Flask web application for the LogiTask dashboards (Manager, Dispatcher,
Driver), built from the approved wireframes.

Run with: python3 app.py
Then open: http://127.0.0.1:5000
"""

import io
import csv
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, session, send_file, flash
)

import models
import auth

app = Flask(__name__)
app.secret_key = "logitask-training-project-secret-key"  # fine for a training project

models.seed_demo_data()


# helpers
def require_role(role):
    """Decorator: only allow access if the logged-in user has this role."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if session.get("role") != role:
                return redirect(url_for("login"))
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


def counts_for(tasks):
    active = sum(1 for t in tasks if t["status"] != "Completed")
    completed = sum(1 for t in tasks if t["status"] == "Completed")
    return active, completed


# auth
@app.route("/", methods=["GET"])
def index():
    if session.get("role") == "manager":
        return redirect(url_for("manager_dashboard"))
    if session.get("role") == "dispatcher":
        return redirect(url_for("dispatcher_dashboard"))
    if session.get("role") == "driver":
        return redirect(url_for("driver_dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    role_tab = request.values.get("role", "manager")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        account = auth.authenticate(username, password)

        if account is None:
            error = "Invalid username or password."
        elif account["role"] != role_tab:
            error = f"That account is not registered as a {role_tab}."
        else:
            session["username"] = account["username"]
            session["role"] = account["role"]
            session["display_name"] = account["display_name"]
            return redirect(url_for(f"{account['role']}_dashboard"))

    return render_template("login.html", error=error, role_tab=role_tab)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# Manager
@app.route("/manager")
@require_role("manager")
def manager_dashboard():
    tasks = models.get_all_tasks()
    active, completed = counts_for(tasks)
    performance = models.driver_performance()
    perf_chart = [{"driver": name, "completed": c} for name, c in performance.items()]
    suggestions = sorted(set(auth.all_drivers().values()) | set(models.distinct_driver_names()))
    return render_template(
        "manager.html",
        active=active,
        completed=completed,
        perf_chart=perf_chart,
        driver_suggestions=suggestions,
        task_types=models.VALID_TASK_TYPES,
        report_rows=None,
        page_title="Manager Dashboard",
        role_label="MANAGER",
    )


@app.route("/manager/report", methods=["POST"])
@require_role("manager")
def manager_report():
    tasks = models.get_all_tasks()
    active, completed = counts_for(tasks)
    performance = models.driver_performance()
    perf_chart = [{"driver": name, "completed": c} for name, c in performance.items()]
    suggestions = sorted(set(auth.all_drivers().values()) | set(models.distinct_driver_names()))

    date_from = request.form.get("date_from") or None
    date_to = request.form.get("date_to") or None
    driver = request.form.get("driver") or None
    task_type = request.form.get("task_type") or None

    filtered = models.filter_tasks(date_from, date_to, driver, task_type)
    report_rows = [
        {
            "date": t["due_date"],
            "driver": t.get("assigned_to") or "Unassigned",
            "task": t["title"],
            "miles": t["miles_driven"],
            "status": t["status"],
        }
        for t in filtered
    ]
    session["last_report"] = report_rows

    return render_template(
        "manager.html",
        active=active,
        completed=completed,
        perf_chart=perf_chart,
        driver_suggestions=suggestions,
        task_types=models.VALID_TASK_TYPES,
        report_rows=report_rows,
        submitted=True,
        page_title="Manager Dashboard",
        role_label="MANAGER",
    )


@app.route("/manager/export/<fmt>")
@require_role("manager")
def manager_export(fmt):
    rows = session.get("last_report") or []

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Date", "Driver", "Task", "Miles Driven", "Status"])
        for r in rows:
            writer.writerow([r["date"], r["driver"], r["task"], r["miles"], r["status"]])
        mem = io.BytesIO(buf.getvalue().encode("utf-8"))
        return send_file(mem, mimetype="text/csv", as_attachment=True,
                          download_name="logitask_report.csv")

    if fmt == "pdf":
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "LogiTask Report Summary", ln=True)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(30, 8, "Date", border=1)
        pdf.cell(40, 8, "Driver", border=1)
        pdf.cell(60, 8, "Task", border=1)
        pdf.cell(25, 8, "Miles", border=1)
        pdf.cell(30, 8, "Status", border=1, ln=True)
        pdf.set_font("Helvetica", "", 10)
        for r in rows:
            pdf.cell(30, 8, str(r["date"]), border=1)
            pdf.cell(40, 8, str(r["driver"])[:18], border=1)
            pdf.cell(60, 8, str(r["task"])[:28], border=1)
            pdf.cell(25, 8, str(r["miles"]), border=1)
            pdf.cell(30, 8, str(r["status"]), border=1, ln=True)
        mem = io.BytesIO(pdf.output())
        return send_file(mem, mimetype="application/pdf", as_attachment=True,
                          download_name="logitask_report.pdf")

    return redirect(url_for("manager_dashboard"))


# Dispatcher
@app.route("/dispatcher")
@require_role("dispatcher")
def dispatcher_dashboard():
    tasks = models.get_all_tasks()
    active, completed = counts_for(tasks)
    registered_drivers = auth.all_drivers()
    # Suggestions include registered driver accounts plus any name a
    # dispatcher has already typed, but typing a brand new name is
    # always allowed too (e.g. an outsourced or contract driver).
    suggestions = sorted(set(registered_drivers.values()) | set(models.distinct_driver_names()))
    return render_template(
        "dispatcher.html",
        tasks=tasks,
        active=active,
        completed=completed,
        drivers_available=len(registered_drivers),
        driver_suggestions=suggestions,
        task_types=models.VALID_TASK_TYPES,
        page_title="Dispatcher Dashboard",
        role_label="DISPATCHER",
    )


@app.route("/dispatcher/create_task", methods=["POST"])
@require_role("dispatcher")
def dispatcher_create_task():
    try:
        models.create_task(
            title=request.form.get("title", ""),
            pickup_location=request.form.get("pickup_location", ""),
            dropoff_location=request.form.get("dropoff_location", ""),
            task_type=request.form.get("task_type", "Delivery"),
            priority=request.form.get("priority", "Medium"),
            due_date=request.form.get("due_date") or None,
            assigned_to=request.form.get("assigned_to") or None,
        )
        flash("Task created successfully.", "success")
    except models.ValidationError as e:
        flash(str(e), "error")
    return redirect(url_for("dispatcher_dashboard"))


@app.route("/dispatcher/assign_driver", methods=["POST"])
@require_role("dispatcher")
def dispatcher_assign_driver():
    task_id = int(request.form.get("task_id"))
    driver = request.form.get("driver") or None
    try:
        models.assign_driver(task_id, driver)
        flash("Driver assigned.", "success")
    except models.ValidationError as e:
        flash(str(e), "error")
    return redirect(url_for("dispatcher_dashboard"))


# Driver
@app.route("/driver")
@require_role("driver")
def driver_dashboard():
    status_filter = request.args.get("status", "Pending")
    all_tasks = models.get_tasks_for_driver({session["username"], session["display_name"]})
    if status_filter == "All":
        tasks = all_tasks
    else:
        tasks = [t for t in all_tasks if t["status"] == status_filter]
    return render_template(
        "driver.html",
        tasks=tasks,
        status_filter=status_filter,
        statuses=models.VALID_STATUSES,
        page_title="Driver Dashboard",
        role_label="DRIVER",
    )


@app.route("/driver/update_status", methods=["POST"])
@require_role("driver")
def driver_update_status():
    task_id = int(request.form.get("task_id"))
    new_status = request.form.get("status")
    miles = request.form.get("miles_driven") or None
    try:
        models.update_task_status(task_id, new_status, miles_driven=miles)
        flash("Status updated.", "success")
    except models.ValidationError as e:
        flash(str(e), "error")
    return redirect(url_for("driver_dashboard", status=request.form.get("current_tab", "Pending")))


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
