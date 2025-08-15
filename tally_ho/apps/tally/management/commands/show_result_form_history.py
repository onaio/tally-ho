import csv
import pathlib
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext
from reversion.models import Version
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.utils.time import format_duration_human_readable


class Command(BaseCommand):
    help = "Show complete history of a result form by barcode"

    def add_arguments(self, parser):
        parser.add_argument(
            'barcode',
            type=str,
            help='Barcode of the result form to show history for'
        )
        parser.add_argument(
            '--tally-id',
            type=int,
            default=None,
            help='Tally ID to filter by (optional)'
        )
        parser.add_argument(
            '--export-csv',
            action='store_true',
            help='Export history to CSV file'
        )

    def handle(self, *args, **options):
        barcode = options['barcode']
        tally_id = options['tally_id']
        export_csv = options['export_csv']

        try:
            # Find the result form
            if tally_id:
                result_form = ResultForm.objects.get(
                    barcode=barcode, 
                    tally__id=tally_id
                )
            else:
                result_forms = ResultForm.objects.filter(barcode=barcode)
                if result_forms.count() > 1:
                    raise CommandError(
                        f'Multiple result forms found with barcode "{barcode}".\n'
                        f'Please specify --tally-id. Found in tallies:\n' +
                        '\n'.join([f'  - Tally {rf.tally.id}: {rf.tally.name}' 
                                  for rf in result_forms])
                    )
                elif result_forms.count() == 0:
                    raise CommandError(
                        f'Result form with barcode "{barcode}" does not exist'
                    )
                else:
                    result_form = result_forms.first()
        except ResultForm.DoesNotExist:
            raise CommandError(
                f'Result form with barcode "{barcode}" does not exist'
            )

        # Get version history
        versions = Version.objects.get_for_object(result_form).order_by('pk')

        if not versions:
            self.stdout.write(
                self.style.WARNING(
                    f'No version history found for result form {barcode}'
                )
            )
            return

        # Display basic form info
        self.stdout.write(
            self.style.SUCCESS(f'\nResult Form History: {barcode}')
        )
        self.stdout.write(f'Center: {result_form.center}')
        self.stdout.write(f'Station: {result_form.station_number}')
        self.stdout.write(f'Ballot: {result_form.ballot}')
        if result_form.tally:
            self.stdout.write(f'Tally: {result_form.tally.name}')
        self.stdout.write(f'Current State: {result_form.form_state.name}\n')

        # Prepare history data (same logic as the view)
        history_data = []
        previous_timestamp = None
        
        for version in versions:
            version_data = version.field_dict
            
            # Get user info
            user_name = "Unknown"
            if 'user_id' in version_data and version_data['user_id']:
                try:
                    user = User.objects.get(pk=version_data['user_id'])
                    user_name = user.username
                except User.DoesNotExist:
                    user_name = f"User ID {version_data['user_id']}"

            # Format timestamp
            modified_date = version_data.get('modified_date')
            timestamp = None
            if modified_date:
                if isinstance(modified_date, str):
                    from django.utils.dateparse import parse_datetime
                    timestamp = parse_datetime(modified_date)
                else:
                    timestamp = modified_date
            
            # Get form states
            current_state = version_data.get('form_state')
            previous_state = version_data.get('previous_form_state')
            
            if current_state:
                current_state_name = FormState(current_state).name
            else:
                current_state_name = "Unknown"

            if previous_state:
                previous_state_name = FormState(previous_state).name
            else:
                previous_state_name = "None"

            # Calculate duration in previous state
            duration_display = None
            if previous_timestamp and timestamp:
                duration = timestamp - previous_timestamp
                duration_display = format_duration_human_readable(duration)

            history_data.append({
                'user': user_name,
                'timestamp': timestamp,
                'current_state': current_state_name,
                'previous_state': previous_state_name,
                'duration_display': duration_display,
                'is_current': False
            })
            
            previous_timestamp = timestamp

        # Reverse to show newest first, then mark first entry as current
        history_data.reverse()
        if history_data:
            history_data[0]['is_current'] = True

        # Display history
        self.stdout.write("History (newest to oldest):")
        self.stdout.write("-" * 110)
        self.stdout.write(
            f"{'User':<20} {'Timestamp':<25} {'Previous State':<15} "
            f"{'Current State':<15} {'Duration':<15} {'Status':<10}"
        )
        self.stdout.write("-" * 110)

        for entry in history_data:
            # Format timestamp for display
            if entry['timestamp']:
                timestamp_str = entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp_str = "Unknown"
            
            # Format duration
            duration_str = entry['duration_display'] if entry['duration_display'] else "-"
            
            # Current status indicator
            status_str = "(current)" if entry['is_current'] else ""
            
            self.stdout.write(
                f"{entry['user']:<20} {timestamp_str:<25} "
                f"{entry['previous_state']:<15} {entry['current_state']:<15} "
                f"{duration_str:<15} {status_str:<10}"
            )

        # Export to CSV if requested
        if export_csv:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = f'result_form_history_{barcode}_{timestamp}.csv'
            csv_filepath = pathlib.Path(csv_filename)

            with open(csv_filepath, mode='w', newline='') as file:
                fieldnames = [
                    'barcode', 'user', 'timestamp', 'previous_state', 
                    'current_state', 'duration_in_previous', 'is_current'
                ]
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()

                for entry in history_data:
                    writer.writerow({
                        'barcode': barcode,
                        'user': entry['user'],
                        'timestamp': entry['timestamp'].isoformat() if entry['timestamp'] else '',
                        'previous_state': entry['previous_state'],
                        'current_state': entry['current_state'],
                        'duration_in_previous': entry['duration_display'] if entry['duration_display'] else '',
                        'is_current': 'Yes' if entry['is_current'] else 'No',
                    })

            self.stdout.write(
                self.style.SUCCESS(f'\nHistory exported to: {csv_filepath}')
            )

        self.stdout.write(f'\nTotal history entries: {len(history_data)}')