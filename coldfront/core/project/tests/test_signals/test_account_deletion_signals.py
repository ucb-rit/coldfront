from coldfront.core.allocation.models import AccountDeletionRequest, \
    AccountDeletionRequestStatusChoice, AccountDeletionRequestReasonChoice
from coldfront.core.project.models import ProjectStatusChoice, \
    ProjectUserRoleChoice, ProjectUserStatusChoice, Project, ProjectUser, \
    ProjectUserJoinRequest, SavioProjectAllocationRequest, \
    ProjectAllocationRequestStatusChoice, VectorProjectAllocationRequest
from coldfront.core.utils.common import utc_now_offset_aware

from coldfront.core.utils.tests.test_base import TestBase


class TestAccountDeletionSignals(TestBase):
    """Test that AccountDeletionRequests are created and cancelled
    when certain project related events occur."""

    def setUp(self):
        super().setUp()

        self.create_test_user()
        self.project = Project.objects.create(
            name='project',
            status=ProjectStatusChoice.objects.get(name='Active'))

    def _create_account_deletion_request(self, status, reason):
        request = AccountDeletionRequest.objects.create(
            user=self.user,
            status=AccountDeletionRequestStatusChoice.objects.get(name=status),
            reason=AccountDeletionRequestReasonChoice.objects.get(name=reason),
            expiration=utc_now_offset_aware())
        return request

    def _clean_previous_iteration(self, model):
        AccountDeletionRequest.objects.all().delete()
        model.objects.all().delete()
        self.assertFalse(AccountDeletionRequest.objects.all().exists())
        self.assertFalse(model.objects.all().exists())

    def _assert_request_cancelled(self, justification):
        request = AccountDeletionRequest.objects.get(user=self.user)
        self.assertEqual(request.status.name, 'Cancelled')
        self.assertEqual(request.state['other']['justification'], justification)

    def test_auto_account_deletion_project_removal(self):
        """Tests functionality of account_deletion_project_user.
        An AccountDeletionRequest should be created when a
        ProjectUserRemovalRequest is completed and the user is not
        apart of any other projects."""
        user_status = \
            ProjectUserStatusChoice.objects.get(name='Active')
        user_role = ProjectUserRoleChoice.objects.get(name='User')
        project_user = ProjectUser.objects.create(
            user=self.user,
            project=self.project,
            status=user_status,
            role=user_role)

        for status in ['Active', 'Pending - Add', 'Pending - Remove']:
            project_user.status = ProjectUserStatusChoice.objects.get(name=status)
            project_user.save()

            # No requests should exist yet.
            requests = AccountDeletionRequest.objects.filter(
                user=self.user,
                status__name='Queued',
                reason__name='LastProject')
            self.assertFalse(requests.exists())

        # Removing the user from their last project.
        project_user.status = ProjectUserStatusChoice.objects.get(name='Removed')
        project_user.save()

        # AccountDeletionRequest should exist now.
        project_users = ProjectUser.objects.filter(
            user=self.user,
            status__name__in=['Active',
                              'Pending - Add',
                              'Pending - Remove'])
        self.assertFalse(project_users.exists())

        requests = AccountDeletionRequest.objects.filter(
            user=self.user,
            status__name='Queued',
            reason__name='LastProject')
        self.assertTrue(requests.exists())
        self.assertEqual(requests.count(), 1)

    def test_cancel_account_deletion_project_user(self):
        """Tests functionality of account_deletion_project_user.
        An AccountDeletionRequest should be cancelled when new ProjectUser
        is created if the AccountDeletionRequest is Queued or Ready and has
        reason = LastProject."""

        user_status = \
            ProjectUserStatusChoice.objects.get(name='Active')
        user_role = ProjectUserRoleChoice.objects.get(name='User')

        # AccountDeletionRequests should be cancelled under these
        # statuses and reasons.
        for status in ['Queued', 'Ready']:
            for reason in ['LastProject']:
                # Clean up from the last iteration.
                self._clean_previous_iteration(ProjectUser)

                request = self._create_account_deletion_request(status, reason)
                self.assertEqual(request.status.name, status)

                ProjectUser.objects.create(
                    user=self.user,
                    project=self.project,
                    status=user_status,
                    role=user_role)

                request.refresh_from_db()
                justification = f'User joined project {self.project.name}.'
                self._assert_request_cancelled(justification)

        # AccountDeletionRequests should not be cancelled under these
        # statuses and reasons.
        for status in ['Processing', 'Complete']:
            for reason in ['User', 'Admin', 'BadPID']:
                # Clean up from the last iteration.
                self._clean_previous_iteration(ProjectUser)

                request = self._create_account_deletion_request(status, reason)
                self.assertEqual(request.status.name, status)

                ProjectUser.objects.create(
                    user=self.user,
                    project=self.project,
                    status=user_status,
                    role=user_role)

                request.refresh_from_db()
                self.assertEqual(request.status.name, status)

    def test_cancel_account_deletion_project_user_join_request(self):
        """Test functionality of 
        cancel_account_deletion_project_user_join_request. 
        An AccountDeletionRequest should be cancelled when new 
        ProjectUserJoinRequest is created if the AccountDeletionRequest 
        is Queued or Ready and has reason = LastProject."""

        user_status = \
            ProjectUserStatusChoice.objects.get(name='Pending - Add')
        user_role = ProjectUserRoleChoice.objects.get(name='User')

        project_user = ProjectUser.objects.create(
            user=self.user,
            project=self.project,
            status=user_status,
            role=user_role)
        
        # AccountDeletionRequests should be cancelled under these
        # statuses and reasons.
        for status in ['Queued', 'Ready']:
            for reason in ['LastProject']:
                # Clean up from the last iteration.
                self._clean_previous_iteration(ProjectUserJoinRequest)

                request = self._create_account_deletion_request(status, reason)
                self.assertEqual(request.status.name, status)

                ProjectUserJoinRequest.objects.create(
                    project_user=project_user,
                    reason='This is a test reason.')

                request.refresh_from_db()
                justification = f'User requested to join project ' \
                                f'{self.project.name}.'
                self._assert_request_cancelled(justification)

        # AccountDeletionRequests should not be cancelled under these
        # statuses and reasons.
        for status in ['Processing', 'Complete']:
            for reason in ['User', 'Admin', 'BadPID']:
                # Clean up from the last iteration.
                self._clean_previous_iteration(ProjectUserJoinRequest)

                request = self._create_account_deletion_request(status, reason)
                self.assertEqual(request.status.name, status)

                ProjectUserJoinRequest.objects.create(
                    project_user=project_user,
                    reason='This is a test reason.')

                request.refresh_from_db()
                self.assertEqual(request.status.name, status)

    def test_cancel_account_deletion_savio_project_request(self):
        """Test functionality of
        test_cancel_account_deletion_savio_project_request. An
        AccountDeletionRequest should be cancelled when new
        SavioProjectAllocationRequest is created if the AccountDeletionRequest
        is Queued or Ready and has reason = LastProject."""

        proj_request_status = \
            ProjectAllocationRequestStatusChoice.objects.get(name='Under Review')

        # AccountDeletionRequests should be cancelled under these
        # statuses and reasons.
        for status in ['Queued', 'Ready']:
            for reason in ['LastProject']:
                # Clean up from the last iteration.
                self._clean_previous_iteration(SavioProjectAllocationRequest)

                request = self._create_account_deletion_request(status, reason)
                self.assertEqual(request.status.name, status)

                SavioProjectAllocationRequest.objects.create(
                    requester=self.user,
                    pi=self.user,
                    project=self.project,
                    status=proj_request_status,
                    survey_answers={})

                request.refresh_from_db()
                justification = f'User requested to create project ' \
                                f'{self.project.name}.'
                self._assert_request_cancelled(justification)

        # AccountDeletionRequests should not be cancelled under these
        # statuses and reasons.
        for status in ['Processing', 'Complete']:
            for reason in ['User', 'Admin', 'BadPID']:
                # Clean up from the last iteration.
                self._clean_previous_iteration(SavioProjectAllocationRequest)

                request = self._create_account_deletion_request(status, reason)
                self.assertEqual(request.status.name, status)

                SavioProjectAllocationRequest.objects.create(
                    requester=self.user,
                    pi=self.user,
                    project=self.project,
                    status=proj_request_status,
                    survey_answers={})

                request.refresh_from_db()
                self.assertEqual(request.status.name, status)

    def test_cancel_account_deletion_vector_project_request(self):
        """Test functionality of
        cancel_account_deletion_vector_project_request. An
        AccountDeletionRequest should be cancelled when new
        VectorProjectAllocationRequest is created if the AccountDeletionRequest
        is Queued or Ready and has reason = LastProject."""

        proj_request_status = \
            ProjectAllocationRequestStatusChoice.objects.get(name='Under Review')

        # AccountDeletionRequests should be cancelled under these
        # statuses and reasons.
        for status in ['Queued', 'Ready']:
            for reason in ['LastProject']:
                # Clean up from the last iteration.
                self._clean_previous_iteration(VectorProjectAllocationRequest)

                request = self._create_account_deletion_request(status, reason)
                self.assertEqual(request.status.name, status)

                VectorProjectAllocationRequest.objects.create(
                    requester=self.user,
                    pi=self.user,
                    project=self.project,
                    status=proj_request_status)

                request.refresh_from_db()
                justification = f'User requested to create vector project ' \
                                f'{self.project.name}.'
                self._assert_request_cancelled(justification)

        # AccountDeletionRequests should not be cancelled under these
        # statuses and reasons.
        for status in ['Processing', 'Complete']:
            for reason in ['User', 'Admin', 'BadPID']:
                # Clean up from the last iteration.
                self._clean_previous_iteration(VectorProjectAllocationRequest)

                request = self._create_account_deletion_request(status, reason)
                self.assertEqual(request.status.name, status)

                VectorProjectAllocationRequest.objects.create(
                    requester=self.user,
                    pi=self.user,
                    project=self.project,
                    status=proj_request_status)

                request.refresh_from_db()
                self.assertEqual(request.status.name, status)