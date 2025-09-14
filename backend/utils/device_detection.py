# backend/utils/device_detection.py
import re
from user_agents import parse

class DeviceDetector:
    """
    Device detection utility for security and analytics
    """
    
    def __init__(self, user_agent_string):
        self.user_agent_string = user_agent_string
        self.user_agent = parse(user_agent_string)
    
    def get_device_info(self):
        """Get comprehensive device information"""
        return {
            'browser': {
                'family': self.user_agent.browser.family,
                'version': self.user_agent.browser.version_string,
            },
            'os': {
                'family': self.user_agent.os.family,
                'version': self.user_agent.os.version_string,
            },
            'device': {
                'family': self.user_agent.device.family,
                'brand': self.user_agent.device.brand,
                'model': self.user_agent.device.model,
            },
            'is_mobile': self.user_agent.is_mobile,
            'is_tablet': self.user_agent.is_tablet,
            'is_desktop': not (self.user_agent.is_mobile or self.user_agent.is_tablet),
            'is_bot': self.user_agent.is_bot,
        }
    
    def is_suspicious_device(self):
        """Check if device shows suspicious characteristics"""
        # Check for bot
        if self.user_agent.is_bot:
            return True
        
        # Check for suspicious user agent patterns
        suspicious_patterns = [
            r'curl',
            r'wget',
            r'python',
            r'script',
            r'bot',
            r'spider',
            r'crawl',
        ]
        
        ua_lower = self.user_agent_string.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, ua_lower):
                return True
        
        return False
    
    def get_risk_score(self):
        """Calculate device risk score (0-100)"""
        score = 0
        
        # Bot detection
        if self.user_agent.is_bot:
            score += 50
        
        # Suspicious patterns
        if self.is_suspicious_device():
            score += 30
        
        # Unknown or very old browsers
        if self.user_agent.browser.family == 'Other':
            score += 20
        
        # Very old OS versions (security risk)
        if self.user_agent.os.family in ['Windows', 'Mac OS X']:
            try:
                version = float(self.user_agent.os.version_string.split('.')[0])
                if self.user_agent.os.family == 'Windows' and version < 10:
                    score += 15
                elif self.user_agent.os.family == 'Mac OS X' and version < 10:
                    score += 15
            except (ValueError, IndexError):
                score += 10
        
        return min(score, 100)
