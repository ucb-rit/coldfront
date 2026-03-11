"""Unit and component tests for SecureDirRequestReviewMOUView.

Component tests for secure directory MOU review view's email
sending functionality.

Unit tests for the _conditionally_send_ready_for_processing_email()
method.
"""

import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.contrib.auth import get_user_model

from coldfront.core.allocation.models import (
    SecureDirRequest, SecureDirRequestStatusChoice,
)
from coldfront.core.project.models import (
    Project, ProjectStatusChoice, ProjectUser,
    ProjectUserStatusChoice, ProjectUserRoleChoice,
)
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware
from flags.state import enable_flag

User = get_user_model()


@pytest.fixture
def superuser(db):
    """Create a superuser for testing."""
    user = User.objects.create_superuser(
        username='admin',
        email='admin@test.com'
    )
    user.set_password('adminpass')
    user.save()
    return user


@pytest.fixture
def pi(db):
    """Create a PI user for testing."""
    pi_user = User.objects.create_user(
        username='pi',
        email='pi@test.com'
    )
    pi_user.set_password('pipass')
    pi_user.save()
    user_profile = UserProfile.objects.get(user=pi_user)
    user_profile.is_pi = True
    user_profile.save()
    return pi_user


@pytest.fixture
def project(db):
    """Create a project for testing."""
    project_status = ProjectStatusChoice.objects.get(
        name='Active'
    )
    return Project.objects.create(
        name='test_project',
        status=project_status
    )


@pytest.fixture
def project_with_pi(db, pi, project):
    """Add PI to project."""
    project_user_status = ProjectUserStatusChoice.objects.get(
        name='Active'
    )
    pi_role = ProjectUserRoleChoice.objects.get(
        name='Principal Investigator'
    )
    ProjectUser.objects.create(
        user=pi,
        project=project,
        role=pi_role,
        status=project_user_status,
        enable_notifications=True
    )
    return project


def _create_secure_dir_request(
    db,
    project,
    requester,
    pi,
    rdm_consultation_status='Pending'
):
    """Helper to create a SecureDirRequest.

    Args:
        db: pytest database fixture
        project: Project object
        requester: User object for the requester
        pi: User object for the PI
        rdm_consultation_status: Initial RDM consultation status
    """
    request_obj = SecureDirRequest.objects.create(
        directory_name='test_dir',
        requester=requester,
        pi=pi,
        data_description='a' * 20,
        project=project,
        status=SecureDirRequestStatusChoice.objects.get(
            name='Under Review'
        ),
        request_time=utc_now_offset_aware()
    )

    # Initialize state with all required keys
    request_obj.state = {
        'rdm_consultation': {
            'status': rdm_consultation_status,
            'justification': '',
            'timestamp': ''
        },
        'notified': {
            'status': 'Pending',
            'timestamp': ''
        },
        'mou': {
            'status': 'Pending',
            'justification': '',
            'timestamp': ''
        },
        'setup': {
            'status': 'Pending',
            'justification': '',
            'timestamp': ''
        },
        'other': {
            'justification': '',
            'timestamp': ''
        }
    }
    request_obj.save()
    return request_obj


