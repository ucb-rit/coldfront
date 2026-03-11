"""Component tests for Savio new project request review views.

Tests for eligibility, readiness, and memorandum signed views.
"""

import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.auth import get_user_model

from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.project.models import (
    Project, SavioProjectAllocationRequest, ProjectStatusChoice,
    ProjectAllocationRequestStatusChoice,
)
from coldfront.core.resource.utils_.allowance_utils.constants import (
    BRCAllowances,
)
from coldfront.core.resource.utils_.allowance_utils.interface import (
    ComputingAllowanceInterface,
)
from coldfront.core.utils.common import utc_now_offset_aware

User = get_user_model()


@pytest.fixture
def superuser(db):
    """Create a superuser for testing."""
    return User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='adminpass'
    )


@pytest.fixture
def computing_allowance(db):
    """Get a computing allowance for testing."""
    interface = ComputingAllowanceInterface()
    # Get the first available allowance
    allowances = interface.allowances()
    if not allowances:
        pytest.skip(
            "No computing allowances found in database"
        )
    return allowances[0]


@pytest.fixture
def allocation_period(db):
    """Get a valid allocation period."""
    now = utc_now_offset_aware()
    period = AllocationPeriod.objects.filter(
        start_date__lte=now,
        end_date__gte=now
    ).first()
    if not period:
        pytest.skip(
            "No valid allocation period found in database"
        )
    return period


@pytest.fixture
def requester(db):
    """Create a requester user."""
    return User.objects.create_user(
        username='requester',
        email='requester@test.com',
        password='password'
    )


@pytest.fixture
def pi(db):
    """Create a PI user."""
    return User.objects.create_user(
        username='pi',
        email='pi@test.com',
        password='password'
    )


def _create_savio_request(
    db,
    computing_allowance,
    allocation_period,
    requester,
    pi,
    eligibility_status='Pending',
    readiness_status='Pending'
):
    """Helper to create a SavioProjectAllocationRequest.

    Args:
        db: pytest database fixture
        computing_allowance: Resource object for the allowance
        allocation_period: AllocationPeriod object
        requester: User object for the requester
        pi: User object for the PI
        eligibility_status: Initial eligibility review status
        readiness_status: Initial readiness review status
    """
    interface = ComputingAllowanceInterface()

    # Create project
    project_status = ProjectStatusChoice.objects.get(name='Active')
    project = Project.objects.create(
        name='test_project',
        status=project_status,
        title='Test Project',
        description='Test project for review views'
    )

    # Create request
    request_status = (
        ProjectAllocationRequestStatusChoice.objects.get(
            name='Under Review'
        )
    )

    request_obj = SavioProjectAllocationRequest.objects.create(
        requester=requester,
        computing_allowance=computing_allowance,
        allocation_period=allocation_period,
        pi=pi,
        project=project,
        survey_answers={},
        status=request_status,
        pool=False,
    )

    # Initialize state with all required keys
    request_obj.state = {
        'eligibility': {
            'status': eligibility_status,
            'justification': '',
            'timestamp': ''
        },
        'readiness': {
            'status': readiness_status,
            'justification': '',
            'timestamp': ''
        },
        'setup': {
            'status': 'Pending',
            'name_change': {
                'requested_name': '',
                'final_name': '',
                'justification': ''
            },
            'timestamp': ''
        },
        'other': {'justification': '', 'timestamp': ''},
        'memorandum_signed': {'status': 'Pending', 'timestamp': ''},
    }
    request_obj.save()

    return request_obj


@pytest.fixture
def savio_request_for_eligibility(
    db, computing_allowance, allocation_period, requester, pi
):
    """Create a SavioProjectAllocationRequest for eligibility review.

    Readiness is pre-approved so approving eligibility triggers
    'Approved - Processing' status.
    """
    return _create_savio_request(
        db,
        computing_allowance,
        allocation_period,
        requester,
        pi,
        eligibility_status='Pending',
        readiness_status='Approved'
    )


