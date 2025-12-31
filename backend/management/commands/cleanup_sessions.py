from django.core.management.base import BaseCommand
from django.utils import timezone
from authentication.sync_service import UserSyncService
from authentication.models import UserSession


class Command(BaseCommand):
    help = 'Clean up expired user sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete sessions older than this many days (default: 30)',
        )

    def handle(self, *args, **options):
        days = options['days']
        
        self.stdout.write(self.style.WARNING(f'Cleaning up sessions older than {days} days...'))
        
        # Clean up expired sessions
        expired_count = UserSyncService.cleanup_expired_sessions()
        self.stdout.write(self.style.SUCCESS(f'✓ Deactivated {expired_count} expired sessions'))
        
        # Delete old inactive sessions
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        old_sessions = UserSession.objects.filter(
            is_active=False,
            created_at__lt=cutoff_date
        )
        
        count = old_sessions.count()
        old_sessions.delete()
        
        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} old inactive sessions'))
        self.stdout.write(self.style.SUCCESS('Session cleanup completed!'))