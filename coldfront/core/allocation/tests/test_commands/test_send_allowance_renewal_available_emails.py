from io import StringIO
import logging
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command

from coldfront.core.allocation.models import (
    AllocationRenewalRequest,
    AllocationRenewalRequestStatusChoice,
)
from coldfront.core.project.models import (
    Project,
    ProjectStatusChoice,
    ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)
from coldfront.core.project.utils_.renewal_utils import (
    AllowanceRenewalAvailableEmailSender,
    get_current_allowance_year_period,
    get_next_allowance_year_period,
)
from coldfront.core.resource.utils_.allowance_utils.interface import (
    ComputingAllowanceInterface,
)
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import LRCTestBase, TestBase


class SendAllowanceRenewalAvailableEmailsTestMixin:
    """Shared tests for the send_allowance_renewal_available_emails command,
    exercised under both BRC and LRC deployments via concrete subclasses."""

    def setUp(self):
        super().setUp()

        self.current_period = get_current_allowance_year_period()
        self.next_period = get_next_allowance_year_period()

        self.pi0 = User.objects.create(
            email="pi0@example.com",
            first_name="PI0",
            last_name="User",
            username="pi0",
        )
        self.pi1 = User.objects.create(
            email="pi1@example.com",
            first_name="PI1",
            last_name="User",
            username="pi1",
        )
        for pi in [self.pi0, self.pi1]:
            profile = UserProfile.objects.get(user=pi)
            profile.is_pi = True
            profile.save()

        active_status = ProjectStatusChoice.objects.get(name="Active")
        pi_role = ProjectUserRoleChoice.objects.get(name="Principal Investigator")
        active_pu_status = ProjectUserStatusChoice.objects.get(name="Active")

        allowance_resource = self.get_predominant_computing_allowance()
        self.allowance_resource = allowance_resource
        prefix = ComputingAllowanceInterface().code_from_name(allowance_resource.name)

        self.project0 = Project.objects.create(
            name=f"{prefix}project0", status=active_status
        )
        self.project1 = Project.objects.create(
            name=f"{prefix}project1", status=active_status
        )

        for project, pi in [
            (self.project0, self.pi0),
            (self.project1, self.pi1),
        ]:
            ProjectUser.objects.create(
                project=project,
                user=pi,
                role=pi_role,
                status=active_pu_status,
            )

    def _call_command_dry_run(self, *extra_args):
        """Call the command with --dry_run and _assert_allocation_period_ready
        mocked out. Returns the stdout string."""
        out = StringIO()
        with patch.object(
            AllowanceRenewalAvailableEmailSender, "_assert_allocation_period_ready"
        ):
            call_command(
                "send_allowance_renewal_available_emails",
                "--dry_run",
                *extra_args,
                stdout=out,
            )
        return out.getvalue()

    def _make_renewal_request(self, project, pi, status_name):
        """Create an AllocationRenewalRequest for the given project/PI
        targeting the next allocation period."""
        status = AllocationRenewalRequestStatusChoice.objects.get(name=status_name)
        return AllocationRenewalRequest.objects.create(
            requester=pi,
            pi=pi,
            computing_allowance=self.allowance_resource,
            allocation_period=self.next_period,
            status=status,
            pre_project=project,
            post_project=project,
            request_time=utc_now_offset_aware(),
        )

    # --- default (all active) ---

    def test_dry_run_logs_all_active_projects(self):
        """--dry_run logs a count of all active allowance projects."""
        with self.assertLogs("coldfront.commands", level=logging.INFO) as cm:
            self._call_command_dry_run()
        self.assertTrue(
            any("Would send emails to 2 projects." in msg for msg in cm.output)
        )

    # --- --not-renewed-only ---

    def test_dry_run_not_renewed_only_excludes_renewed(self):
        """--not-renewed-only reduces the count when a project has already
        submitted a non-denied renewal request."""
        self._make_renewal_request(self.project0, self.pi0, "Under Review")
        with self.assertLogs("coldfront.commands", level=logging.INFO) as cm:
            self._call_command_dry_run("--not-renewed-only")
        self.assertTrue(
            any("Would send emails to 1 projects." in msg for msg in cm.output)
        )

    def test_dry_run_not_renewed_only_all_renewed(self):
        """--not-renewed-only logs 0 projects when all active projects have
        non-denied renewal requests."""
        self._make_renewal_request(self.project0, self.pi0, "Approved")
        self._make_renewal_request(self.project1, self.pi1, "Complete")
        with self.assertLogs("coldfront.commands", level=logging.INFO) as cm:
            self._call_command_dry_run("--not-renewed-only")
        self.assertTrue(
            any("Would send emails to 0 projects." in msg for msg in cm.output)
        )

    def test_dry_run_not_renewed_only_denied_counts_as_not_renewed(self):
        """--not-renewed-only treats a project with only a Denied request as
        not yet renewed, so it is still included in the count."""
        self._make_renewal_request(self.project0, self.pi0, "Denied")
        with self.assertLogs("coldfront.commands", level=logging.INFO) as cm:
            self._call_command_dry_run("--not-renewed-only")
        self.assertTrue(
            any("Would send emails to 2 projects." in msg for msg in cm.output)
        )

    # --- wet run (confirmed) ---

    def test_confirmed_by_user_logs_sent_count(self):
        """Entering 'y' at the confirmation prompt logs the sent count."""
        with self.assertLogs("coldfront.commands", level=logging.INFO) as cm:
            with patch.object(
                AllowanceRenewalAvailableEmailSender, "_assert_allocation_period_ready"
            ):
                with patch("builtins.input", return_value="y"):
                    call_command("send_allowance_renewal_available_emails")
        self.assertTrue(any("Sent emails to 2 projects." in msg for msg in cm.output))

    # --- cancellation ---

    def test_cancelled_by_user_prints_warning(self):
        """Entering 'n' at the confirmation prompt prints 'Operation
        cancelled.' and returns without sending emails."""
        out = StringIO()
        with patch.object(
            AllowanceRenewalAvailableEmailSender, "_assert_allocation_period_ready"
        ):
            with patch("builtins.input", return_value="n"):
                call_command("send_allowance_renewal_available_emails", stdout=out)
        self.assertIn("Operation cancelled.", out.getvalue())


class TestSendAllowanceRenewalAvailableEmailsBRC(
    SendAllowanceRenewalAvailableEmailsTestMixin, TestBase
):
    """Run send_allowance_renewal_available_emails tests under BRC (FCA)."""


class TestSendAllowanceRenewalAvailableEmailsLRC(
    SendAllowanceRenewalAvailableEmailsTestMixin, LRCTestBase
):
    """Run send_allowance_renewal_available_emails tests under LRC (PCA)."""
