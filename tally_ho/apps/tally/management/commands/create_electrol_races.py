from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.translation import ugettext_lazy

from tally_ho.apps.tally.models.electrol_race import ElectrolRace


def create_electrol_races(command, electrol_races):
    """Create electrol races.

    :param command: stdout command.
    :param electrol_races: Dictonary array of electrol races.

    :returns: A queryset of electrol races created.
    """
    try:
        objs = [
        ElectrolRace(
            type=electrol_race['type'],
            code=electrol_race['code'],
            ballot_name=electrol_race['ballot_name'],
        )
        for electrol_race in electrol_races
        ]
        qs = ElectrolRace.objects.bulk_create(objs=objs)
        return qs
    except Exception as e:
        command.stdout.write(command.style.ERROR(
            "Failed to create electrol races, error: {error}".format(error=e)))



class Command(BaseCommand):
    help = ugettext_lazy("Create electrol races.")

    def handle(self, *args, **kwargs):
        create_electrol_races(self, getattr(settings, 'ELECTROL_RACES'))
