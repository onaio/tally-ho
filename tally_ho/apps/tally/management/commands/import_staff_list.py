import csv
import os

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.permissions import groups

# Default paths for backward compatibility
DEFAULT_STAFF_LIST_PATH = "data/staff_list.csv"

# Dict for all the variations on Clerk names.
STAFF_ROLE_DICT = {
    "AUDIT CLERK": groups.AUDIT_CLERK,
    "AUDIT SUPERVISOR": groups.AUDIT_SUPERVISOR,
    "CLEARANCE CLERK": groups.CLEARANCE_CLERK,
    "CLEARANCE SUPERVISOR": groups.CLEARANCE_SUPERVISOR,
    "CORRECTION": groups.CORRECTIONS_CLERK,
    "CORRECTION CLERK": groups.CORRECTIONS_CLERK,
    "CORRECTIONS CLERK": groups.CORRECTIONS_CLERK,
    "CORRECTION SUPERVISOR": groups.CORRECTIONS_CLERK,
    "DATA ENTRY 1": groups.DATA_ENTRY_1_CLERK,
    "DATA ENTRY 1 CLERK": groups.DATA_ENTRY_1_CLERK,
    "DATA ENTRY 2": groups.DATA_ENTRY_2_CLERK,
    "DATA ENTRY 2 CLERK": groups.DATA_ENTRY_2_CLERK,
    "DATA ENTRY 1 SUPERVISOR": groups.DATA_ENTRY_1_CLERK,
    "DATA ENTRY 2 SUPERVISOR": groups.DATA_ENTRY_2_CLERK,
    "INTAKE CLERK": groups.INTAKE_CLERK,
    "INTAKE": groups.INTAKE_CLERK,
    "INTAKE SUPERVISOR": groups.INTAKE_SUPERVISOR,
    "QUALITY CONTROL CLERK": groups.QUALITY_CONTROL_CLERK,
    "QUALITY CONTROL SUPERVISOR": groups.QUALITY_CONTROL_SUPERVISOR,
    "DATABASE": groups.SUPER_ADMINISTRATOR,
    "PROGRAMMER": groups.SUPER_ADMINISTRATOR,
    "SUPER ADMINISTRATOR": groups.SUPER_ADMINISTRATOR,
    "TALLY MANAGER": groups.TALLY_MANAGER,
}


