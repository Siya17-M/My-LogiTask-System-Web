# LogiTask Web Dashboards

A Flask web application implementing the Manager, Dispatcher, and Driver
dashboards from the approved wireframes.

## Setup

```
pip install flask fpdf2
python3 app.py
```

Then open http://127.0.0.1:5000 in a browser.

## Demo accounts (separate login per role)

| Role       | Username    | Password        |
|------------|-------------|------------------|
| Manager    | manager1    | Manager@2026     |
| Dispatcher | dispatch1   | Dispatch@2026    |
| Driver     | driver1     | Driver@2026      |
| Driver     | driver2     | Driver@2026      |

Each account only ever sees its own dashboard - a driver account
cannot reach the manager or dispatcher pages even by typing the URL
directly.

## Assigning tasks and locations

Pickup location, drop-off location, and the assigned driver are all
**optional, free-text fields**:

- Leaving pickup/drop-off blank saves the task as "Not specified".
- The dispatcher can type *any* name into the driver field - it does
  not have to match a registered driver account (useful for
  contractors or informal assignments). Existing names are offered as
  autocomplete suggestions, but typing something new is always allowed.
- A driver's own dashboard shows tasks where the assigned name matches
  either their username or their display name (case-insensitive).

## Files

- `app.py` - Flask routes for login and all three dashboards
- `auth.py` - role-based login accounts (hashed passwords)
- `models.py` - task data model, JSON storage, validation, filtering
- `templates/` - Jinja2 templates for login + each dashboard
- `static/css/style.css` - design system (navy/amber, route-line motif)
- `data/tasks.json` - created automatically on first run (seeded with demo data)

## Reports

The Manager dashboard's Reports panel filters by date range, driver
name (partial match), and task type, then supports **Export CSV** and
**Export PDF** of the generated report.
