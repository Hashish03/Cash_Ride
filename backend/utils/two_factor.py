# backend/utils/two_factor.py
import pyotp
import qrcode
from io import BytesIO
import base64
from django.conf import settings

class TwoFactorService:
    """
    Two-factor authentication service using TOTP
    """
    
    def __init__(self):
        self.issuer_name = getattr(settings, 'TWO_FACTOR_ISSUER_NAME', 'Cash Ride')
    
    def generate_secret(self):
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    def get_totp_uri(self, user, secret):
        """Get TOTP URI for QR code generation"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user.email,
            issuer_name=self.issuer_name
        )
    
    def generate_qr_code(self, totp_uri):
        """Generate QR code for TOTP setup"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 string
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_token(self, secret, token):
        """Verify TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # Allow 1 window (30 seconds) tolerance
    
    def generate_backup_codes(self, count=10):
        """Generate backup codes for 2FA recovery"""
        import secrets
        import string
        
        codes = []
        for _ in range(count):
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            # Format as XXXX-XXXX
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
        
        return codes