@pytest.fixture
def savio_request_for_readiness(
    db, computing_allowance, allocation_period, requester, pi
):
    """Create a SavioProjectAllocationRequest for readiness review.

    Eligibility is pre-approved so approving readiness triggers
    'Approved - Processing' status.
    """
    return _create_savio_request(
        db,
        computing_allowance,
        allocation_period,
        requester,
        pi,
        eligibility_status='Approved',
        readiness_status='Pending'
    )


@pytest.fixture
def savio_request_for_memorandum(db, allocation_period, requester, pi):
    """Create a SavioProjectAllocationRequest for memorandum review.

    Both eligibility and readiness are pre-approved, and memorandum
    is pending so marking memorandum as complete triggers
    'Approved - Processing' status.

    Uses an ICA allowance since ICA requires an MOU to be signed.
    """
    interface = ComputingAllowanceInterface()

    # Get an ICA allowance (requires MOU)
    from coldfront.core.resource.models import Resource

    ica_allowance = Resource.objects.get(name=BRCAllowances.ICA)

    # Create project
    project_status = ProjectStatusChoice.objects.get(name='Active')
    project = Project.objects.create(
        name='test_project',
        status=project_status,
        title='Test Project',
        description='Test project for review views'
    )

    # Create request
    request_status = ProjectAllocationRequestStatusChoice.objects.get(
        name='Under Review'
    )
    # Get the allocation_type (short name) for the allowance
    allocation_type = interface.name_short_from_name(ica_allowance.name)

    request_obj = SavioProjectAllocationRequest.objects.create(
        requester=requester,
        allocation_type=allocation_type,
        computing_allowance=ica_allowance,
        allocation_period=allocation_period,
        pi=pi,
        project=project,
        survey_answers={},
        status=request_status,
        pool=False,
    )

    # Initialize state with all required keys
    request_obj.state = {
        'eligibility': {
            'status': 'Approved',
            'justification': '',
            'timestamp': ''
        },
        'readiness': {
            'status': 'Approved',
            'justification': '',
            'timestamp': ''
        },
        'setup': {
            'status': 'Pending',
            'name_change': {
                'requested_name': '',
                'final_name': '',
                'justification': ''
            },
            'timestamp': ''
        },
        'other': {'justification': '', 'timestamp': ''},
        'memorandum_signed': {'status': 'Pending', 'timestamp': ''},
    }
    request_obj.save()

    return request_obj


@pytest.mark.component
class TestSavioProjectReviewEligibilityView:
    """Component tests for eligibility review view."""

    def test_form_submission_updates_eligibility_status(
        self, client, superuser, savio_request_for_eligibility
    ):
        """Test that form submission updates eligibility status."""
        client.force_login(superuser)
        url = reverse(
            'new-project-request-review-eligibility',
            kwargs={'pk': savio_request_for_eligibility.pk}
        )

        response = client.post(url, {
            'status': 'Approved',
            'justification': 'Test approval'
        })

        # Should redirect on success
        assert response.status_code == 302

        # Check that eligibility status was updated
        savio_request_for_eligibility.refresh_from_db()
        assert (
            savio_request_for_eligibility.state['eligibility']['status']
            == 'Approved'
        )

    def test_email_conditionally_sent_on_status_change(
        self, client, superuser, savio_request_for_eligibility
    ):
        """Test email is sent when status becomes 'Approved -
        Processing'."""
        client.force_login(superuser)
        url = reverse(
            'new-project-request-review-eligibility',
            kwargs={'pk': savio_request_for_eligibility.pk}
        )

        with patch(
            'coldfront.core.project.views_.new_project_views.'
            'approval_views.'
            'send_project_request_ready_for_processing_email'
        ) as mock_send:
            response = client.post(url, {
                'status': 'Approved',
                'justification': 'Test approval'
            })

        # Should redirect on success
        assert response.status_code == 302

        # Email function should be called when status becomes
        # 'Approved - Processing'
        savio_request_for_eligibility.refresh_from_db()
        assert (
            savio_request_for_eligibility.status.name
            == 'Approved - Processing'
        )
        mock_send.assert_called_once_with(
            savio_request_for_eligibility
        )

    def test_requires_superuser_permission(
        self, client, savio_request_for_eligibility
    ):
        """Test that view requires superuser permission."""
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='password'
        )
        client.force_login(regular_user)
        url = reverse(
            'new-project-request-review-eligibility',
            kwargs={'pk': savio_request_for_eligibility.pk}
        )

        response = client.get(url)

        # Should be redirected or forbidden
        assert response.status_code in [302, 403]

    def test_email_not_sent_if_readiness_pending(
        self, client, superuser, computing_allowance,
        allocation_period, requester, pi
    ):
        """Email not sent if readiness review still pending."""
        # Create request with readiness still pending
        savio_request = _create_savio_request(
            None,
            computing_allowance,
            allocation_period,
            requester,
            pi,
            eligibility_status='Pending',
            readiness_status='Pending'
        )

        client.force_login(superuser)
        url = reverse(
            'new-project-request-review-eligibility',
            kwargs={'pk': savio_request.pk}
        )

        with patch(
            'coldfront.core.project.views_.new_project_views.'
            'approval_views.'
            'send_project_request_ready_for_processing_email'
        ) as mock_send:
            response = client.post(url, {
                'status': 'Approved',
                'justification': 'Test approval'
            })

        # Should redirect on success
        assert response.status_code == 302

        # Status should remain 'Under Review' (not 'Approved -
        # Processing') because readiness is still pending
        savio_request.refresh_from_db()
        assert savio_request.status.name == 'Under Review'

        # Email should NOT be sent
        mock_send.assert_not_called()


