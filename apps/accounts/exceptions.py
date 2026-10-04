# apps/accounts/exceptions.py
from rest_framework.exceptions import APIException


class AccountLocked(APIException):
    status_code = 423
    default_detail = "Account temporarily locked after too many failed logins."
    default_code = "account_locked"


class EmailAlreadyExists(APIException):
    status_code = 409
    default_detail = "An account with this email already exists."
    default_code = "email_exists"


class PhoneAlreadyExists(APIException):
    status_code = 409
    default_detail = "An account with this phone number already exists."
    default_code = "phone_exists"