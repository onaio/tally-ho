from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import IntegrityError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from tally_ho.apps.tally.models.electrol_race import ElectrolRace


def create_electrol_races(command, electrol_races):
    """Create electrol races.

    :param command: stdout command.
    :param electrol_races: Dictonary array of electrol races.

    :returns: A queryset of electrol races created.
    """
    objs = [
            ElectrolRace(
                type=electrol_race.get('type'),
                code=electrol_race.get('code'),
                ballot_name=electrol_race.get('ballot_name'),
                component_ballot_numbers=\
                    electrol_race.get('component_ballot_numbers'),
            )
            for electrol_race in electrol_races
            ]
    try:
        return ElectrolRace.objects.bulk_create(objs=objs)
    except IntegrityError as e:
        # Do bulk update incase a duplicate key value error is thrown
        if 'duplicate key value violates unique constraint' in e.args[0]:
            with transaction.atomic():
                for obj in objs:
                    ElectrolRace.objects.filter(
                        type=obj.type,
                        code=obj.code).update(
                        ballot_name=obj.ballot_name,
                        component_ballot_numbers=obj.component_ballot_numbers)
        else:
            command.stdout.write(command.style.ERROR(
            "Failed to create electrol races, error: {error}".format(error=e)))
    except Exception as e:
        command.stdout.write(command.style.ERROR(
            "Failed to create electrol races, error: {error}".format(error=e)))



class Command(BaseCommand):
    help = _("Create electrol races.")

    def handle(self, *args, **kwargs):
        create_electrol_races(self, getattr(settings, 'ELECTROL_RACES'))
