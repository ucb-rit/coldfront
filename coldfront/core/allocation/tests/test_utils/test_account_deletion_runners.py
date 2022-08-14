import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail

from coldfront.api.statistics.utils import create_project_allocation, \
    create_user_project_allocation
from coldfront.config import settings
from coldfront.core.allocation.models import AccountDeletionRequestReasonChoice, \
    AccountDeletionRequestStatusChoice, AccountDeletionRequest, \
    AllocationAttributeType, AllocationUserAttribute
from coldfront.core.allocation.utils_.account_deletion_utils import \
    AccountDeletionRequestRunner
from coldfront.core.billing.models import BillingActivity, BillingProject
from coldfront.core.project.models import ProjectStatusChoice, Project, \
    ProjectUser, ProjectUserStatusChoice, ProjectUserRoleChoice, \
    ProjectUserRemovalRequest
from coldfront.core.utils.common import utc_now_offset_aware, \
    import_from_settings
from coldfront.core.utils.tests.test_base import TestBase


class TestAccountDeletionRunnersBase(TestBase):
    """Base testing class for AccountDeletionRequest runners."""

    def setUp(self):
        super().setUp()

        self.superuser = User.objects.create(username='superuser',
                                             email='superuser@example.com',
                                             is_superuser=True)

        self.create_test_user()
        self.user.userprofile.cluster_uid = '11223344'
        billing_project = BillingProject.objects.create(
            identifier='123456',
            description='Test description.')
        self.user.userprofile.billing_activity = \
            BillingActivity.objects.create(identifier='123',
                                           billing_project=billing_project)
        self.user.userprofile.host_user = self.superuser
        self.user.userprofile.save()

        for i in range(3):
            project = Project.objects.create(
                name=f'project{i}',
                status=ProjectStatusChoice.objects.get(name='Active'))
            setattr(self, f'project{i}', project)

            project_user = ProjectUser.objects.create(
                project=project,
                user=self.user,
                status=ProjectUserStatusChoice.objects.get(name='Active'),
                role=ProjectUserRoleChoice.objects.get(name='User'))
            setattr(self, f'project_user{i}', project_user)

            # Create a compute allocation for the Project.
            amount = Decimal(f'{i + 1}000.00')
            allocation_objs = create_project_allocation(project, amount)
            setattr(self, f'allocation{i}', allocation_objs.allocation)

            # Create a compute allocation the user.
            allocation_user_objs = \
                create_user_project_allocation(self.user, project, amount)
            setattr(self, f'allocation_user{i}', allocation_user_objs.allocation_user)

            AllocationUserAttribute.objects.create(
                allocation=allocation_objs.allocation,
                allocation_user=allocation_user_objs.allocation_user,
                allocation_attribute_type=AllocationAttributeType.objects.get(name='Cluster Account Status'),
                value='Active')