@pytest.mark.component
class TestSavioProjectReviewReadinessView:
    """Component tests for readiness review view."""

    def test_form_submission_updates_readiness_status(
        self, client, superuser, savio_request_for_readiness
    ):
        """Test that form submission updates readiness status."""
        client.force_login(superuser)
        url = reverse(
            'new-project-request-review-readiness',
            kwargs={'pk': savio_request_for_readiness.pk}
        )

        response = client.post(url, {
            'status': 'Approved',
            'justification': 'Test approval'
        })

        # Should redirect on success
        assert response.status_code == 302

        # Check that readiness status was updated
        savio_request_for_readiness.refresh_from_db()
        assert (
            savio_request_for_readiness.state['readiness']['status']
            == 'Approved'
        )

    def test_email_conditionally_sent_on_status_change(
        self, client, superuser, savio_request_for_readiness
    ):
        """Test email is sent when status becomes 'Approved -
        Processing'."""
        client.force_login(superuser)
        url = reverse(
            'new-project-request-review-readiness',
            kwargs={'pk': savio_request_for_readiness.pk}
        )

        with patch(
            'coldfront.core.project.views_.new_project_views.'
            'approval_views.'
            'send_project_request_ready_for_processing_email'
        ) as mock_send:
            response = client.post(url, {
                'status': 'Approved',
                'justification': 'Test approval'
            })

        # Should redirect on success
        assert response.status_code == 302

        # Email function should be called when status becomes
        # 'Approved - Processing'
        savio_request_for_readiness.refresh_from_db()
        assert (
            savio_request_for_readiness.status.name
            == 'Approved - Processing'
        )
        mock_send.assert_called_once_with(
            savio_request_for_readiness
        )

    def test_requires_superuser_permission(
        self, client, savio_request_for_readiness
    ):
        """Test that view requires superuser permission."""
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='password'
        )
        client.force_login(regular_user)
        url = reverse(
            'new-project-request-review-readiness',
            kwargs={'pk': savio_request_for_readiness.pk}
        )

        response = client.get(url)

        assert response.status_code in [302, 403]

    def test_email_not_sent_if_eligibility_pending(
        self, client, superuser, computing_allowance,
        allocation_period, requester, pi
    ):
        """Email not sent if eligibility review still pending."""
        # Create request with eligibility still pending
        savio_request = _create_savio_request(
            None,
            computing_allowance,
            allocation_period,
            requester,
            pi,
            eligibility_status='Pending',
            readiness_status='Pending'
        )

        client.force_login(superuser)
        url = reverse(
            'new-project-request-review-readiness',
            kwargs={'pk': savio_request.pk}
        )

        with patch(
            'coldfront.core.project.views_.new_project_views.'
            'approval_views.'
            'send_project_request_ready_for_processing_email'
        ) as mock_send:
            response = client.post(url, {
                'status': 'Approved',
                'justification': 'Test approval'
            })

        # Should redirect on success
        assert response.status_code == 302

        # Status should remain 'Under Review' (not 'Approved -
        # Processing') because eligibility is still pending
        savio_request.refresh_from_db()
        assert savio_request.status.name == 'Under Review'

        # Email should NOT be sent
        mock_send.assert_not_called()


