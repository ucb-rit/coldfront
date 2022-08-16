import datetime

from django.core import mail
from flags.state import enable_flag

from coldfront.config import settings
from coldfront.core.allocation.models import \
    AccountDeletionRequestReasonChoice, \
    AccountDeletionRequestStatusChoice, AccountDeletionRequest, \
    AllocationUserAttribute, AllocationUser, AllocationUserStatusChoice
from coldfront.core.allocation.tests.test_account_deletion_base import \
    TestAccountDeletionBase
from coldfront.core.allocation.utils_.account_deletion_utils import \
    AccountDeletionRequestRunner, AccountDeletionRequestCompleteRunner
from coldfront.core.allocation.utils_.secure_dir_utils import create_secure_dirs
from coldfront.core.project.models import ProjectUser, ProjectUserRemovalRequest
from coldfront.core.utils.common import utc_now_offset_aware, \
    import_from_settings


class TestAccountDeletionRequestRunner(TestAccountDeletionBase):
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


class TestAccountDeletionRequestCompleteRunner(TestAccountDeletionBase):
    """Testing class for AccountDeletionRequestCompleteRunner."""

    def setUp(self):
        super().setUp()
        self.runner_class = AccountDeletionRequestCompleteRunner

        self.request = AccountDeletionRequest.objects.create(
            user=self.user,
            status=AccountDeletionRequestStatusChoice.objects.get(name='Processing'),
            reason=AccountDeletionRequestReasonChoice.objects.get(name='Admin'),
            expiration=utc_now_offset_aware())

        self.complete_request_checklist()

        ProjectUser.objects.all().delete()

    def test_status_set(self):
        """Tests that the request status is updated."""
        self.assertEqual(self.request.status.name, 'Processing')
        runner = self.runner_class(self.request)
        runner.run()
        self.request.refresh_from_db()
        self.assertEqual(self.request.status.name, 'Complete')

    def test_set_userprofile_values(self):
        """Tests that the runner sets the correct userprofile values."""
        user_profile = self.user.userprofile
        self.assertFalse(user_profile.is_deleted)
        self.assertIsNotNone(user_profile.billing_activity)
        self.assertIsNotNone(user_profile.cluster_uid)

        runner = self.runner_class(self.request)
        runner.run()

        user_profile.refresh_from_db()
        self.assertTrue(user_profile.is_deleted)
        self.assertIsNone(user_profile.billing_activity)
        self.assertIsNone(user_profile.cluster_uid)

    def test_set_cluster_access_attributes(self):
        """Tests that cluster access attributes are set correctly."""
        attributes = AllocationUserAttribute.objects.filter(
            allocation_user__user=self.user,
            allocation_attribute_type__name='Cluster Account Status')
        for attr in attributes:
            self.assertEqual(attr.value, 'Active')

        runner = self.runner_class(self.request)
        runner.run()

        for attr in attributes:
            attr.refresh_from_db()
            self.assertEqual(attr.value, 'Removed')

    def test_remove_remaining_allocations(self):
        """Tests that the user is removed from allocations."""
        alloc_users = AllocationUser.objects.filter(user=self.user)
        for alloc_user in alloc_users:
            self.assertEqual(alloc_user.status.name, 'Active')

        runner = self.runner_class(self.request)
        runner.run()

        alloc_users = AllocationUser.objects.filter(user=self.user)
        for alloc_user in alloc_users:
            self.assertEqual(alloc_user.status.name, 'Removed')

    def test_remove_secure_directories(self):
        """Tests that the user is removed from any secure directories."""
        enable_flag('SECURE_DIRS_REQUESTABLE')

        # Create secure directories.
        groups_allocation = \
            create_secure_dirs(self.project0, 'test', 'groups')
        scratch_allocation = \
            create_secure_dirs(self.project0, 'test', 'scratch')

        # Add user to the secure directories.
        active_status = AllocationUserStatusChoice.objects.get(name='Active')
        groups_alloc_user = AllocationUser.objects.create(
            user=self.user,
            allocation=groups_allocation,
            status=active_status)
        scratch_alloc_user = AllocationUser.objects.create(
            user=self.user,
            allocation=scratch_allocation,
            status=active_status)

        alloc_users = AllocationUser.objects.filter(
            user=self.user,
            status__name='Active',
            allocation__resources__name__icontains='Directory')
        self.assertEqual(alloc_users.count(), 2)

        runner = self.runner_class(self.request)
        runner.run()

        groups_alloc_user.refresh_from_db()
        scratch_alloc_user.refresh_from_db()
        self.assertEqual(groups_alloc_user.status.name, 'Removed')
        self.assertEqual(scratch_alloc_user.status.name, 'Removed')

        alloc_users = AllocationUser.objects.filter(
            user=self.user,
            status__name='Active',
            allocation__resources__name__icontains='Directory')
        self.assertFalse(alloc_users.exists())

    def test_emails_sent(self):
        self.assertEqual(len(mail.outbox), 0)

        runner = self.runner_class(self.request)
        runner.run()

        request = AccountDeletionRequest.objects.get(user=self.user)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        email_body = ['The request to delete your cluster account '
                      'was completed successfully.',
                      'You were removed from any remaining projects. '
                      'Your cluster access was revoked, meaning you will '
                      'no longer be able to login to the clusters. '
                      'Additionally, all of your data in your \'home\' '
                      'and \'scratch\' directories was deleted.',
                      'If this is a mistake, or you have any '
                      'questions, please contact us at',
                      request.reason.description]

        for section in email_body:
            self.assertIn(section, email.body)
        self.assertIn('Cluster Account Deletion Request Complete',
                      email.subject)
        self.assertEqual(email.to, [self.user.email])
        self.assertEqual(email.cc, [self.superuser.email])
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)
