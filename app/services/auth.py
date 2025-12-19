import hashlib
import secrets

def generate_api_key() -> str:
    # Generate a secure, random URL-safe string (e.g., 32 bytes)
    return secrets.token_urlsafe(32)

def hash_api_key(api_key: str) -> str:
    # SHA-256 is fast and secure for high-entropy strings
    return hashlib.sha256(api_key.encode()).hexdigest()