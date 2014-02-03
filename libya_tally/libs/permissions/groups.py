from django.contrib.auth.models import Group, User

ADMINISTRATOR = "Administrator"
ARCHIVING_CLERK = "Archiving Clerk"
ARCHIVE_SUPERVISOR = "Archive Supervisor"
AUDIT_CLERK = "Audit Clerk"
AUDIT_SUPERVISOR = "Audit Supervisor"
CLEARANCE_CLERK = "Clearance Clerk"
CLEARANCE_SUPERVISOR = "Clearance Supervisor"
CORRECTIONS_CLERK = "Corrections Clerk"
DATA_ENTRY_CLERK = "Data Entry Clerk"
INTAKE_CLERK = "Intake Clerk"
INTAKE_SUPERVISOR = "Intake Supervisor"
QUALITY_CONTROL_CLERK = "Quality Control Clerk"
SUPER_ADMINISTRATOR = "Super Administrator"

GROUPS = [ADMINISTRATOR, ARCHIVING_CLERK, ARCHIVE_SUPERVISOR, AUDIT_CLERK,
          AUDIT_SUPERVISOR, CLEARANCE_CLERK, CLEARANCE_SUPERVISOR,
          CORRECTIONS_CLERK, DATA_ENTRY_CLERK, INTAKE_SUPERVISOR,
          INTAKE_CLERK, QUALITY_CONTROL_CLERK, SUPER_ADMINISTRATOR]


def create_permission_groups():
    for group in GROUPS:
        Group.objects.get_or_create(name=group)


def add_user_to_group(user, name):
    group = Group.objects.get(name=name)
    user.groups.add(group)


def create_demo_users_with_groups(password='data'):
    for group in GROUPS:
        obj, created = Group.objects.get_or_create(name=group)
        username = group.replace(' ', '_').lower()
        user, created = User.objects.get_or_create(
            username=username, first_name=group)
        user.set_password(password)
        user.save()
        user.groups.add(obj)
