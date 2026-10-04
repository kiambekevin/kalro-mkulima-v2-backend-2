# apps/dashboard/constants.py

# Cache TTLs (seconds)
LEARNER_DASHBOARD_TTL = 60 * 3       # 3 minutes
COUNTY_DASHBOARD_TTL = 60 * 15       # 15 minutes
ACTIVITY_WINDOW_DAYS = 7

# Streak rule: a day counts as "active" when the learner completes at
# least one lesson OR downloads one lesson for offline use.
MIN_LESSONS_FOR_ACTIVE_DAY = 1

# Dashboard limits
MAX_IN_PROGRESS = 3
MAX_RECOMMENDED = 3
MAX_RECENT_BADGES = 3
MAX_FIELD_DAYS = 3

# Roles allowed to view county-level aggregates
COUNTY_DASHBOARD_ROLES = ("county", "admin")

# Gender + age brackets used across reports and dashboards
AGE_BRACKETS = [
    ("youth",   (18, 35)),
    ("adult",   (36, 60)),
    ("senior",  (61, 120)),
]