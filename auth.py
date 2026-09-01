"""
auth.py
Role-based authentication for the LogiTask web dashboards.

Three separate account types exist: manager, dispatcher, and driver.
Each account only ever sees the dashboard that matches its role -
a driver account can never reach the manager or dispatcher views,
even if they know the URL (enforced in app.py with @require_role).
"""

import hashlib

# In production this would be a database table with salted, per-user
# hashes. Kept as a simple in-memory dict here for a training project.
USERS = {
    "manager1": {
        "password_hash": hashlib.sha256("Manager@2026".encode()).hexdigest(),
        "role": "manager",
        "display_name": "Thato Ngubane",
    },
    "dispatch1": {
        "password_hash": hashlib.sha256("Dispatch@2026".encode()).hexdigest(),
        "role": "dispatcher",
        "display_name": "Sipho Nkosi",
    },
    "driver1": {
        "password_hash": hashlib.sha256("Driver@2026".encode()).hexdigest(),
        "role": "driver",
        "display_name": "Thabo Mokoena",
    },
    "driver2": {
        "password_hash": hashlib.sha256("Driver@2026".encode()).hexdigest(),
        "role": "driver",
        "display_name": "Lindiwe Dube",
    },
}


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(username, password):
    """
    Return the user's account dict (including role) if the username/
    password combination is valid, otherwise None. Never reveals
    whether the username exists.
    """
    account = USERS.get(username)
    if account is None:
        return None
    if account["password_hash"] != hash_password(password):
        return None
    return {"username": username, "role": account["role"], "display_name": account["display_name"]}


def all_drivers():
    """Return {username: display_name} for every driver account."""
    return {
        username: acc["display_name"]
        for username, acc in USERS.items()
        if acc["role"] == "driver"
    }
