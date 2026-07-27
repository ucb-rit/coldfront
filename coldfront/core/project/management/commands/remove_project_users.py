import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from coldfront.core.project.models import ProjectUser
from coldfront.core.project.utils_.removal_utils import ProjectRemovalRequestRunner
from coldfront.core.utils.common import add_argparse_dry_run_argument


class Command(BaseCommand):
    help = (
        "Create project removal requests for a list of users. Reads usernames "
        "from a file (one per line) and creates a pending removal request for "
        "each of their active project memberships."
    )
    logger = logging.getLogger("coldfront.commands")

    def add_arguments(self, parser):
        add_argparse_dry_run_argument(parser)
        parser.add_argument(
            "input_file",
            help="Path to a file containing usernames to remove, one per line.",
        )
        parser.add_argument(
            "--requester",
            required=True,
            help=("Username of the user initiating the removal requests."),
        )
        parser.add_argument(
            "--reason",
            default="",
            help="Optional reason stored on each removal request for audit purposes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        reason = options["reason"]

        try:
            requester = User.objects.get(username=options["requester"])
        except User.DoesNotExist:
            raise CommandError(
                f'Requester "{options["requester"]}" not found.'
            ) from None

        try:
            with open(options["input_file"]) as f:
                usernames = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            raise CommandError(
                f'Input file "{options["input_file"]}" not found.'
            ) from None

        if not usernames:
            self.logger.info("No usernames found in input file.")
            return

        # Deduplicate while preserving order.
        seen = set()
        unique_usernames = []
        for u in usernames:
            if u not in seen:
                seen.add(u)
                unique_usernames.append(u)
        usernames = unique_usernames

        self.logger.info(f"Processing {len(usernames)} username(s).")

        num_requests = 0
        num_skipped = 0
        num_errors = 0

        for username in usernames:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.logger.warning(f'[SKIP] "{username}": user not found.')
                num_skipped += 1
                continue

            active_memberships = ProjectUser.objects.filter(
                user=user,
                status__name="Active",
            ).select_related("project")

            if not active_memberships.exists():
                self.logger.info(f"[SKIP] {username}: no active project memberships.")
                num_skipped += 1
                continue

            for project_user in active_memberships:
                project = project_user.project
                if dry_run:
                    self.logger.info(
                        f"DRY RUN: Would request removal of {username} "
                        f"from {project.name}."
                    )
                    num_requests += 1
                    continue

                runner = ProjectRemovalRequestRunner(
                    requester, user, project, reason=reason
                )
                runner.run()
                success_messages, error_messages = runner.get_messages()

                for msg in success_messages:
                    self.logger.info(f"[OK] {username} / {project.name}: {msg}")
                    num_requests += 1
                for msg in error_messages:
                    self.logger.error(f"[ERROR] {username} / {project.name}: {msg}")
                    num_errors += 1

        prefix = "DRY RUN: Would have created" if dry_run else "Created"
        self.logger.info(
            f"{prefix} {num_requests} removal request(s). "
            f"Skipped {num_skipped}. Errors: {num_errors}."
        )
