# apps/common/constants.py

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Language codes used across content and preferences
LANGUAGE_EN = "en"
LANGUAGE_SW = "sw"
LANGUAGE_CHOICES = [(LANGUAGE_EN, "English"), (LANGUAGE_SW, "Kiswahili")]

# Kenya regions (used by counties and dashboard filters)
KENYA_REGIONS = [
    "Coast",
    "North Eastern",
    "Eastern",
    "Central",
    "Rift Valley",
    "Western",
    "Nyanza",
    "Nairobi",
]

# Roles that count as staff-facing for permission shortcuts
STAFF_ROLES = ("trainer", "researcher", "county", "admin")

# A soft-deleted row is auto-purged after this many days
SOFT_DELETE_RETENTION_DAYS = 90

# Max length used by CharField defaults across apps
SHORT_TEXT = 80
MEDIUM_TEXT = 180
LONG_TEXT = 400