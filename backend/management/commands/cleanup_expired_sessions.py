from django.core.management.base import BaseCommand
from django.utils import timezone
from authentication.models import UserSession

class Command(BaseCommand):
    help = 'Clean up expired user sessions'
    
    def handle(self, *args, **options):
        # Delete expired sessions
        expired_count = UserSession.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully deleted {expired_count} expired sessions'
            )
        )
