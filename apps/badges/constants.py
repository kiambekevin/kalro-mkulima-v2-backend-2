# apps/badges/constants.py

# PNG rasterisation target size (square). 2x the largest on-screen preview.
BADGE_PNG_SIZE = 960

# Default colours used when a Subject has no custom BadgeTemplate yet
DEFAULT_TINT = "#123B26"
DEFAULT_ACCENT = "#F0B429"
DEFAULT_ICON = "fa-solid fa-award"

# Verification rate limit: max lookups per IP per minute
VERIFY_RATE_LIMIT_PER_MIN = 60

# Snapshot schema version — bump if the badge JSON structure changes so we
# can migrate old badges without re-issuing them.
SNAPSHOT_VERSION = 1

# Brand strings used in the SVG/PNG renderer
BRAND_NAME = "KALRO"
BRAND_SUB = "MKULIMA"
BRAND_TAGLINE = "Kenya Agricultural & Livestock Research Organization"