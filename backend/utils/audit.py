"""
utils/audit.py
──────────────
Structured audit logging for KarmayogAI.
Writes JSON-formatted records to logs/audit.log.

Events logged:
  - AUTH: login, logout, register, failed_login, password_change
  - DATA: assessment_submit, course_enroll, progress_update, profile_update
  - FILE: upload, upload_rejected
  - ADMIN: add_course, list_users
  - SECURITY: csrf_failure, rate_limit_hit, invalid_input, unauthorized_access
"""

import logging
import json
import os
from datetime import datetime, timezone
from flask import request, has_request_context

# ── Setup log directory & file ────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'audit.log')

_audit_logger = logging.getLogger('karmayogai.audit')
_audit_logger.setLevel(logging.INFO)
_audit_logger.propagate = False  # don't pollute root logger

if not _audit_logger.handlers:
    _handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    _handler.setFormatter(logging.Formatter('%(message)s'))
    _audit_logger.addHandler(_handler)


# ── Core emit function ────────────────────────────────────

def log_event(
    event_type: str,
    action: str,
    user_id: int | None = None,
    details: dict | None = None,
    success: bool = True,
    severity: str = 'INFO',   # INFO | WARN | ERROR
):
    """
    Emit a single structured audit log entry.

    Args:
        event_type: Category (AUTH / DATA / FILE / ADMIN / SECURITY)
        action:     Specific action name, e.g. 'login', 'upload'
        user_id:    Authenticated user id, or None for anonymous
        details:    Arbitrary dict with extra context
        success:    Whether the action succeeded
        severity:   Log severity label
    """
    ip = None
    path = None
    method = None
    user_agent = None

    if has_request_context():
        ip = request.remote_addr
        path = request.path
        method = request.method
        user_agent = request.headers.get('User-Agent', '')[:200]

    record = {
        'ts':         datetime.now(timezone.utc).isoformat(),
        'severity':   severity,
        'event_type': event_type,
        'action':     action,
        'success':    success,
        'user_id':    user_id,
        'ip':         ip,
        'method':     method,
        'path':       path,
        'user_agent': user_agent,
        'details':    details or {},
    }
    _audit_logger.info(json.dumps(record))


# ── Convenience wrappers ──────────────────────────────────

def log_auth(action: str, user_id=None, details=None, success=True):
    severity = 'INFO' if success else 'WARN'
    log_event('AUTH', action, user_id=user_id, details=details,
              success=success, severity=severity)


def log_data(action: str, user_id=None, details=None, success=True):
    log_event('DATA', action, user_id=user_id, details=details,
              success=success, severity='INFO')


def log_file(action: str, user_id=None, details=None, success=True):
    severity = 'INFO' if success else 'WARN'
    log_event('FILE', action, user_id=user_id, details=details,
              success=success, severity=severity)


def log_admin(action: str, user_id=None, details=None, success=True):
    log_event('ADMIN', action, user_id=user_id, details=details,
              success=success, severity='INFO')


def log_security(action: str, user_id=None, details=None):
    log_event('SECURITY', action, user_id=user_id, details=details,
              success=False, severity='ERROR')
