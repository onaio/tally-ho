from django.contrib.auth.models import Group, User

ADMINISTRATOR = "Administrator"
ARCHIVE_CLERK = "Archive Clerk"
ARCHIVE_SUPERVISOR = "Archive Supervisor"
AUDIT_CLERK = "Audit Clerk"
AUDIT_SUPERVISOR = "Audit Supervisor"
CLEARANCE_CLERK = "Clearance Clerk"
CLEARANCE_SUPERVISOR = "Clearance Supervisor"
CORRECTIONS_CLERK = "Corrections Clerk"
DATA_ENTRY_1_CLERK = "Data Entry 1 Clerk"
DATA_ENTRY_2_CLERK = "Data Entry 2 Clerk"
INTAKE_CLERK = "Intake Clerk"
INTAKE_SUPERVISOR = "Intake Supervisor"
QUALITY_CONTROL_CLERK = "Quality Control Clerk"
SUPER_ADMINISTRATOR = "Super Administrator"

GROUPS = [ADMINISTRATOR, ARCHIVE_CLERK, ARCHIVE_SUPERVISOR, AUDIT_CLERK,
          AUDIT_SUPERVISOR, CLEARANCE_CLERK, CLEARANCE_SUPERVISOR,
          CORRECTIONS_CLERK, DATA_ENTRY_1_CLERK, DATA_ENTRY_2_CLERK,
          INTAKE_SUPERVISOR, INTAKE_CLERK, QUALITY_CONTROL_CLERK,
          SUPER_ADMINISTRATOR]


def create_permission_groups():
    for group in GROUPS:
        Group.objects.get_or_create(name=group)


def add_user_to_group(user, name):
    group = Group.objects.get(name=name)
    user.groups.add(group)


def create_demo_users_with_groups(password='data'):
    """Create a demo user for each group.

    :param password: The password for the demo users.
    """
    for group in GROUPS:
        obj, created = Group.objects.get_or_create(name=group)
        username = group.replace(' ', '_').lower()
        user, created = User.objects.get_or_create(
            username=username, first_name=group)
        user.set_password(password)
        user.save()
        user.groups.add(obj)


def user_groups(user):
    return user.groups.values_list("name", flat=True)
