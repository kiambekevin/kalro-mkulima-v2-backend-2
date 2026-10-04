# apps/courses/constants.py

# Cache TTLs
CATALOGUE_CACHE_TTL = 60 * 5            # 5 minutes
COURSE_DETAIL_CACHE_TTL = 60 * 15       # 15 minutes
CURRICULUM_CACHE_TTL = 60 * 15          # 15 minutes

# Curriculum rules
MIN_LESSONS_PER_COURSE = 4
MAX_LESSONS_PER_COURSE = 120
MAX_MODULES_PER_COURSE = 20

# Default hours when not provided
DEFAULT_LESSON_MINUTES = 10

# Allowed resource kinds — kept in sync with the React resources UI
RESOURCE_KINDS = ("pdf", "tool", "link")