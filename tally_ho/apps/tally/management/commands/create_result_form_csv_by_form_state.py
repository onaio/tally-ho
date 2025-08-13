import csv
import pathlib

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.translation import gettext_lazy

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState


def generate_csv():
    # Retrieve the form state using the provided enum number
    form_state = FormState.QUALITY_CONTROL

    # Filter result forms by form state
    result_forms = ResultForm.objects.filter(
        form_state=form_state, tally__id=1)

    # Generate CSV file path with timestamp
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'result_forms_{form_state.name}_{timestamp}.csv'
    csv_filepath = pathlib.Path(csv_filename)

    # Define the CSV column headers
    headers = [
        'barcode',
        'center',
        'station',
        'ballot',
        'race',
        'triggers',
        'user',
        'date',
        'audit',
        'sub_name',
    ]

    # Write the filtered result forms to the CSV file
    with open(csv_filepath, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for result_form in result_forms:
            barcode = result_form.barcode
            center = result_form.center.code,
            station = result_form.station_number
            ballot = result_form.ballot.number,
            race = result_form.ballot.electrol_race.ballot_name
            user = result_form.user.username
            modified_date = result_form.modified_date
            audit_resolution = ""
            triggers = ""
            sub_name = result_form.center.sub_constituency.name

            if (result_form.form_state == FormState.ARCHIVED) &\
                (result_form.qualitycontrol is not None):
                user = result_form.qualitycontrol.user.username
                modified_date =\
                    result_form.qualitycontrol.modified_date_formatted

            if (result_form.form_state == FormState.QUALITY_CONTROL) &\
                (result_form.qualitycontrol is not None):
                user = result_form.qualitycontrol.user.username
                modified_date =\
                    result_form.qualitycontrol.modified_date_formatted

            if (result_form.form_state == FormState.AUDIT) &\
                (result_form.has_recon is True) &\
                (result_form.audit is None):
                recon_qs = result_form.reconciliationform_set.filter(
                    active=True, entry_version=EntryVersion.FINAL
                )
                if len(recon_qs):
                    user = recon_qs[0].user.username

            if (result_form.form_state == FormState.AUDIT) &\
                (result_form.has_recon is True) &\
                (result_form.audit is not None):
                audit_resolution =\
                    result_form.audit.resolution_recommendation_name()
                quarantine_checks =\
                    [q.name for q in result_form.audit.quarantine_checks.all()]
                if len(quarantine_checks):
                    triggers = " , ".join(quarantine_checks)
                user = result_form.audit.user.username
                modified_date = result_form.audit.modified_date_formatted

            # Write the data row
            writer.writerow([
                    barcode,
                    center[0],
                    station,
                    ballot[0],
                    race,
                    triggers,
                    user,
                    modified_date,
                    audit_resolution,
                    sub_name,
                ])

    print(f"CSV file has been created: {csv_filepath}")


class Command(BaseCommand):
    help = gettext_lazy("create result_form csv by form_state.")

    def handle(self, *args, **kwargs):
        self.create_result_form_csv_by_form_state()

    def create_result_form_csv_by_form_state(self):
        # Generate CSV based on the form state enum number
        generate_csv()
