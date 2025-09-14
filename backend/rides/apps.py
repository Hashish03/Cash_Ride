from django.apps import AppConfig

class RidesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rides'
    
    def ready(self):
        # Import signals or tasks only if they exist
        try:
            from . import signals  # Only if you have signals.py
        except ImportError:
            pass