"""
utils/security.py
─────────────────
Central security utilities for KarmayogAI:
  - Input sanitization (XSS prevention)
  - Input validation helpers
  - File upload validation (MIME + magic bytes)
  - CSRF double-submit cookie helpers
  - Rate-limit helpers (in-memory, per-IP)
"""

import re
import os
import hmac
import hashlib
import secrets
import time
from collections import defaultdict
from functools import wraps
from flask import request, jsonify, g
import html

# ─────────────────────────────────────────────────────────
# XSS / Input Sanitization
# ─────────────────────────────────────────────────────────

def sanitize_string(value: str, max_length: int = 500) -> str:
    """
    Escape HTML entities and strip leading/trailing whitespace.
    Raises ValueError if value exceeds max_length.
    """
    if not isinstance(value, str):
        return value
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length}")
    return html.escape(value, quote=True)


def sanitize_dict(data: dict, schema: dict) -> dict:
    """
    Sanitize and validate a dict of user inputs against a schema.

    schema = {
        'field_name': {
            'type': str | int | float | bool,
            'required': True | False,
            'max_length': int,        # str only
            'min_length': int,        # str only
            'max_value': number,      # numeric only
            'min_value': number,      # numeric only
            'pattern': regex_string,  # str only
            'choices': [list],        # allowed values
            'default': any,
        }
    }
    Returns sanitized dict.
    Raises ValueError with descriptive message on validation failure.
    """
    result = {}
    for field, rules in schema.items():
        raw = data.get(field)
        required = rules.get('required', False)
        default = rules.get('default', None)

        if raw is None or raw == '':
            if required:
                raise ValueError(f"'{field}' is required")
            result[field] = default
            continue

        expected_type = rules.get('type', str)

        # Type coercion / check
        try:
            if expected_type == int:
                value = int(raw)
            elif expected_type == float:
                value = float(raw)
            elif expected_type == bool:
                if isinstance(raw, bool):
                    value = raw
                else:
                    value = str(raw).lower() in ('true', '1', 'yes')
            else:
                value = str(raw)
        except (ValueError, TypeError):
            raise ValueError(f"'{field}' must be of type {expected_type.__name__}")

        # String-specific checks
        if expected_type == str:
            max_len = rules.get('max_length', 1000)
            min_len = rules.get('min_length', 0)
            if len(value) > max_len:
                raise ValueError(f"'{field}' is too long (max {max_len} characters)")
            if len(value) < min_len:
                raise ValueError(f"'{field}' is too short (min {min_len} characters)")
            pattern = rules.get('pattern')
            if pattern and not re.fullmatch(pattern, value):
                raise ValueError(f"'{field}' has an invalid format")
            value = html.escape(value.strip(), quote=True)

        # Numeric range checks
        if expected_type in (int, float):
            if 'min_value' in rules and value < rules['min_value']:
                raise ValueError(f"'{field}' must be >= {rules['min_value']}")
            if 'max_value' in rules and value > rules['max_value']:
                raise ValueError(f"'{field}' must be <= {rules['max_value']}")

        # Allowed choices
        choices = rules.get('choices')
        if choices is not None and value not in choices:
            raise ValueError(f"'{field}' must be one of: {choices}")

        result[field] = value

    return result


# ─────────────────────────────────────────────────────────
# Email / Password validators
# ─────────────────────────────────────────────────────────

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

def validate_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise ValueError("Invalid email address format")
    if len(email) > 120:
        raise ValueError("Email address is too long")
    return email


