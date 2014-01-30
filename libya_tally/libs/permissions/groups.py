from django.contrib.auth.models import Group

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