def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(unicode_csv_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield row


def add_row(
    command,
    name,
    username,
    role,
    admin=None,
    tally_id=None,
    password_suffix=None,
):
    """Add a user from a CSV row with required password suffix."""
    try:
        # Parse the name into first and last name
        first_name, last_name = assign_names(name)

        tally = None
        if tally_id:
            try:
                tally = Tally.objects.get(id=tally_id)
            except Tally.DoesNotExist:
                command.stdout.write(
                    command.style.ERROR(
                        f"Tally with id '{tally_id}' does not exist."
                    )
                )
                return False  # Exit function if the Tally is not found

        user, was_created = create_user(
            first_name,
            last_name,
            username,
            tally,
            password_suffix=password_suffix,
        )

        # Only modify permissions and groups for newly created users
        if was_created:
            permission = True if admin == "Yes" else False
            user.is_superuser = user.is_staff = permission
            user.save(update_fields=["is_superuser", "is_staff"])

    except Exception as e:
        command.stdout.write(
            command.style.ERROR(f"User '{username}' not created! '{e}'")
        )
        return False
    else:
        system_role = STAFF_ROLE_DICT.get(role.upper().strip())

        if system_role:
            # Only add to group if user was newly created
            if was_created:
                group = Group.objects.get_or_create(name=system_role)[0]
                user.groups.add(group)
                command.stdout.write(
                    f"Created user '{username}' with role '{system_role}'"
                )
            else:
                command.stdout.write(
                    f"User '{username}' already exists, skipped"
                )
            return True
        else:
            command.stdout.write(
                command.style.ERROR(
                    f"Unable to add user {username} to unknown group '{role}'."
                )
            )
            return False


def assign_names(name):
    first_name = name
    last_name = ""
    split_names = name.split(" ")

    if len(split_names) > 1:
        first_name = split_names[0]
        last_name = " ".join(split_names[1:])

    return first_name, last_name


def create_user(
    first_name, last_name, username, tally=None, password_suffix=None
):
    """Create a user with password as username + suffix.

    Args:
        first_name: User's first name
        last_name: User's last name
        username: User's username
        tally: Optional Tally object to assign
        password_suffix: Required suffix for password generation

    Returns:
        Tuple of (user, was_created)
    """
    try:
        return UserProfile.objects.get(
            username=username
        ), False  # Return existing user and False (not created)
    except UserProfile.DoesNotExist:
        if not password_suffix:
            raise ValueError("password_suffix is required for user creation")

        user = UserProfile(
            username=username,
            first_name=first_name,
            last_name=last_name,
            reset_password=True,
        )
        if tally:
            user.tally = tally
        # Save with password_suffix - UserProfile.save() will create password
        # as username + suffix
        user.save(password_suffix=password_suffix)

        return user, True  # Return new user and True (created)


class Command(BaseCommand):
    help = (
        "Import staff list from CSV file.\n\n"
        "Example usage:\n"
        "    python manage.py import_staff_list --csv-template staff "
        "--password-suffix '@2024Secure'\n"
        "    python manage.py import_staff_list --csv-file users.csv "
        "--csv-template staff --password-suffix '#Tally2024'\n"
        "    python manage.py import_staff_list --csv-file users.csv "
        "--csv-template user --password-suffix '!Secure123'\n"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            "--file",
            dest="csv_file",
            type=str,
            default=DEFAULT_STAFF_LIST_PATH,
            help=(
                "Path to CSV file to import "
                f"(default: {DEFAULT_STAFF_LIST_PATH})"
            ),
        )
        parser.add_argument(
            "--csv-template",
            type=str,
            choices=["staff", "user"],
            required=True,
            help=(
                "CSV template format: 'staff' "
                "(name,username,role,admin,tally_id) "
                "or 'user' (username,name,role)"
            ),
        )
        parser.add_argument(
            "--password-suffix",
            type=str,
            required=True,
            help=(
                "Required suffix to append to usernames for initial "
                "passwords. Example: '@2024' will create passwords like "
                "'username@2024'. Users must change password on first login. "
                "Minimum 4 characters."
            ),
        )

    def handle(self, *args, **kwargs):
        csv_file = kwargs["csv_file"]
        csv_template = kwargs["csv_template"]
        password_suffix = kwargs["password_suffix"]

        # Validate password suffix has minimum security requirements
        if len(password_suffix) < 4:
            raise CommandError(
                "Password suffix must be at least 4 characters long"
            )

        # Check if file exists
        if not os.path.exists(csv_file):
            raise CommandError(f"CSV file '{csv_file}' does not exist.")

        # Import using appropriate template
        if csv_template == "user":
            self.stdout.write(
                f"Using user template with password suffix: {password_suffix}"
            )
            self.import_user_list(csv_file, password_suffix)
        elif csv_template == "staff":
            self.stdout.write(
                f"Using staff template with password suffix: {password_suffix}"
            )
            self.import_staff_list(csv_file, password_suffix)
        else:
            raise CommandError(f"Invalid template: {csv_template}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully imported users from '{csv_file}'"
            )
        )

    def import_staff_list(self, csv_file, password_suffix):
        """Import users from staff format CSV"""
        self.stdout.write(f"Importing staff from '{csv_file}'...")
        imported_count = 0
        error_count = 0

        with open(csv_file, encoding="utf-8") as f:
            reader = unicode_csv_reader(f)
            try:
                next(reader)  # ignore header
            except StopIteration:
                self.stdout.write("CSV file is empty or has no data rows.")
                return

            for row_num, row in enumerate(
                reader, start=2
            ):  # Start at 2 to account for header
                try:
                    name, username, role, admin = row[0:4]
                    tally_id = (
                        row[4].strip()
                        if len(row) > 4 and row[4].strip()
                        else None
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Row {row_num}: Unable to parse row: {row}. "
                            f"xception: {e}"
                        )
                    )
                    error_count += 1
                else:
                    if add_row(
                        self,
                        name,
                        username,
                        role,
                        admin,
                        tally_id,
                        password_suffix,
                    ):
                        imported_count += 1
                    else:
                        error_count += 1

        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported_count} users successfully."
            )
        )
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Failed to import {error_count} users.")
            )

    def import_user_list(self, csv_file, password_suffix):
        """Import users from user format CSV"""
        self.stdout.write(f"Importing users from '{csv_file}'...")
        imported_count = 0
        error_count = 0

        with open(csv_file, encoding="utf-8") as f:
            reader = unicode_csv_reader(f)
            try:
                next(reader)  # ignore header
            except StopIteration:
                self.stdout.write("CSV file is empty or has no data rows.")
                return

            for row_num, row in enumerate(
                reader, start=2
            ):  # Start at 2 to account for header
                try:
                    username, name, role = row[0:3]
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Row {row_num}: Unable to parse row: {row}. "
                            f"xception: {e}"
                        )
                    )
                    error_count += 1
                else:
                    if add_row(
                        self,
                        name,
                        username,
                        role,
                        password_suffix=password_suffix,
                    ):
                        imported_count += 1
                    else:
                        error_count += 1

        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported_count} users successfully."
            )
        )
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Failed to import {error_count} users.")
            )
