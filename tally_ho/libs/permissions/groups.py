from django.contrib.auth.models import Group

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
QUALITY_CONTROL_SUPERVISOR = "Quality Control Supervisor"
SUPER_ADMINISTRATOR = "Super Administrator"
TALLY_MANAGER = "Tally Manager"

GROUPS = [
    QUALITY_CONTROL_SUPERVISOR,
    AUDIT_CLERK,
    AUDIT_SUPERVISOR,
    CLEARANCE_CLERK,
    CLEARANCE_SUPERVISOR,
    CORRECTIONS_CLERK,
    DATA_ENTRY_1_CLERK,
    DATA_ENTRY_2_CLERK,
    INTAKE_SUPERVISOR,
    INTAKE_CLERK,
    QUALITY_CONTROL_CLERK,
    SUPER_ADMINISTRATOR,
    TALLY_MANAGER,
]


def create_permission_groups():
    for group in GROUPS:
        Group.objects.get_or_create(name=group)


def add_user_to_group(user, name):
    group = Group.objects.get(name=name)
    user.groups.add(group)


def user_groups(user):
    # Check if user is authenticated and not anonymous before accessing groups
    if user and user.is_authenticated:
        return user.groups.values_list("name", flat=True)
    return []


# Helper functions for checking group membership
def is_audit_clerk(user):
    return AUDIT_CLERK in user_groups(user)


def is_audit_supervisor(user):
    return AUDIT_SUPERVISOR in user_groups(user)


def is_tally_manager(user):
    return TALLY_MANAGER in user_groups(user)


def is_super_administrator(user):
    return SUPER_ADMINISTRATOR in user_groups(user)