def validate_password(password: str) -> None:
    """Enforce minimum password strength."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(password) > 128:
        raise ValueError("Password is too long")
    if not re.search(r'[A-Za-z]', password):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r'[0-9]', password):
        raise ValueError("Password must contain at least one number")


# ─────────────────────────────────────────────────────────
# File Upload Validation
# ─────────────────────────────────────────────────────────

# Allowed MIME types → allowed extensions
ALLOWED_UPLOAD_TYPES = {
    'application/pdf':    'pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
    'text/plain':         'txt',
}

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'txt'}

# Magic bytes for each format
MAGIC_BYTES = {
    b'%PDF':                   'pdf',
    b'PK\x03\x04':             'docx_or_pptx',  # ZIP-based (docx, pptx)
}

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB hard limit


def validate_upload_file(file_storage) -> dict:
    """
    Validate a werkzeug FileStorage object.
    Checks:
      1. Filename present and non-empty
      2. Extension in allowlist
      3. File size ≤ MAX_UPLOAD_BYTES
      4. Magic bytes match declared extension

    Returns {'valid': True, 'ext': 'pdf'} or raises ValueError.
    """
    filename = file_storage.filename or ''
    if not filename:
        raise ValueError("No filename provided")

    # Extension check
    parts = filename.rsplit('.', 1)
    if len(parts) != 2 or parts[1].lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"File type not allowed. Accepted types: {', '.join(ALLOWED_EXTENSIONS).upper()}"
        )
    ext = parts[1].lower()

    # Read first 8 bytes for magic check, then seek back
    header = file_storage.read(8)
    file_storage.seek(0)

    # Validate magic bytes
    matched_magic = None
    for magic, ftype in MAGIC_BYTES.items():
        if header.startswith(magic):
            matched_magic = ftype
            break

    if matched_magic is None and ext != 'txt':
        raise ValueError("File content does not match its extension")

    if ext in ('docx', 'pptx') and matched_magic != 'docx_or_pptx':
        raise ValueError("File content does not match its extension")

    if ext == 'pdf' and matched_magic != 'pdf':
        raise ValueError("File content does not match its extension")

    # Size check — read entire file into memory to count bytes
    file_storage.seek(0, 2)  # seek to end
    size = file_storage.tell()
    file_storage.seek(0)

    if size == 0:
        raise ValueError("Uploaded file is empty")
    if size > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"File too large. Maximum allowed size is {MAX_UPLOAD_BYTES // (1024*1024)} MB"
        )

    return {'valid': True, 'ext': ext, 'size': size}


# ─────────────────────────────────────────────────────────
# CSRF — Double-Submit Cookie pattern
# ─────────────────────────────────────────────────────────
# Since the app uses JWT Bearer tokens (not session cookies), full CSRF
# is not required for the API. However, we implement a CSRF token endpoint
# and validation decorator to protect any future form-based or cookie-based flows.

CSRF_TOKEN_LENGTH = 32


def generate_csrf_token() -> str:
    return secrets.token_hex(CSRF_TOKEN_LENGTH)


def verify_csrf_token(cookie_token: str, header_token: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    if not cookie_token or not header_token:
        return False
    return hmac.compare_digest(cookie_token, header_token)


def csrf_protect(fn):
    """
    Decorator: verify CSRF double-submit cookie for non-GET/HEAD requests.
    Skips validation if the request carries a valid JWT Bearer token
    (API clients — already CSRF-safe by nature of Bearer auth).
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Bearer token requests are inherently CSRF-safe
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return fn(*args, **kwargs)

        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return fn(*args, **kwargs)

        cookie_token = request.cookies.get('csrf_token', '')
        header_token = request.headers.get('X-CSRF-Token', '')

        if not verify_csrf_token(cookie_token, header_token):
            return jsonify({'error': 'CSRF validation failed'}), 403
        return fn(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────
# Rate Limiting (in-memory, per-IP)
# ─────────────────────────────────────────────────────────

_rate_store: dict = defaultdict(list)  # ip -> [timestamps]


def rate_limit(max_requests: int, window_seconds: int):
    """
    Decorator factory: allow max_requests per window_seconds per IP.
    Usage: @rate_limit(5, 60)  → 5 requests per minute
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ip = request.remote_addr or '0.0.0.0'
            key = f"{fn.__name__}:{ip}"
            now = time.time()
            window_start = now - window_seconds

            # Purge old entries
            _rate_store[key] = [t for t in _rate_store[key] if t > window_start]

            if len(_rate_store[key]) >= max_requests:
                return jsonify({
                    'error': 'Too many requests. Please try again later.'
                }), 429

            _rate_store[key].append(now)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
