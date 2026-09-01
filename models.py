"""
models.py
Task data model and JSON-file persistence for the LogiTask web dashboards.

Extends the original LogiTask-System task record with the fields the
Manager, Dispatcher, and Driver dashboards need: pickup/drop-off
locations, an assigned driver, a task type, and miles driven (used in
manager reports).
"""

import json
import os
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "tasks.json")

VALID_PRIORITIES = ("Low", "Medium", "High")
VALID_STATUSES = ("Pending", "In Progress", "Completed")
VALID_TASK_TYPES = ("Delivery", "Pickup", "Maintenance", "Inspection")


class ValidationError(Exception):
    """Raised when task input data fails validation."""
    pass


def _load():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save(tasks):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)


def get_all_tasks():
    return _load()


def get_task(task_id):
    for t in _load():
        if t["id"] == task_id:
            return t
    return None


def get_tasks_for_driver(match_names):
    """
    Return tasks assigned to this driver. match_names is a set/list of
    strings (e.g. the logged-in driver's username AND display name) -
    since assigned_to is now free text typed by a dispatcher, a task
    counts as "theirs" if assigned_to matches any of those names
    (case-insensitive, whitespace-trimmed).
    """
    wanted = {n.strip().lower() for n in match_names if n}
    return [
        t for t in _load()
        if t.get("assigned_to") and t["assigned_to"].strip().lower() in wanted
    ]


def distinct_driver_names():
    """
    Return a sorted list of every driver name that has ever been typed
    into assigned_to, for use as autocomplete suggestions - not a
    restriction on what can be typed.
    """
    tasks = _load()
    names = {t["assigned_to"].strip() for t in tasks if t.get("assigned_to")}
    return sorted(names)


def create_task(title, pickup_location=None, dropoff_location=None, task_type="Delivery",
                 priority="Medium", due_date=None, assigned_to=None):
    """
    Create a new task. Only the title is required - pickup location,
    drop-off location, and the assigned driver are all optional and can
    be any free text the dispatcher chooses (not limited to a fixed
    list of locations or registered driver accounts).
    """
    if not title or not title.strip():
        raise ValidationError("Task title cannot be empty.")
    if task_type not in VALID_TASK_TYPES:
        raise ValidationError(f"Task type must be one of {VALID_TASK_TYPES}.")
    if priority not in VALID_PRIORITIES:
        raise ValidationError(f"Priority must be one of {VALID_PRIORITIES}.")

    tasks = _load()
    next_id = max((t["id"] for t in tasks), default=0) + 1

    pickup = pickup_location.strip() if pickup_location and pickup_location.strip() else "Not specified"
    dropoff = dropoff_location.strip() if dropoff_location and dropoff_location.strip() else "Not specified"
    driver = assigned_to.strip() if assigned_to and assigned_to.strip() else None

    task = {
        "id": next_id,
        "title": title.strip(),
        "pickup_location": pickup,
        "dropoff_location": dropoff,
        "task_type": task_type,
        "priority": priority,
        "due_date": due_date or datetime.now().strftime("%Y-%m-%d"),
        "status": "Pending",
        "assigned_to": driver,
        "miles_driven": 0,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    tasks.append(task)
    _save(tasks)
    return task


def update_task_status(task_id, new_status, miles_driven=None):
    if new_status not in VALID_STATUSES:
        raise ValidationError(f"Status must be one of {VALID_STATUSES}.")

    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = new_status
            if miles_driven is not None:
                try:
                    t["miles_driven"] = float(miles_driven)
                except (TypeError, ValueError):
                    raise ValidationError("Miles driven must be a number.")
            _save(tasks)
            return t
    raise ValidationError(f"Task not found: no task with ID {task_id}.")


def assign_driver(task_id, driver_name):
    """
    Assign any free-typed name to a task - not limited to a registered
    driver account. An empty value clears the assignment (Unassigned).
    """
    driver_name = driver_name.strip() if driver_name and driver_name.strip() else None
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            t["assigned_to"] = driver_name
            _save(tasks)
            return t
    raise ValidationError(f"Task not found: no task with ID {task_id}.")


def filter_tasks(date_from=None, date_to=None, driver=None, task_type=None):
    """
    driver, if given, matches case-insensitively against whatever name
    was typed into assigned_to (partial match, since it's free text).
    """
    tasks = _load()
    driver_lower = driver.strip().lower() if driver else None
    results = []
    for t in tasks:
        if date_from and t["due_date"] < date_from:
            continue
        if date_to and t["due_date"] > date_to:
            continue
        if driver_lower and driver_lower not in (t.get("assigned_to") or "").lower():
            continue
        if task_type and t["task_type"] != task_type:
            continue
        results.append(t)
    return results


def driver_performance():
    """Return {driver_name: completed_task_count} for the bar chart, using
    whatever name text was assigned to each task."""
    tasks = _load()
    counts = {}
    for t in tasks:
        if t["status"] == "Completed" and t.get("assigned_to"):
            counts[t["assigned_to"]] = counts.get(t["assigned_to"], 0) + 1
    return counts


def seed_demo_data():
    """Populate the data file with realistic demo tasks, if empty."""
    if _load():
        return
    demo = [
        ("Deliver medical supplies", "Johannesburg CBD", "Sandton Clinic", "Delivery", "High", "Thabo Mokoena", "Completed", 42),
        ("Collect returned stock", "Midrand Depot", "Johannesburg CBD", "Pickup", "Medium", "Lindiwe Dube", "Completed", 18),
        ("Deliver furniture order", "Pretoria Warehouse", "Centurion", "Delivery", "Medium", "Thabo Mokoena", "In Progress", 0),
        ("Weekly vehicle inspection", "Midrand Depot", "Midrand Depot", "Inspection", "Low", "Lindiwe Dube", "Pending", 0),
        ("Deliver retail restock", "Midrand Depot", "Fourways Mall", "Delivery", "High", None, "Pending", 0),
        ("Fleet maintenance check", "Midrand Depot", "Midrand Depot", "Maintenance", "Low", "Thabo Mokoena", "Completed", 0),
        ("Deliver e-commerce parcels", "Johannesburg CBD", "Roodepoort", "Delivery", "Medium", "Lindiwe Dube", "Pending", 0),
    ]
    tasks = []
    for i, (title, pickup, dropoff, ttype, pri, drv, status, miles) in enumerate(demo, start=1):
        tasks.append({
            "id": i,
            "title": title,
            "pickup_location": pickup,
            "dropoff_location": dropoff,
            "task_type": ttype,
            "priority": pri,
            "due_date": "2026-08-2" + str(i % 9),
            "status": status,
            "assigned_to": drv,
            "miles_driven": miles,
            "created_at": "2026-08-20 09:00:00",
        })
    _save(tasks)
