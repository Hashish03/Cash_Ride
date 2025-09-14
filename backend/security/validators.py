# backend/security/validators.py
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class PasswordValidator:
    """
    Custom password validator for enhanced security
    """
    
    def validate(self, password, user=None):
        """Validate password strength"""
        errors = []
        
        # Minimum length
        if len(password) < 8:
            errors.append(_('Password must be at least 8 characters long.'))
        
        # Maximum length
        if len(password) > 128:
            errors.append(_('Password must be no more than 128 characters long.'))
        
        # Check for uppercase letter
        if not re.search(r'[A-Z]', password):
            errors.append(_('Password must contain at least one uppercase letter.'))
        
        # Check for lowercase letter
        if not re.search(r'[a-z]', password):
            errors.append(_('Password must contain at least one lowercase letter.'))
        
        # Check for digit
        if not re.search(r'\d', password):
            errors.append(_('Password must contain at least one digit.'))
        
        # Check for special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append(_('Password must contain at least one special character.'))
        
        # Check for common patterns
        if self._has_common_patterns(password):
            errors.append(_('Password contains common patterns and is not secure.'))
        
        # Check against user information
        if user:
            if self._password_similar_to_user_info(password, user):
                errors.append(_('Password is too similar to your personal information.'))
        
        if errors:
            raise ValidationError(errors)
    
    def _has_common_patterns(self, password):
        """Check for common password patterns"""
        common_patterns = [
            r'123456',
            r'password',
            r'qwerty',
            r'abc123',
            r'111111',
            r'000000',
        ]
        
        password_lower = password.lower()
        for pattern in common_patterns:
            if pattern in password_lower:
                return True
        
        return False
    
    def _password_similar_to_user_info(self, password, user):
        """Check if password is similar to user information"""
        password_lower = password.lower()
        
        # Check against email
        if user.email:
            email_parts = user.email.lower().split('@')[0]
            if email_parts in password_lower or password_lower in email_parts:
                return True
        
        # Check against name
        if user.full_name:
            name_parts = user.full_name.lower().split()
            for part in name_parts:
                if len(part) > 2 and (part in password_lower or password_lower in part):
                    return True
        
        return False
    
    def get_help_text(self):
        return _(
            "Your password must contain at least 8 characters, including "
            "uppercase and lowercase letters, digits, and special characters."
        )

class PhoneNumberValidator:
    """
    Phone number validator with international format support
    """
    
    def __call__(self, value):
        """Validate phone number format"""
        if not value:
            return
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', value)
        
        # Check if it starts with + (international format)
        if not cleaned.startswith('+'):
            raise ValidationError(_('Phone number must be in international format (+1234567890).'))
        
        # Remove + for further validation
        digits_only = cleaned[1:]
        
        # Check length (international phone numbers are typically 7-15 digits)
        if len(digits_only) < 7 or len(digits_only) > 15:
            raise ValidationError(_('Phone number must be between 7 and 15 digits.'))
        
        # Check if all remaining characters are digits
        if not digits_only.isdigit():
            raise ValidationError(_('Phone number contains invalid characters.'))
