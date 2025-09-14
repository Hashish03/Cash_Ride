from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from security.logging import SecurityLog
import csv
import os

class Command(BaseCommand):
    help = 'Generate security report'
    
    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Number of days to include in report')
        parser.add_argument('--output', type=str, default='security_report.csv', help='Output file name')
    
    def handle(self, *args, **options):
        days = options['days']
        output_file = options['output']
        
        # Get security logs from the last N days
        start_date = timezone.now() - timedelta(days=days)
        
        logs = SecurityLog.objects.filter(
            timestamp__gte=start_date
        ).order_by('-timestamp')
        
        # Generate CSV report
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = [
                'timestamp', 'event_type', 'user_id', 'ip_address',
                'description', 'severity'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for log in logs:
                writer.writerow({
                    'timestamp': log.timestamp.isoformat(),
                    'event_type': log.event_type,
                    'user_id': log.user_id,
                    'ip_address': log.ip_address,
                    'description': log.description,
                    'severity': log.severity,
                })
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Security report generated: {output_file} ({logs.count()} records)'
            )
        )