"""Security utilities for encryption."""
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.config import settings


def _get_fernet() -> Fernet:
    """Get Fernet instance from secret key."""
    # Derive a key from the secret
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"seedarr_salt_v1",  # Fixed salt for consistency
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.secret_key.encode()))
    return Fernet(key)


def encrypt_password(password: str) -> str:
    """Encrypt a password."""
    if not password:
        return ""
    fernet = _get_fernet()
    return fernet.encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    """Decrypt a password."""
    if not encrypted:
        return ""
    try:
        fernet = _get_fernet()
        return fernet.decrypt(encrypted.encode()).decode()
    except Exception:
        # Return as-is if decryption fails (might not be encrypted)
        return encrypted
