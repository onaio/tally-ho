import codecs
import csv

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.user_profile import UserProfile

STAFF_LIST_PATH = 'data/staff_list.csv'
USER_LIST_PATH = 'data/user_list.csv'

# Dict for all the variations on Clerk names.
STAFF_ROLE_DICT = {
    'AUDIT CLERK': groups.AUDIT_CLERK,
    'AUDIT SUPERVISOR': groups.AUDIT_SUPERVISOR,
    'CLEARANCE CLERK': groups.CLEARANCE_CLERK,
    'CLEARANCE SUPERVISOR': groups.CLEARANCE_SUPERVISOR,
    'CORRECTION': groups.CORRECTIONS_CLERK,
    'CORRECTION CLERK': groups.CORRECTIONS_CLERK,
    'CORRECTION SUPERVISOR': groups.CORRECTIONS_CLERK,
    'DATA ENTRY 1': groups.DATA_ENTRY_1_CLERK,
    'DATA ENTRY 1 CLERK': groups.DATA_ENTRY_1_CLERK,
    'DATA ENTRY 2': groups.DATA_ENTRY_2_CLERK,
    'DATA ENTRY 2 CLERK': groups.DATA_ENTRY_2_CLERK,
    'DATA ENTRY 1 SUPERVISOR': groups.DATA_ENTRY_1_CLERK,
    'DATA ENTRY 2 SUPERVISOR': groups.DATA_ENTRY_2_CLERK,
    'INTAKE CLERK': groups.INTAKE_CLERK,
    'INTAKE': groups.INTAKE_CLERK,
    'INTAKE SUPERVISOR': groups.INTAKE_SUPERVISOR,
    'QUALITY CONTROL CLERK': groups.QUALITY_CONTROL_CLERK,
    'QUALITY CONTROL SUPERVISOR': groups.QUALITY_CONTROL_SUPERVISOR,
    'DATABASE': groups.SUPER_ADMINISTRATOR,
    'PROGRAMMER': groups.SUPER_ADMINISTRATOR,
    'SUPER ADMINISTRATOR': groups.SUPER_ADMINISTRATOR,
    'TALLY MANAGER': groups.TALLY_MANAGER,
}

STAFF_ROLES = STAFF_ROLE_DICT.keys()


def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(unicode_csv_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield row


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')


def add_row(command, name, username, role, admin=None, tally_id=None):
    try:
        # Parse the name into first and last name
        first_name, last_name = assign_names(name)

        tally = None
        if tally_id:
            try:
                tally = Tally.objects.get(id=tally_id)
            except Tally.DoesNotExist:
                command.stdout.write(command.style.ERROR(
                    f"Tally with id '{tally_id}' does not exist."
                ))
                return  # Exit function if the Tally is not found

        user = create_user(first_name, last_name, username, tally)

        permission = True if admin == 'Yes' else False
        user.is_superuser = user.is_staff = permission
        user.save()

    except Exception as e:
        command.stdout.write(command.style.ERROR(
            f"User '{username}' not created! '{e}'"
        ))
    else:
        system_role = STAFF_ROLE_DICT.get(role.upper().strip())

        if system_role:
            group = Group.objects.get_or_create(name=system_role)[0]
            user.groups.add(group)
        else:
            command.stdout.write(command.style.ERROR(
                f"Unable to add user {username} to unknown group '{role}'."
            ))


def assign_names(name):
    first_name = name
    last_name = u''
    split_names = name.split(u' ')

    if len(split_names) > 1:
        first_name = split_names[0]
        last_name = u' '.join(split_names[1:])

    return first_name, last_name


def create_user(first_name, last_name, username, tally=None):
    try:
        return UserProfile.objects.get(username=username)
    except UserProfile.DoesNotExist:
        user = UserProfile.objects.create_user(
            username=username,
            password=username,
            first_name=first_name,
            last_name=last_name
        )
        if tally:
            user.tally = tally
            user.save()
        return user


class Command(BaseCommand):
    help = gettext_lazy("Import staff list.")

    def handle(self, *args, **kwargs):
        self.import_staff_list()

    def import_staff_list(self):
        with codecs.open(STAFF_LIST_PATH, encoding='utf-8') as f:
            reader = unicode_csv_reader(f)
            next(reader)  # ignore header

            for row in reader:
                try:
                    name, username, role, admin = row[0:4]
                    tally_id =\
                        row[4].strip()\
                            if len(row) > 4 and row[4].strip() else None
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'Unable to add user in row: {row}. Exception: {e}.'
                    ))
                else:
                    add_row(self, name, username, role, admin, tally_id)

    def import_user_list(self):
        with codecs.open(USER_LIST_PATH, encoding='utf-8') as f:
            reader = unicode_csv_reader(f)
            next(reader)  # ignore header

            for row in reader:
                try:
                    username, name, role = row[0:3]
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        "Unable to add user in row: '%s'. Exception '%s'." %
                        (row, e)))
                else:
                    add_row(self, name, username, role)
