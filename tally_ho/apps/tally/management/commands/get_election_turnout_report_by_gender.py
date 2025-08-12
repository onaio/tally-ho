import csv
import pathlib

from django.core.management.base import BaseCommand
from django.db.models import (
    Case,
    CharField,
    F,
    IntegerField,
    OuterRef,
    Subquery,
    Sum,
    When,
)
from django.db.models import Value as V
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext_lazy

from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState


def generate_csv():
    tally_id = 1
    station_gender_query =\
        Subquery(
            Station.objects.filter(
                tally__id=tally_id,
                center__code=OuterRef(
                    'center__code'),
                station_number=OuterRef(
                    'station_number'))
            .values('gender')[:1],
            output_field=IntegerField())
    station_registrants_query =\
        Subquery(
            Station.objects.filter(
                tally__id=tally_id,
                center__code=OuterRef(
                    'center__code'),
                station_number=OuterRef(
                    'station_number'))
            .values('registrants')[:1],
            output_field=IntegerField())

    turnout_data = ResultForm.objects.filter(
        tally__id=tally_id,
        form_state=FormState.ARCHIVED,
    ).annotate(
        station_gender_code=station_gender_query,
        station_registrants=station_registrants_query,
        station_gender=Case(
            When(station_gender_code=0,
                 then=V('Man')),
            default=V('Woman'),
            output_field=CharField()),
        municipality_name=F('center__sub_constituency__name'),
        municipality_code=F('center__sub_constituency__code'),
        sub_race_type=F('ballot__electrol_race__ballot_name')
    ).values(
        'municipality_name',
        'municipality_code',
        'station_gender_code',
        'station_gender',
        'sub_race_type'
    ).annotate(
        total_registrants=Sum('station_registrants')
    )

    # Generate CSV file path with timestamp
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'turnout_report_by_mun_by_race_by_gender_{timestamp}.csv'
    csv_filepath = pathlib.Path(csv_filename)

    # Define the CSV column headers
    headers = [
        'municipality_name',
        'municipality_code',
        'sub_race',
        'human',
        'voters',
        'registrants',
        'turnout',
    ]

    with open(csv_filepath, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for data in turnout_data:
            result_station_gender_query =\
                Subquery(
                    Station.objects.filter(
                        tally__id=tally_id,
                        center__code=OuterRef(
                            'result_form__center__code'),
                        station_number=OuterRef(
                            'result_form__station_number'))
                    .values('gender')[:1],
                    output_field=IntegerField())
            result_station_registrants_query =\
                Subquery(
                    Station.objects.filter(
                        tally__id=tally_id,
                        center__code=OuterRef(
                            'result_form__center__code'),
                        station_number=OuterRef(
                            'result_form__station_number'))
                    .values('registrants')[:1],
                    output_field=IntegerField())

            voters =\
                Result.objects.filter(
                    result_form__tally__id=tally_id,
                    result_form__center__sub_constituency__code=\
                        data.get('municipality_code'),
                    result_form__ballot__electrol_race__ballot_name=\
                        data.get('sub_race_type'),
                    result_form__form_state=FormState.ARCHIVED,
                    entry_version=EntryVersion.FINAL,
                    active=True,
            ).annotate(
                station_gender_code=result_station_gender_query,
                station_registrants=result_station_registrants_query,
            ).filter(
                station_gender_code=data.get('station_gender_code')
            ).aggregate(
                voters=Coalesce(Sum('votes'), 0)
            ).get('voters')

            municipality_name = data.get('municipality_name')
            municipality_code = data.get('municipality_code')
            sub_race = data.get('sub_race_type')
            human = data.get('station_gender')
            registrants = data.get('total_registrants')

            turnout = round(100 * voters / registrants, 2)
            # Write the data row
            writer.writerow([
                municipality_name,
                municipality_code,
                sub_race,
                human,
                voters,
                registrants,
                turnout,
                ])

    print(f"CSV files has been created: {csv_filepath}")


class Command(BaseCommand):
    help = gettext_lazy("get election turnout report by gender.")

    def handle(self, *args, **kwargs):
        self.get_election_turnout_report_by_gender()

    def get_election_turnout_report_by_gender(self):
        generate_csv()
