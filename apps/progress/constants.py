# apps/progress/constants.py

# A streak day requires at least this many lessons completed
MIN_LESSONS_FOR_STREAK_DAY = 1

# Daily activity recompute window — how far back we recalc on-demand
ACTIVITY_REBUILD_DAYS = 30

# Progress is considered complete at 100%
COMPLETION_THRESHOLD = 100

# Cache keys
CACHE_PROGRESS_PREFIX = "progress:course"
CACHE_STREAK_PREFIX = "progress:streak"
CACHE_TTL_SHORT = 60          # 1 min
CACHE_TTL_MEDIUM = 60 * 5     # 5 min
CACHE_TTL_LONG = 60 * 30      # 30 min