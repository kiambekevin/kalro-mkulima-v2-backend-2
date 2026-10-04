# api/parsers.py
"""
Parsers accepted by the API. Restricting the list keeps attack
surface small and prevents accidental XML/YAML parsing.
"""
from rest_framework.parsers import (
    FormParser,
    JSONParser,
    MultiPartParser,
)

# Default for most endpoints
DEFAULT_PARSERS = (JSONParser, FormParser)

# For endpoints that accept file uploads (media, avatars)
UPLOAD_PARSERS = (MultiPartParser, FormParser, JSONParser)