class TestAccountDeletionRequestRunner(TestAccountDeletionRunnersBase):
    """Testing class for TestAccountDeletionRunnersBase."""

    def setUp(self):
        super().setUp()
        self.runner_class = AccountDeletionRequestRunner

        for name in ['Admin', 'User', 'LastProject', 'BadPID']:
            reason = AccountDeletionRequestReasonChoice.objects.get(name=name)
            setattr(self, f'reason_{name.lower()}', reason)

    def _get_expiration_date(self, reason):
        if reason.name in ['User', 'Admin']:
            expiration_days = \
                import_from_settings('ACCOUNT_DELETION_MANUAL_QUEUE_DAYS')
        else:
            expiration_days = \
                import_from_settings('ACCOUNT_DELETION_AUTO_QUEUE_DAYS')

        return utc_now_offset_aware() + datetime.timedelta(days=expiration_days)

    def test_deletion_request_exists(self):
        """Test that no AccountDeletionRequest is created when one
        already exists."""
        AccountDeletionRequest.objects.create(
            user=self.user,
            reason=self.reason_admin,
            status=AccountDeletionRequestStatusChoice.objects.get(name='Queued'),
            expiration=utc_now_offset_aware())
        self.assertEqual(AccountDeletionRequest.objects.filter(user=self.user).count(), 1)

        runner = self.runner_class(self.user, self.superuser, self.reason_admin)
        runner.run()

        self.assertEqual(AccountDeletionRequest.objects.filter(user=self.user).count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_deletion_request_created(self):
        """Test that the runner correctly creates the AccountDeletionRequest."""
        self.assertFalse(AccountDeletionRequest.objects.filter(user=self.user).exists())

        pre_time = self._get_expiration_date(self.reason_admin)

        runner = self.runner_class(self.user, self.superuser, self.reason_admin)
        runner.run()

        post_time = self._get_expiration_date(self.reason_admin)

        requests = AccountDeletionRequest.objects.filter(
            user=self.user,
            reason=self.reason_admin,
            status__name='Queued')

        self.assertEqual(requests.count(), 1)
        self.assertTrue(pre_time <= requests.first().expiration <= post_time)

    def test_project_removals(self):
        """Test that the runner creates project removal requests if the
        request was created by admins."""

        self.assertFalse(ProjectUserRemovalRequest.objects.all().exists())

        runner = self.runner_class(self.user, self.superuser, self.reason_admin)
        runner.run()

        self.assertEqual(ProjectUserRemovalRequest.objects.all().count(), 3)

        for removal_request in ProjectUserRemovalRequest.objects.all():
            self.assertEqual(removal_request.project_user.user, self.user)
            self.assertEqual(removal_request.requester, self.superuser)
            self.assertEqual(removal_request.status.name, 'Pending')

        # Automatic project removals are only created when an admin
        # creates the account deletion request.
        for reason in [self.reason_user, self.reason_lastproject, self.reason_badpid]:
            AccountDeletionRequest.objects.all().delete()
            ProjectUserRemovalRequest.objects.all().delete()

            runner = self.runner_class(self.user, self.superuser, reason)
            runner.run()

            self.assertFalse(ProjectUserRemovalRequest.objects.all().exists())

    def test_cluster_attributes_set(self):
        """Tests that cluster access attributes are set to Pending - Remove."""

        attributes = AllocationUserAttribute.objects.filter(
            allocation_user__user=self.user,
            allocation_attribute_type__name='Cluster Account Status')
        for attr in attributes:
            self.assertEqual(attr.value, 'Active')

        runner = self.runner_class(self.user, self.superuser, self.reason_admin)
        runner.run()

        for attr in attributes:
            attr.refresh_from_db()
            self.assertEqual(attr.value, 'Pending - Delete')

    def _assert_admin_email(self, request, email):
        email_body = ['There is a new cluster account deletion request '
                      'from User',
                      request.reason.description]

        for section in email_body:
            self.assertIn(section, email.body)
        self.assertEqual(email.to, settings.EMAIL_ADMIN_LIST)
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def _assert_user_email(self, request, email):
        email_body = ['After the request is complete, you will be removed '
                      'from any remaining projects. You will lose access',
                      'If you do not confirm, system administrators may '
                      'delete your data before you have ',
                      'If this is a mistake, or you have any '
                      'questions, please contact us at',
                      request.reason.description]

        for section in email_body:
            self.assertIn(section, email.body)
        self.assertEqual(email.to, [self.user.email])
        self.assertEqual(email.cc, [self.superuser.email])
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def test_emails_sent(self):
        """Test that the correct emails are sent."""

        def _clean_iterations():
            AccountDeletionRequest.objects.all().delete()
            mail.outbox = []

        # Test that emails are sent to both the user and admins
        # with the below reasons.
        for reason in [self.reason_lastproject, self.reason_badpid]:
            _clean_iterations()
            self.assertEqual(len(mail.outbox), 0)

            runner = self.runner_class(self.user, self.superuser, reason)
            runner.run()

            request = AccountDeletionRequest.objects.get(user=self.user)

            self.assertEqual(len(mail.outbox), 2)
            for email in mail.outbox:
                if 'New Cluster Account Deletion Request' in email.subject:
                    self._assert_admin_email(request, email)
                elif 'Cluster Account Deletion Request' in email.subject:
                    self._assert_user_email(request, email)
                else:
                    self.fail('Unknown email sent')

        # Test that emails are sent to only admins when the user
        # requests a deletion.
        reason = self.reason_admin
        _clean_iterations()

        runner = self.runner_class(self.user, self.superuser, reason)
        runner.run()

        request = AccountDeletionRequest.objects.get(user=self.user)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('Cluster Account Deletion Request', email.subject)
        self._assert_user_email(request, email)

        # Test that emails are sent to only users when an admin requests a
        # deletion.
        reason = self.reason_user
        _clean_iterations()

        runner = self.runner_class(self.user, self.superuser, reason)
        runner.run()

        request = AccountDeletionRequest.objects.get(user=self.user)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('New Cluster Account Deletion Request', email.subject)
        self._assert_admin_email(request, email)
