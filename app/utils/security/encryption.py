"""
SOC360 Encryption Service
Encryption for sensitive data at rest.
"""
import os
import base64
import hashlib
import secrets
from typing import Optional, Tuple, Union
from datetime import datetime, timezone
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import Flask, current_app


class EncryptionService:
    """
    Serviço de criptografia para dados sensíveis.
    
    Suporta:
    - Fernet symmetric encryption (com rotação de chaves)
    - AES-256-GCM para campos específicos
    - Key derivation (PBKDF2)
    - Secure token generation
    """
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self._fernet: Optional[MultiFernet] = None
        self._aesgcm: Optional[AESGCM] = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize with Flask app."""
        self.app = app
        
        # Get encryption keys from config
        primary_key = app.config.get('ENCRYPTION_KEY')
        rotation_keys = app.config.get('ENCRYPTION_ROTATION_KEYS', [])
        
        if not primary_key:
            app.logger.warning(
                'ENCRYPTION_KEY not set. Generating ephemeral key. '
                'This will break encrypted data between restarts!'
            )
            primary_key = Fernet.generate_key().decode()
        
        # Initialize Fernet with key rotation support
        self._init_fernet(primary_key, rotation_keys)
        
        # Initialize AES-GCM for specific use cases
        aes_key = app.config.get('AES_KEY')
        if aes_key:
            self._init_aesgcm(aes_key)
    
    def _init_fernet(self, primary_key: str, rotation_keys: list) -> None:
        """Initialize Fernet encryption with key rotation."""
        try:
            # Validate and convert keys
            keys = [self._ensure_fernet_key(primary_key)]
            
            for key in rotation_keys:
                keys.append(self._ensure_fernet_key(key))
            
            # MultiFernet allows decryption with old keys but encrypts with newest
            fernets = [Fernet(k) for k in keys]
            self._fernet = MultiFernet(fernets)
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f'Failed to initialize Fernet: {e}')
            raise
    
    def _init_aesgcm(self, key: str) -> None:
        """Initialize AES-GCM encryption."""
        try:
            # Derive 256-bit key from provided key
            key_bytes = self._derive_key(key.encode(), b'openmonitor-aesgcm', 32)
            self._aesgcm = AESGCM(key_bytes)
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f'Failed to initialize AES-GCM: {e}')
    
    def _ensure_fernet_key(self, key: str) -> bytes:
        """
        Ensure key is valid Fernet key format.
        
        Args:
            key: Key string (may be URL-safe base64 or raw)
            
        Returns:
            Valid Fernet key bytes
        """
        try:
            # Try to use as-is (already valid Fernet key)
            key_bytes = key.encode() if isinstance(key, str) else key
            Fernet(key_bytes)  # Validate
            return key_bytes
        except Exception:
            pass
        
        # Derive Fernet key from provided key
        derived = self._derive_key(
            key.encode() if isinstance(key, str) else key,
            b'openmonitor-fernet',
            32  # Fernet uses 32 bytes
        )
        
        return base64.urlsafe_b64encode(derived)
    
    def _derive_key(
        self,
        password: bytes,
        salt: bytes,
        length: int = 32,
        iterations: int = 480000
    ) -> bytes:
        """
        Derive key using PBKDF2-HMAC-SHA256.
        
        Args:
            password: Input password/key
            salt: Salt for derivation
            length: Output key length
            iterations: PBKDF2 iterations
            
        Returns:
            Derived key bytes
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            iterations=iterations,
        )
        
        return kdf.derive(password)
    
    # =========================================================================
    # Fernet Encryption (General Purpose)
    # =========================================================================
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """
        Encrypt data using Fernet.
        
        Args:
            data: Data to encrypt
            
        Returns:
            Base64-encoded encrypted data
        """
        if self._fernet is None:
            raise RuntimeError('Encryption service not initialized')
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted = self._fernet.encrypt(data)
        return encrypted.decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt Fernet-encrypted data.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            
        Returns:
            Decrypted string
            
        Raises:
            InvalidToken: If decryption fails
        """
        if self._fernet is None:
            raise RuntimeError('Encryption service not initialized')
        
        try:
            decrypted = self._fernet.decrypt(encrypted_data.encode('utf-8'))
            return decrypted.decode('utf-8')
        except InvalidToken:
            if self.app:
                self.app.logger.error('Failed to decrypt data: invalid token')
            raise
    
    def rotate_key(self, encrypted_data: str) -> str:
        """
        Re-encrypt data with the current primary key.
        
        Use this during key rotation to update encrypted values.
        
        Args:
            encrypted_data: Data encrypted with old key
            
        Returns:
            Data re-encrypted with primary key
        """
        if self._fernet is None:
            raise RuntimeError('Encryption service not initialized')
        
        rotated = self._fernet.rotate(encrypted_data.encode('utf-8'))
        return rotated.decode('utf-8')
    
    # =========================================================================
    # AES-GCM Encryption (High Security)
    # =========================================================================
    
    def encrypt_aes(self, data: Union[str, bytes], aad: Optional[bytes] = None) -> str:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            data: Data to encrypt
            aad: Additional authenticated data
            
        Returns:
            Base64-encoded nonce + ciphertext
        """
        if self._aesgcm is None:
            raise RuntimeError('AES-GCM not initialized. Set AES_KEY in config.')
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Generate random 96-bit nonce
        nonce = os.urandom(12)
        
        # Encrypt
        ciphertext = self._aesgcm.encrypt(nonce, data, aad)
        
        # Return nonce + ciphertext
        return base64.urlsafe_b64encode(nonce + ciphertext).decode('utf-8')
    
    def decrypt_aes(self, encrypted_data: str, aad: Optional[bytes] = None) -> str:
        """
        Decrypt AES-256-GCM encrypted data.
        
        Args:
            encrypted_data: Base64-encoded nonce + ciphertext
            aad: Additional authenticated data (must match encryption)
            
        Returns:
            Decrypted string
        """
        if self._aesgcm is None:
            raise RuntimeError('AES-GCM not initialized. Set AES_KEY in config.')
        
        try:
            raw = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            
            # Extract nonce (first 12 bytes)
            nonce = raw[:12]
            ciphertext = raw[12:]
            
            # Decrypt
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, aad)
            return plaintext.decode('utf-8')
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f'AES-GCM decryption failed: {e}')
            raise
    
    # =========================================================================
    # Token Generation
    # =========================================================================
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        Generate cryptographically secure token.
        
        Args:
            length: Token length in bytes
            
        Returns:
            URL-safe base64-encoded token
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate API key (48 bytes = 64 chars base64)."""
        return secrets.token_urlsafe(48)
    
    @staticmethod
    def generate_session_id() -> str:
        """Generate session ID (32 bytes)."""
        return secrets.token_hex(32)
    
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """
        Generate numeric OTP.
        
        Args:
            length: Number of digits
            
        Returns:
            Numeric OTP string
        """
        return ''.join(str(secrets.randbelow(10)) for _ in range(length))
    
    # =========================================================================
    # Hashing
    # =========================================================================
    
    @staticmethod
    def hash_data(data: Union[str, bytes], algorithm: str = 'sha256') -> str:
        """
        Create hash of data.
        
        Args:
            data: Data to hash
            algorithm: Hash algorithm (sha256, sha384, sha512)
            
        Returns:
            Hex-encoded hash
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if algorithm == 'sha256':
            h = hashlib.sha256(data)
        elif algorithm == 'sha384':
            h = hashlib.sha384(data)
        elif algorithm == 'sha512':
            h = hashlib.sha512(data)
        else:
            raise ValueError(f'Unsupported algorithm: {algorithm}')
        
        return h.hexdigest()
    
    @staticmethod
    def hash_with_salt(data: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash data with salt.
        
        Args:
            data: Data to hash
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (hash, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        salted = (salt + data).encode('utf-8')
        hash_value = hashlib.sha256(salted).hexdigest()
        
        return hash_value, salt
    
    @staticmethod
    def verify_hash(data: str, expected_hash: str, salt: str) -> bool:
        """
        Verify hash with salt.
        
        Args:
            data: Original data
            expected_hash: Expected hash value
            salt: Salt used for hashing
            
        Returns:
            True if hash matches
        """
        computed_hash, _ = EncryptionService.hash_with_salt(data, salt)
        return secrets.compare_digest(computed_hash, expected_hash)


class EncryptedField:
    """
    Descriptor for encrypted model fields.
    
    Usage:
        class User(db.Model):
            _api_token = db.Column('api_token', db.Text)
            api_token = EncryptedField('_api_token')
    """
    
    def __init__(self, field_name: str, use_aes: bool = False):
        """
        Args:
            field_name: Name of the actual database field
            use_aes: Use AES-GCM instead of Fernet
        """
        self.field_name = field_name
        self.use_aes = use_aes
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        
        encrypted_value = getattr(obj, self.field_name)
        
        if encrypted_value is None:
            return None
        
        try:
            service = current_app.extensions.get('encryption')
            if service is None:
                raise RuntimeError('Encryption extension not initialized')
            
            if self.use_aes:
                return service.decrypt_aes(encrypted_value)
            return service.decrypt(encrypted_value)
            
        except Exception:
            current_app.logger.error(
                f'Failed to decrypt field {self.field_name}'
            )
            return None
    
    def __set__(self, obj, value):
        if value is None:
            setattr(obj, self.field_name, None)
            return
        
        try:
            service = current_app.extensions.get('encryption')
            if service is None:
                raise RuntimeError('Encryption extension not initialized')
            
            if self.use_aes:
                encrypted = service.encrypt_aes(value)
            else:
                encrypted = service.encrypt(value)
            
            setattr(obj, self.field_name, encrypted)
            
        except Exception:
            current_app.logger.error(
                f'Failed to encrypt field {self.field_name}'
            )
            raise


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        URL-safe base64-encoded key
    """
    return Fernet.generate_key().decode()


def generate_aes_key() -> str:
    """
    Generate a new AES-256 key.
    
    Returns:
        URL-safe base64-encoded key
    """
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


# Global instance
encryption_service = EncryptionService()