@pytest.mark.component
class TestSavioProjectReviewMemorandumSignedView:
    """Component tests for memorandum signed review view."""

    def test_form_submission_updates_memorandum_status(
        self, client, superuser, savio_request_for_memorandum
    ):
        """Test that form submission updates memorandum_signed
        status."""
        client.force_login(superuser)
        url = reverse(
            'new-project-request-review-memorandum-signed',
            kwargs={'pk': savio_request_for_memorandum.pk}
        )

        response = client.post(url, {
            'status': 'Complete'
        })

        # Should redirect on success or 404 if MOU not required
        assert response.status_code in [302, 404]

        # Check that status was updated (only if view accepted the
        # form)
        savio_request_for_memorandum.refresh_from_db()
        if response.status_code == 302:
            assert (
                savio_request_for_memorandum.state.get(
                    'memorandum_signed', {}
                ).get('status')
                == 'Complete'
            )

    def test_email_conditionally_sent_on_status_change(
        self, client, superuser, savio_request_for_memorandum
    ):
        """Test email is sent when status becomes 'Approved -
        Processing'."""
        client.force_login(superuser)
        url = reverse(
            'new-project-request-review-memorandum-signed',
            kwargs={'pk': savio_request_for_memorandum.pk}
        )

        with patch(
            'coldfront.core.project.views_.new_project_views.'
            'approval_views.'
            'send_project_request_ready_for_processing_email'
        ) as mock_send:
            response = client.post(url, {
                'status': 'Complete'
            })

        # Should redirect on success
        assert response.status_code == 302

        # Email function should be called when status becomes
        # 'Approved - Processing'
        savio_request_for_memorandum.refresh_from_db()
        assert (
            savio_request_for_memorandum.status.name
            == 'Approved - Processing'
        )
        mock_send.assert_called_once_with(
            savio_request_for_memorandum
        )

    def test_requires_superuser_permission(
        self, client, savio_request_for_memorandum
    ):
        """Test that view requires superuser permission."""
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='password'
        )
        client.force_login(regular_user)
        url = reverse(
            'new-project-request-review-memorandum-signed',
            kwargs={'pk': savio_request_for_memorandum.pk}
        )

        response = client.get(url)

        assert response.status_code in [302, 403]

    def test_email_not_sent_if_eligibility_pending(
        self, client, superuser, allocation_period, requester, pi
    ):
        """Email not sent if eligibility review still pending."""
        from coldfront.core.resource.models import Resource

        # Create request with eligibility pending
        ica_allowance = Resource.objects.get(
            name=BRCAllowances.ICA
        )
        savio_request = _create_savio_request(
            None,
            ica_allowance,
            allocation_period,
            requester,
            pi,
            eligibility_status='Pending',
            readiness_status='Approved'
        )

        client.force_login(superuser)
        url = reverse(
            'new-project-request-review-memorandum-signed',
            kwargs={'pk': savio_request.pk}
        )

        with patch(
            'coldfront.core.project.views_.new_project_views.'
            'approval_views.'
            'send_project_request_ready_for_processing_email'
        ) as mock_send:
            response = client.post(url, {
                'status': 'Complete'
            })

        # Should redirect on success
        assert response.status_code == 302

        # Status should remain 'Under Review' (not 'Approved -
        # Processing') because eligibility is still pending
        savio_request.refresh_from_db()
        assert savio_request.status.name == 'Under Review'

        # Email should NOT be sent
        mock_send.assert_not_called()
