import codecs
import csv

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy

from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.user_profile import UserProfile

STAFF_LIST_PATH = 'data/staff_list.csv'
USER_LIST_PATH = 'data/user_list.csv'

# Dict for all the variations on Clerk names.
STAFF_ROLE_DICT = {
    'ADMINISTRATOR': groups.ADMINISTRATOR,
    'ARCHIVE SUPERVISOR': groups.ARCHIVE_SUPERVISOR,
    'ARCHIVE': groups.ARCHIVE_CLERK,
    'ARCHIVE CLERK': groups.ARCHIVE_CLERK,
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
    'IN TAKE': groups.INTAKE_CLERK,
    'INTAKE SUPERVISOR': groups.INTAKE_SUPERVISOR,
    'QUALITY CONTROL': groups.QUALITY_CONTROL_CLERK,
    'QUALITY CONTROL CLERK': groups.QUALITY_CONTROL_CLERK,
    'DATABASE': groups.SUPER_ADMINISTRATOR,
    'PROGRAMMER': groups.SUPER_ADMINISTRATOR,
    'SUPER ADMINISTRATOR': groups.SUPER_ADMINISTRATOR,
}

STAFF_ROLES = STAFF_ROLE_DICT.keys()


def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')


def add_row(name, username, role):
    try:
        first_name, last_name = assign_names(name)
        user = create_user(first_name, last_name, username)
    except Exception as e:
        print "User '%s' not created! '%s'" % (username, e)
    else:
        system_role = STAFF_ROLE_DICT.get(role.upper().strip())

        if system_role:
            group, created = Group.objects.get_or_create(
                name=system_role)
            user.groups.add(group)
        else:
            print (
                "Unable to add user %s to unknown group '%s'."
                % (username, role))


def assign_names(name):
    first_name = name
    last_name = u''
    split_names = name.split(u' ')

    if len(split_names) > 1:
        first_name = split_names[0]
        last_name = u' '.join(split_names[1:])

    return first_name, last_name


def create_user(first_name, last_name, username):
    try:
        return UserProfile.objects.get(username=username)
    except UserProfile.DoesNotExist:
        return UserProfile.objects.create_user(
            username, password=username,
            first_name=first_name,
            last_name=last_name)


class Command(BaseCommand):
    help = ugettext_lazy("Import staff list.")

    def handle(self, *args, **kwargs):
        self.import_staff_list()
        self.import_user_list()

    def import_staff_list(self):
        with codecs.open(STAFF_LIST_PATH, encoding='utf-8') as f:
            reader = unicode_csv_reader(f)
            reader.next()  # ignore header

            for row in reader:
                try:
                    name, username, role = row[0:3]
                except Exception as e:
                    print "Unable to add user in row: %s. Exception %s." %\
                        (row, e)
                else:
                    add_row(name, username, role)

    def import_user_list(self):
        with codecs.open(USER_LIST_PATH, encoding='utf-8') as f:
            reader = unicode_csv_reader(f)
            reader.next()  # ignore header

            for row in reader:
                try:
                    username, name, role = row[0:3]
                except Exception as e:
                    print "Unable to add user in row: '%s'. Exception '%s'." %\
                        (row, e)
                else:
                    add_row(name, username, role)
