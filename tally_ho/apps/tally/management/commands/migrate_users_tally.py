from argparse import RawDescriptionHelpFormatter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile


class Command(BaseCommand):
    help = (
        "Migrate users from one tally to another within the same database.\n\n"
        "Example usage:\n"
        "    # Migrate all users from tally 2 to tally 5\n"
        "    python manage.py migrate_users_tally --source-tally 2 "
        "--target-tally 5 --all-users\n"
        "\n"
        "    # Migrate specific users\n"
        "    python manage.py migrate_users_tally --source-tally 2 "
        "--target-tally 5 --usernames 'user1,user2,user3'\n"
        "\n"
        "    # Dry run to preview changes\n"
        "    python manage.py migrate_users_tally --source-tally 2 "
        "--target-tally 5 --all-users --dry-run\n"
        "\n"
        "    # Migrate all except certain users\n"
        "    python manage.py migrate_users_tally --source-tally 2 "
        "--target-tally 5 --all-users --exclude-usernames 'admin,super_user'\n"
    )

    def create_parser(self, prog_name, subcommand, **kwargs):
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        parser.formatter_class = RawDescriptionHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-tally",
            type=int,
            required=True,
            help="Source tally ID to migrate users from",
        )
        parser.add_argument(
            "--target-tally",
            type=int,
            required=True,
            help="Target tally ID to migrate users to",
        )
        parser.add_argument(
            "--all-users",
            action="store_true",
            help="Migrate all users from source tally",
        )
        parser.add_argument(
            "--usernames",
            type=str,
            help="Comma-separated list of specific usernames to migrate",
        )
        parser.add_argument(
            "--exclude-usernames",
            type=str,
            help="Comma-separated list of usernames to exclude from migration",
        )
        parser.add_argument(
            "--preserve-admin-tallies",
            action="store_true",
            help="Keep administrated_tallies associations (default: False)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without making them",
        )

    def handle(self, *args, **options):
        source_tally_id = options["source_tally"]
        target_tally_id = options["target_tally"]
        all_users = options["all_users"]
        usernames = options.get("usernames")
        exclude_usernames = options.get("exclude_usernames")
        preserve_admin_tallies = options["preserve_admin_tallies"]
        dry_run = options["dry_run"]

        # Validate arguments
        if not all_users and not usernames:
            raise CommandError(
                "Either --all-users or --usernames must be specified"
            )

        if all_users and usernames:
            raise CommandError(
                "Cannot specify both --all-users and --usernames"
            )

        if source_tally_id == target_tally_id:
            raise CommandError("Source and target tally cannot be the same")

        # Validate tallies exist
        try:
            source_tally = Tally.objects.get(id=source_tally_id)
        except Tally.DoesNotExist:
            raise CommandError(
                f"Source tally with ID '{source_tally_id}' does not exist"
            )

        try:
            target_tally = Tally.objects.get(id=target_tally_id)
        except Tally.DoesNotExist:
            raise CommandError(
                f"Target tally with ID '{target_tally_id}' does not exist"
            )

        # Build queryset
        queryset = UserProfile.objects.filter(tally=source_tally)

        if usernames:
            username_list = [u.strip() for u in usernames.split(",")]
            queryset = queryset.filter(username__in=username_list)

            # Check if all specified users exist
            existing_usernames = set(
                queryset.values_list("username", flat=True)
            )
            missing_usernames = set(username_list) - existing_usernames
            if missing_usernames:
                raise CommandError(
                    f"The following users do not exist in source tally: "
                    f"{', '.join(missing_usernames)}"
                )

        if exclude_usernames:
            exclude_list = [u.strip() for u in exclude_usernames.split(",")]
            queryset = queryset.exclude(username__in=exclude_list)

        users_to_migrate = list(queryset.order_by("username"))

        if not users_to_migrate:
            self.stdout.write(
                self.style.WARNING(
                    "No users found to migrate with the given criteria"
                )
            )
            return

        # Display summary
        self.stdout.write("Migration Summary:")
        self.stdout.write(
            f"  Source Tally: {source_tally.name} (ID: {source_tally_id})"
        )
        self.stdout.write(
            f"  Target Tally: {target_tally.name} (ID: {target_tally_id})"
        )
        self.stdout.write(f"  Users to migrate: {len(users_to_migrate)}")
        self.stdout.write(
            f"  Preserve admin tallies: {preserve_admin_tallies}"
        )
        self.stdout.write(f"  Dry run: {dry_run}")
        self.stdout.write("")

        # Show users to be migrated
        self.stdout.write("Users to be migrated:")
        for user in users_to_migrate:
            admin_tallies = user.administrated_tallies.all()
            tally_names = ', '.join([t.name for t in admin_tallies])
            admin_info = (
                f" (administrates: {tally_names})"
                if admin_tallies
                else ""
            )
            self.stdout.write(
                f"  - {user.username} ({user.first_name} {user.last_name})"
                f"{admin_info}"
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nDRY RUN: No changes were made to the database"
                )
            )
            return

        # Perform migration
        self.stdout.write("\nStarting migration...")
        migrated_count = 0
        errors = []

        try:
            with transaction.atomic():
                for user in users_to_migrate:
                    try:
                        # Store original admin tallies if not preserving
                        if not preserve_admin_tallies:
                            admin_tallies_to_remove = list(
                                user.administrated_tallies.all()
                            )

                        # Update user's tally
                        user.tally = target_tally
                        user.save(update_fields=["tally"])

                        # Remove admin tallies if not preserving
                        if (
                            not preserve_admin_tallies
                            and admin_tallies_to_remove
                        ):
                            user.administrated_tallies.remove(
                                *admin_tallies_to_remove
                            )

                        migrated_count += 1
                        self.stdout.write(f"  ✓ Migrated {user.username}")

                    except Exception as e:
                        error_msg = f"Failed to migrate {user.username}: {e}"
                        errors.append(error_msg)
                        self.stdout.write(self.style.ERROR(f"  ✗ {error_msg}"))

                if errors:
                    raise CommandError(
                        f"Migration failed with {len(errors)} errors"
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"\nMigration failed and was rolled back: {e}"
                )
            )
            return

        # Display final summary
        self.stdout.write(
            self.style.SUCCESS(
                "\nMigration completed successfully!"
            )
        )
        self.stdout.write(f"  Total users migrated: {migrated_count}")
        self.stdout.write(
            f"  From: {source_tally.name} (ID: {source_tally_id})"
        )
        self.stdout.write(f"  To: {target_tally.name} (ID: {target_tally_id})")

        if not preserve_admin_tallies:
            self.stdout.write(
                "\nNote: Administrated tally associations were removed. "
                "Users may need to be re-assigned as administrators if needed."
            )
