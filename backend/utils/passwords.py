"""
utils/passwords.py
──────────────────
Bcrypt password hashing for KarmayogAI.

Uses bcrypt with a cost factor of 12 (2^12 = 4096 iterations).
Cost 12 is a good balance: ~250ms on modern hardware — slow enough
to deter brute-force, fast enough for real users.

Also handles transparent migration: if a legacy Werkzeug hash is
detected it will verify correctly and re-hash with bcrypt on success.
"""

import bcrypt

BCRYPT_ROUNDS = 12

# Werkzeug hash prefixes — used to detect legacy hashes
_LEGACY_PREFIXES = ('scrypt:', 'pbkdf2:', 'sha256$', 'sha512$')


def hash_password(plain: str) -> str:
    """
    Hash a plaintext password with bcrypt.
    Returns a UTF-8 string suitable for storing in the DB.
    """
    if not plain:
        raise ValueError("Password must not be empty")
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plain.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, stored_hash: str) -> bool:
    """
    Verify a plaintext password against a stored hash.
    Supports both bcrypt hashes and legacy Werkzeug hashes
    (scrypt / pbkdf2) for backward compatibility during migration.
    Returns True if the password matches, False otherwise.
    Never raises — always returns bool.
    """
    if not plain or not stored_hash:
        return False

    try:
        # Legacy Werkzeug hash — fall back to werkzeug checker
        if any(stored_hash.startswith(p) for p in _LEGACY_PREFIXES):
            from werkzeug.security import check_password_hash
            return check_password_hash(stored_hash, plain)

        # bcrypt hash
        return bcrypt.checkpw(plain.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception:
        return False


def needs_rehash(stored_hash: str) -> bool:
    """
    Returns True if the stored hash is a legacy Werkzeug hash
    and should be re-hashed with bcrypt on next successful login.
    """
    return any(stored_hash.startswith(p) for p in _LEGACY_PREFIXES)
