import csv

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.models.enums.race_type import RaceType

from tally_ho.apps.tally.management.commands.import_data import get_component_race_type, invalid_line, \
                                                                empty_strings_to_none

SPECIAL_VOTING = 'Special Voting'


def import_sub_constituencies_and_ballots(tally, subconst_file):
    with subconst_file as f:
        reader = csv.reader(f)
        reader.next()  # ignore header

        for row in reader:
            if invalid_line(row):
                next

            row = empty_strings_to_none(row)

            try:
                code_value, field_office, races, ballot_number_general,\
                    ballot_number_women, number_of_ballots,\
                    ballot_number_component = row[:7]

                code_value = int(code_value)
                number_of_ballots = number_of_ballots and int(
                    number_of_ballots)

                ballot_component = None
                ballot_general = None
                ballot_women = None

                if ballot_number_component:
                    component_race_type = get_component_race_type(
                        ballot_number_component)

                    ballot_component, _ = Ballot.objects.get_or_create(
                        number=int(ballot_number_component),
                        race_type=component_race_type,
                        tally = tally)

                if ballot_number_general:
                    ballot_general, _ = Ballot.objects.get_or_create(
                        number=int(ballot_number_general),
                        race_type=RaceType.GENERAL,
                        tally = tally)

                if ballot_number_women:
                    ballot_women, _ = Ballot.objects.get_or_create(
                        number=int(ballot_number_women),
                        race_type=RaceType.WOMEN,
                        tally = tally)

                if number_of_ballots == 2 and not (
                        ballot_general and ballot_women):
                    raise Exception(
                        'Missing ballot data: expected 2 ballots, missing '
                        + ('general' if ballot_number_women else 'women'))

                _, created = SubConstituency.objects.get_or_create(
                    code=code_value,
                    field_office=field_office,
                    races=races,
                    ballot_component=ballot_component,
                    ballot_general=ballot_general,
                    ballot_women=ballot_women,
                    number_of_ballots=number_of_ballots,
                    tally = tally)

            except ValueError:
                pass
