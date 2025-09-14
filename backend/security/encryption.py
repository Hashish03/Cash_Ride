# backend/security/encryption.py
from django.db import models
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import os

class EncryptedField(models.CharField):
    """
    Custom field that encrypts data before storing in database
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cipher_suite = self._get_cipher_suite()
    
    def _get_cipher_suite(self):
        """Get or create encryption key"""
        key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
        if not key:
            # Generate a key if not provided
            key = Fernet.generate_key()
            print(f"Generated encryption key: {key.decode()}")
        else:
            key = key.encode() if isinstance(key, str) else key
        
        return Fernet(key)
    
    def from_db_value(self, value, expression, connection):
        """Decrypt when reading from database"""
        if value is None:
            return value
        
        try:
            # Decrypt the value
            decrypted = self.cipher_suite.decrypt(value.encode())
            return decrypted.decode()
        except Exception:
            # If decryption fails, return the original value
            # This handles cases where data might not be encrypted yet
            return value
    
    def to_python(self, value):
        """Convert to Python value"""
        if isinstance(value, str) or value is None:
            return value
        return str(value)
    
    def get_prep_value(self, value):
        """Encrypt before saving to database"""
        if value is None:
            return value
        
        try:
            # Encrypt the value
            encrypted = self.cipher_suite.encrypt(str(value).encode())
            return encrypted.decode()
        except Exception as e:
            # If encryption fails, log and return original
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Encryption error: {str(e)}")
            return value
