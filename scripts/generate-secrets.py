#!/usr/bin/env python3
"""Generate secure random values for .env configuration"""
import secrets
import string

def generate_secret(length=32):
    """Generate a secure random hex string"""
    return secrets.token_hex(length)

def generate_password(length=24):
    """Generate a strong random password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(chars) for _ in range(length))

if __name__ == '__main__':
    print("# Open-Monitor v3.0 - Generated Secrets")
    print(f"SECRET_KEY={generate_secret(32)}")
    print(f"POSTGRES_PASSWORD={generate_password(24)}")
    print(f"REDIS_PASSWORD={generate_password(16)}")
    print("# Copy these values to your .env file")