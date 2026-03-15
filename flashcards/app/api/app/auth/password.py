"""Argon2 password hashing."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

_hasher = PasswordHasher(time_cost=2, memory_cost=65536)


def hash_password(password: str) -> str:
    """Returns argon2 hash. Don't store plaintext."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Returns True if password matches hash. Only catches argon2 verify errors."""
    try:
        _hasher.verify(password_hash, password)
        return True
    except (VerifyMismatchError, VerificationError):
        return False
