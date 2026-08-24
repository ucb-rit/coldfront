from unittest.mock import patch

from django.contrib.auth.models import User

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
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import (
    ComputingAllowance,
)
from coldfront.core.resource.utils_.allowance_utils.interface import (
    ComputingAllowanceInterface,
)
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.email.email_strategy import EnqueueEmailStrategy
from coldfront.core.utils.tests.test_base import (
    LRCTestBase,
    TestBase,
    enable_deployment,
)


class AllowanceRenewalAvailableEmailSenderTestMixin:
    """Shared tests for AllowanceRenewalAvailableEmailSender, exercised
    under both BRC and LRC deployments via concrete subclasses."""

    def setUp(self):
        super().setUp()
        self._deployer = enable_deployment(self._deployment_name)
        self._deployer.enable()

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
        self.pi2 = User.objects.create(
            email="pi2@example.com",
            first_name="PI2",
            last_name="User",
            username="pi2",
        )
        for pi in [self.pi0, self.pi1, self.pi2]:
            profile = UserProfile.objects.get(user=pi)
            profile.is_pi = True
            profile.save()

        active_status = ProjectStatusChoice.objects.get(name="Active")
        inactive_status = ProjectStatusChoice.objects.get(name="Inactive")
        pi_role = ProjectUserRoleChoice.objects.get(name="Principal Investigator")
        active_pu_status = ProjectUserStatusChoice.objects.get(name="Active")

        allowance_resource = self.get_predominant_computing_allowance()
        self.allowance_resource = allowance_resource
        self.computing_allowance = ComputingAllowance(allowance_resource)
        prefix = ComputingAllowanceInterface().code_from_name(allowance_resource.name)

        # Three active projects, one inactive, all with the deployment prefix.
        self.project0 = Project.objects.create(
            name=f"{prefix}project0", status=active_status
        )
        self.project1 = Project.objects.create(
            name=f"{prefix}project1", status=active_status
        )
        self.project2 = Project.objects.create(
            name=f"{prefix}project2", status=active_status
        )
        self.project_inactive = Project.objects.create(
            name=f"{prefix}project_inactive", status=inactive_status
        )

        for project, pi in [
            (self.project0, self.pi0),
            (self.project1, self.pi1),
            (self.project2, self.pi2),
            (self.project_inactive, self.pi0),
        ]:
            ProjectUser.objects.create(
                project=project,
                user=pi,
                role=pi_role,
                status=active_pu_status,
            )

    def tearDown(self):
        self._deployer.disable()
        super().tearDown()

    def _make_sender(self, not_renewed_only=False):
        """Return an AllowanceRenewalAvailableEmailSender with
        _assert_allocation_period_ready mocked out (audit is tested
        separately; here we focus on project filtering and email queueing)."""
        self.email_strategy = EnqueueEmailStrategy()
        with patch.object(
            AllowanceRenewalAvailableEmailSender, "_assert_allocation_period_ready"
        ):
            sender = AllowanceRenewalAvailableEmailSender(
                self.current_period,
                self.next_period,
                self.computing_allowance,
                not_renewed_only=not_renewed_only,
                email_strategy=self.email_strategy,
            )
        return sender

    def _make_renewal_request(self, project, pi, status_name):
        """Create and return an AllocationRenewalRequest for the given
        project and PI targeting the next allocation period."""
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

    def _queued_project_pks(self):
        """Return the set of project PKs from the current email queue."""
        return {args[0].pk for _, args, _ in self.email_strategy.get_queue()}

    # --- _get_eligible_projects ---

    def test_eligible_projects_includes_all_active(self):
        """Without not_renewed_only, all active allowance projects are
        returned."""
        sender = self._make_sender()
        pks = {p.pk for p in sender._get_eligible_projects()}
        self.assertIn(self.project0.pk, pks)
        self.assertIn(self.project1.pk, pks)
        self.assertIn(self.project2.pk, pks)

    def test_eligible_projects_excludes_inactive(self):
        """Without not_renewed_only, inactive projects are not returned."""
        sender = self._make_sender()
        pks = {p.pk for p in sender._get_eligible_projects()}
        self.assertNotIn(self.project_inactive.pk, pks)

    def test_not_renewed_only_excludes_under_review(self):
        """With not_renewed_only, a project with an Under Review request
        for the next period is excluded."""
        self._make_renewal_request(self.project0, self.pi0, "Under Review")
        sender = self._make_sender(not_renewed_only=True)
        pks = {p.pk for p in sender._get_eligible_projects()}
        self.assertNotIn(self.project0.pk, pks)

    def test_not_renewed_only_excludes_approved(self):
        """With not_renewed_only, a project with an Approved request for the
        next period is excluded."""
        self._make_renewal_request(self.project0, self.pi0, "Approved")
        sender = self._make_sender(not_renewed_only=True)
        pks = {p.pk for p in sender._get_eligible_projects()}
        self.assertNotIn(self.project0.pk, pks)

    def test_not_renewed_only_excludes_complete(self):
        """With not_renewed_only, a project with a Complete request for the
        next period is excluded."""
        self._make_renewal_request(self.project0, self.pi0, "Complete")
        sender = self._make_sender(not_renewed_only=True)
        pks = {p.pk for p in sender._get_eligible_projects()}
        self.assertNotIn(self.project0.pk, pks)

    def test_not_renewed_only_keeps_denied_only(self):
        """With not_renewed_only, a project whose only renewal request for
        the next period is Denied is still included."""
        self._make_renewal_request(self.project0, self.pi0, "Denied")
        sender = self._make_sender(not_renewed_only=True)
        pks = {p.pk for p in sender._get_eligible_projects()}
        self.assertIn(self.project0.pk, pks)

    def test_not_renewed_only_keeps_no_request(self):
        """With not_renewed_only, projects with no renewal request for the
        next period are included."""
        self._make_renewal_request(self.project0, self.pi0, "Under Review")
        sender = self._make_sender(not_renewed_only=True)
        pks = {p.pk for p in sender._get_eligible_projects()}
        self.assertIn(self.project1.pk, pks)
        self.assertIn(self.project2.pk, pks)

    # --- run() ---

    def test_run_queues_one_email_per_active_project(self):
        """run() without not_renewed_only queues exactly one email per
        active project and excludes the inactive project."""
        sender = self._make_sender()
        sender.run()
        queued_pks = self._queued_project_pks()
        self.assertEqual(len(self.email_strategy.get_queue()), 3)
        self.assertIn(self.project0.pk, queued_pks)
        self.assertIn(self.project1.pk, queued_pks)
        self.assertIn(self.project2.pk, queued_pks)
        self.assertNotIn(self.project_inactive.pk, queued_pks)

    def test_run_not_renewed_only_skips_renewed_projects(self):
        """run() with not_renewed_only only queues emails for projects that
        have not yet submitted a non-denied renewal request."""
        self._make_renewal_request(self.project0, self.pi0, "Under Review")
        sender = self._make_sender(not_renewed_only=True)
        sender.run()
        queued_pks = self._queued_project_pks()
        self.assertEqual(len(self.email_strategy.get_queue()), 2)
        self.assertNotIn(self.project0.pk, queued_pks)
        self.assertIn(self.project1.pk, queued_pks)
        self.assertIn(self.project2.pk, queued_pks)

    def test_run_not_renewed_only_includes_denied_project(self):
        """run() with not_renewed_only queues an email for a project that
        only has a Denied renewal request."""
        self._make_renewal_request(self.project0, self.pi0, "Denied")
        sender = self._make_sender(not_renewed_only=True)
        sender.run()
        queued_pks = self._queued_project_pks()
        self.assertIn(self.project0.pk, queued_pks)


class TestAllowanceRenewalAvailableEmailSenderBRC(
    AllowanceRenewalAvailableEmailSenderTestMixin, TestBase
):
    """Run AllowanceRenewalAvailableEmailSender tests under BRC (FCA)."""


class TestAllowanceRenewalAvailableEmailSenderLRC(
    AllowanceRenewalAvailableEmailSenderTestMixin, LRCTestBase
):
    """Run AllowanceRenewalAvailableEmailSender tests under LRC (PCA)."""
