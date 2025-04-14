import csv
import pathlib

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy
from django.utils import timezone
from django.db.models import F, IntegerField, Subquery, OuterRef

from tally_ho.apps.tally.models.reconciliation_form import ReconciliationForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState

def generate_csv():
    tally_id = 1
    station_id_query =\
        Subquery(
            Station.objects.filter(
                tally__id=tally_id,
                center__code=OuterRef(
                    'result_form__center__code'),
                station_number=OuterRef(
                    'result_form__station_number'))
            .values('id')[:1],
            output_field=IntegerField())
    station_registrants_query =\
        Subquery(
            Station.objects.filter(
                tally__id=tally_id,
                id=OuterRef(('station_id_num')))
            .values('registrants')[:1],
            output_field=IntegerField())
    recon_forms =\
        ReconciliationForm.objects.filter(
            result_form__tally__id=tally_id,
            result_form__form_state=FormState.ARCHIVED,
            entry_version=EntryVersion.FINAL,
            active=True
        ).annotate(
            barcode=F('result_form__barcode'),
            station_id_num=station_id_query
        ).values('barcode').annotate(
            ballots_inside=F('number_ballots_inside_box'),
            station_registrants=station_registrants_query,
            station_id=F('station_id_num'),
            station_number=F('result_form__station_number'),
            center_code=F('result_form__center__code'),
            sub_race_name=F('result_form__center__sub_constituency__name'),
            sub_race_code=F('result_form__center__sub_constituency__code')
        )
    forms =\
        [
            recon_form for recon_form in recon_forms\
                if recon_form.get(
                    'ballots_inside') > recon_form.get('station_registrants')
        ]

    # Generate CSV file path with timestamp
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'overvote_forms_{timestamp}.csv'
    csv_filepath = pathlib.Path(csv_filename)

    # Define the CSV column headers
    headers = [
        'barcode',
        'center_code',
        'station_number',
        'ballots_inside',
        'station_registrants',
        'sub_race_name',
        'sub_race_code',
    ]

    with open(csv_filepath, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for form in forms:
            barcode = form.get('barcode'),
            center_code = form.get('center_code'),
            station_number = form.get('station_number'),
            ballots_inside = form.get('ballots_inside'),
            station_registrants = form.get('station_registrants'),
            sub_race_name = form.get('sub_race_name'),
            sub_race_code = form.get('sub_race_code'),

            # Write the data row
            writer.writerow([
                    barcode[0],
                    center_code[0],
                    station_number[0],
                    ballots_inside[0],
                    station_registrants[0],
                    sub_race_name[0],
                    sub_race_code[0],
                ])

    print(f"CSV files has been created: {csv_filepath}")


class Command(BaseCommand):
    help = gettext_lazy("create csv file with overvotes.")

    def handle(self, *args, **kwargs):
        self.get_overvoted_result_forms_csv()

    def get_overvoted_result_forms_csv(self):
        generate_csv()
