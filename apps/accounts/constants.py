# apps/accounts/constants.py

# Kenyan phone — matches +254 7XX XXX XXX, 07XX XXX XXX, 01XX XXX XXX
KENYAN_PHONE_REGEX = r"^(?:\+?254|0)(?:7\d{8}|1\d{8})$"

# Password policy (mirrors Django validators + extras)
MIN_PASSWORD_LENGTH = 8
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

# Reserve some email domains we never want to accept
DISALLOWED_EMAIL_DOMAINS = {
    "example.com",
    "test.com",
    "mailinator.com",
}