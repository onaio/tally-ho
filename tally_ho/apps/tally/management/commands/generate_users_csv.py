import csv
from argparse import RawDescriptionHelpFormatter

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Generate a CSV file with users for import_staff_list command\n\n"
        "Example usage:\n"
        "    python manage.py generate_users_csv \\\n"
        "        --audit-count 8 \\\n"
        "        --intake-count 12 \\\n"
        "        --clearance-count 5 \\\n"
        "        --quality-control-count 10 \\\n"
        "        --data-entry-1-count 30 \\\n"
        "        --data-entry-2-count 30 \\\n"
        "        --corrections-count 9 \\\n"
        "        --tally-id 2 \\\n"
        "        --output users.csv\n"
    )

    def create_parser(self, prog_name, subcommand, **kwargs):
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        parser.formatter_class = RawDescriptionHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            "--audit-count",
            type=int,
            default=1,
            help="Number of Audit Clerk users to generate (default: 1)",
        )
        parser.add_argument(
            "--intake-count",
            type=int,
            default=1,
            help="Number of Intake Clerk users to generate (default: 1)",
        )
        parser.add_argument(
            "--clearance-count",
            type=int,
            default=1,
            help="Number of Clearance Clerk users to generate (default: 1)",
        )
        parser.add_argument(
            "--quality-control-count",
            type=int,
            default=1,
            help=(
                "Number of Quality Control Clerk users to generate"
                " (default: 1)"
            ),
        )
        parser.add_argument(
            "--data-entry-1-count",
            type=int,
            default=1,
            help="Number of Data Entry 1 Clerk users to generate (default: 1)",
        )
        parser.add_argument(
            "--data-entry-2-count",
            type=int,
            default=1,
            help="Number of Data Entry 2 Clerk users to generate (default: 1)",
        )
        parser.add_argument(
            "--corrections-count",
            type=int,
            default=1,
            help="Number of Correction Clerk users to generate (default: 1)",
        )
        parser.add_argument(
            "--tally-id",
            type=int,
            default=1,
            help="Tally ID to assign users to (default: 1)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="users.csv",
            help="Output CSV file path (default: users.csv)",
        )

    def handle(self, *args, **options):
        audit_count = options["audit_count"]
        intake_count = options["intake_count"]
        clearance_count = options["clearance_count"]
        quality_control_count = options["quality_control_count"]
        data_entry_1_count = options["data_entry_1_count"]
        data_entry_2_count = options["data_entry_2_count"]
        corrections_count = options["corrections_count"]
        tally_id = options["tally_id"]
        output_file = options["output"]

        # Role configurations
        role_configs = [
            {"role": "Audit Clerk", "prefix": "aud", "count": audit_count},
            {"role": "Intake Clerk", "prefix": "intk", "count": intake_count},
            {
                "role": "Clearance Clerk",
                "prefix": "clr",
                "count": clearance_count,
            },
            {
                "role": "Quality Control Clerk",
                "prefix": "qar",
                "count": quality_control_count,
            },
            {
                "role": "Data Entry 1 Clerk",
                "prefix": "de1",
                "count": data_entry_1_count,
            },
            {
                "role": "Data Entry 2 Clerk",
                "prefix": "de2",
                "count": data_entry_2_count,
            },
            {
                "role": "Correction Clerk",
                "prefix": "cor",
                "count": corrections_count,
            },
        ]

        # Generate users
        users = []
        total_users = 0

        for config in role_configs:
            role = config["role"]
            prefix = config["prefix"]
            count = config["count"]

            for i in range(1, count + 1):
                username = f"{prefix}-{i:02d}"
                name = f"{role} {i:02d}"
                users.append(
                    {
                        "name": name,
                        "username": username,
                        "role": role,
                        "admin": "No",
                        "tally_id": tally_id,
                    }
                )
                total_users += 1

        # Write to CSV
        with open(output_file, "w", newline="") as csvfile:
            fieldnames = ["name", "username", "role", "admin", "tally_id"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for user in users:
                writer.writerow(user)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully generated {total_users} "
                f"users in '{output_file}'"
            )
        )

        # Display summary
        self.stdout.write("\nGenerated users summary:")
        for config in role_configs:
            if config["count"] > 0:
                self.stdout.write(
                    f"  - {config['count']} {config['role']} user(s)"
                )
        self.stdout.write(f"  - All users assigned to Tally ID: {tally_id}")