@pytest.mark.django_db
class TestSecureDirRequestReviewMOUViewEmailSending:
    """Test email sending in SecureDirRequestReviewMOUView."""

    @pytest.fixture(autouse=True)
    def setup(self, db, superuser, pi, project_with_pi):
        """Set up test fixtures."""
        enable_flag('SECURE_DIRS_REQUESTABLE')
        self.superuser = superuser
        self.pi = pi
        self.project = project_with_pi

    @pytest.fixture
    def secure_dir_request_for_mou(self):
        """Request with RDM consultation already approved."""
        return _create_secure_dir_request(
            None,
            self.project,
            self.pi,
            self.pi,
            rdm_consultation_status='Approved'
        )

    def test_email_sent_when_mou_approved(
        self, client, secure_dir_request_for_mou
    ):
        """Email sent to admins when MOU is approved."""
        with patch(
            'coldfront.core.allocation.views_.'
            'secure_dir_views.new_directory.approval_views.'
            'send_secure_directory_request_ready_for_processing_email'
        ) as mock_send:
            client.force_login(self.superuser)
            url = reverse(
                'secure-dir-request-review-mou',
                kwargs={'pk': secure_dir_request_for_mou.pk}
            )
            data = {
                'status': 'Approved',
                'justification': 'Test justification'
            }
            response = client.post(url, data)

            # Verify redirect
            success_url = reverse(
                'secure-dir-request-detail',
                kwargs={'pk': secure_dir_request_for_mou.pk}
            )
            assert response.status_code == 302
            assert response.url == success_url

            # Verify request status updated
            secure_dir_request_for_mou.refresh_from_db()
            assert (
                secure_dir_request_for_mou.status.name ==
                'Approved - Processing'
            )

            # Verify email sent
            mock_send.assert_called_once_with(
                secure_dir_request_for_mou
            )

    def test_email_not_sent_if_rdm_pending(
        self, client, superuser, pi, project_with_pi
    ):
        """Email not sent if RDM consultation still pending."""
        # Create request with RDM consultation pending
        request_obj = _create_secure_dir_request(
            None,
            project_with_pi,
            pi,
            pi,
            rdm_consultation_status='Pending'
        )

        with patch(
            'coldfront.core.allocation.views_.'
            'secure_dir_views.new_directory.approval_views.'
            'send_secure_directory_request_ready_for_processing_email'
        ) as mock_send:
            client.force_login(superuser)
            url = reverse(
                'secure-dir-request-review-mou',
                kwargs={'pk': request_obj.pk}
            )
            data = {
                'status': 'Approved',
                'justification': 'Test justification'
            }
            response = client.post(url, data)

            # Status should remain 'Under Review' (not
            # 'Approved - Processing') because RDM is still pending
            request_obj.refresh_from_db()
            assert request_obj.status.name == 'Under Review'

            # Email should NOT be sent
            mock_send.assert_not_called()

    def test_email_not_sent_if_denied(
        self, client, superuser, pi, project_with_pi
    ):
        """Email not sent if MOU is denied."""
        # Create request with RDM consultation approved
        request_obj = _create_secure_dir_request(
            None,
            project_with_pi,
            pi,
            pi,
            rdm_consultation_status='Approved'
        )

        with patch(
            'coldfront.core.allocation.views_.'
            'secure_dir_views.new_directory.approval_views.'
            'send_secure_directory_request_ready_for_processing_email'
        ) as mock_send:
            client.force_login(superuser)
            url = reverse(
                'secure-dir-request-review-mou',
                kwargs={'pk': request_obj.pk}
            )
            data = {
                'status': 'Denied',
                'justification': 'Test denial'
            }
            response = client.post(url, data)

            # Status should be 'Denied' (not 'Approved - Processing')
            request_obj.refresh_from_db()
            assert request_obj.status.name == 'Denied'

            # Email should NOT be sent
            mock_send.assert_not_called()

    def test_permission_required(
        self, client, pi, secure_dir_request_for_mou
    ):
        """Only superusers can access MOU review view."""
        client.force_login(pi)
        url = reverse(
            'secure-dir-request-review-mou',
            kwargs={'pk': secure_dir_request_for_mou.pk}
        )
        response = client.get(url)
        assert response.status_code == 403


@pytest.mark.unit
class TestSecureDirRequestMixinEmailMethod:
    """Unit tests for
    _conditionally_send_ready_for_processing_email()."""

    @patch(
        'coldfront.core.allocation.views_.'
        'secure_dir_views.new_directory.approval_views.'
        'send_secure_directory_request_ready_for_processing_email'
    )
    def test_sends_email_if_status_is_approved_processing(
        self, mock_send
    ):
        """Email sent when status is Approved - Processing."""
        from coldfront.core.allocation.views_\
            .secure_dir_views.new_directory.approval_views\
            import SecureDirRequestReviewMOUView

        view = SecureDirRequestReviewMOUView()
        view.request_obj = MagicMock()
        view.request_obj.status.name = 'Approved - Processing'

        view._conditionally_send_ready_for_processing_email()

        mock_send.assert_called_once_with(view.request_obj)

    @patch(
        'coldfront.core.allocation.views_.'
        'secure_dir_views.new_directory.approval_views.'
        'logger'
    )
    @patch(
        'coldfront.core.allocation.views_.'
        'secure_dir_views.new_directory.approval_views.'
        'send_secure_directory_request_ready_for_processing_email'
    )
    def test_handles_email_send_exception_gracefully(
        self, mock_send, mock_logger
    ):
        """Exceptions during email send are logged."""
        from coldfront.core.allocation.views_\
            .secure_dir_views.new_directory.approval_views\
            import SecureDirRequestReviewMOUView

        view = SecureDirRequestReviewMOUView()
        view.request_obj = MagicMock()
        view.request_obj.status.name = 'Approved - Processing'

        test_exception = ValueError('Test error')
        mock_send.side_effect = test_exception

        # Should not raise, but log the exception
        view._conditionally_send_ready_for_processing_email()

        mock_logger.exception.assert_called_once()

    @pytest.mark.parametrize('status_name', [
        'Under Review',
        'Approved - Complete',
        'Denied'
    ])
    @patch(
        'coldfront.core.allocation.views_.'
        'secure_dir_views.new_directory.approval_views.'
        'send_secure_directory_request_ready_for_processing_email'
    )
    def test_does_not_send_email_for_non_processing_statuses(
        self, mock_send, status_name
    ):
        """Email not sent for statuses other than
        Approved - Processing."""
        from coldfront.core.allocation.views_\
            .secure_dir_views.new_directory.approval_views\
            import SecureDirRequestReviewMOUView

        view = SecureDirRequestReviewMOUView()
        view.request_obj = MagicMock()
        view.request_obj.status.name = status_name

        view._conditionally_send_ready_for_processing_email()

        mock_send.assert_not_called()
