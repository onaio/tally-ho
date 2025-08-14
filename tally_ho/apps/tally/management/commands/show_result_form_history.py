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
                result_form = ResultForm.objects.get(barcode=barcode)
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

        # Prepare history data
        history_data = []
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
            if modified_date:
                if isinstance(modified_date, str):
                    timestamp = modified_date
                else:
                    timestamp = modified_date.isoformat()
            else:
                timestamp = "Unknown"

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

            history_data.append({
                'user': user_name,
                'timestamp': timestamp,
                'current_state': current_state_name,
                'previous_state': previous_state_name,
                'version_id': version.pk
            })

        # Display history
        self.stdout.write("History (oldest to newest):")
        self.stdout.write("-" * 100)
        self.stdout.write(
            f"{'User':<20} {'Timestamp':<25} {'Previous State':<20} "
            f"{'Current State':<20} {'Version':<10}"
        )
        self.stdout.write("-" * 100)

        for entry in history_data:
            self.stdout.write(
                f"{entry['user']:<20} {entry['timestamp']:<25} "
                f"{entry['previous_state']:<20} {entry['current_state']:<20} "
                f"{entry['version_id']:<10}"
            )

        # Export to CSV if requested
        if export_csv:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = f'result_form_history_{barcode}_{timestamp}.csv'
            csv_filepath = pathlib.Path(csv_filename)

            with open(csv_filepath, mode='w', newline='') as file:
                fieldnames = [
                    'barcode', 'user', 'timestamp', 'previous_state', 
                    'current_state', 'version_id'
                ]
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()

                for entry in history_data:
                    writer.writerow({
                        'barcode': barcode,
                        'user': entry['user'],
                        'timestamp': entry['timestamp'],
                        'previous_state': entry['previous_state'],
                        'current_state': entry['current_state'],
                        'version_id': entry['version_id']
                    })

            self.stdout.write(
                self.style.SUCCESS(f'\nHistory exported to: {csv_filepath}')
            )

        self.stdout.write(f'\nTotal history entries: {len(history_data)}')