# apps/fielddays/constants.py

# Reminder windows (hours before the event start)
REMINDER_WINDOWS_HOURS = [48, 24, 2]

# Booking window: a user cannot book after this many minutes past start
BOOKING_CUTOFF_MINUTES = 30

# Check-in window: how early / late a check-in is accepted (minutes)
CHECKIN_EARLY_MINUTES = 60
CHECKIN_LATE_MINUTES = 120

# Waitlist rules
WAITLIST_ENABLED = True
WAITLIST_EXPIRY_HOURS = 6      # waitlisted users lose their spot after this

# Reference length for a booking code (used in the QR on the ticket)
BOOKING_CODE_LENGTH = 8

# Status enum values (mirrored in models)
STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"
STATUS_CANCELLED = "cancelled"
STATUS_COMPLETED = "completed"

BOOKING_STATUS_CONFIRMED = "confirmed"
BOOKING_STATUS_WAITLISTED = "waitlisted"
BOOKING_STATUS_CANCELLED = "cancelled"
BOOKING_STATUS_ATTENDED = "attended"
BOOKING_STATUS_NO_SHOW = "no_show"