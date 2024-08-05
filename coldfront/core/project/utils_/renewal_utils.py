import gspread

from coldfront.api.statistics.utils import set_project_user_allocation_value
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.request_processing_utils import create_project_users
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.common import project_detail_url
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.common import validate_num_service_units
from coldfront.core.utils.email.email_strategy import validate_email_strategy_or_get_default
from coldfront.core.utils.mail import send_email_template
from collections import namedtuple
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from urllib.parse import urljoin
import logging

from flags.state import flag_enabled
import json


logger = logging.getLogger(__name__)


def get_current_allowance_year_period():
    """Return the AllocationPeriod representing the current allowance
    year, of which there should be exactly one.

    Parameters:
        - None

    Returns:
        - An AllocationPeriod object.

    Raises:
        - AllocationPeriod.DoesNotExist, if no such period is found.
        - AllocationPeriod.MultipleObjectsReturned, if multiple such
          periods are found.
    """
    date = display_time_zone_current_date()
    return AllocationPeriod.objects.get(
        name__startswith='Allowance Year',
        start_date__lte=date,
        end_date__gte=date)


def get_next_allowance_year_period():
    """Return the AllocationPeriod representing the next allowance year,
    of which there should be at most one.

    Parameters:
        - None

    Returns:
        - An AllocationPeriod object, or None.

    Raises:
        - None
    """
    date = display_time_zone_current_date()
    return AllocationPeriod.objects.filter(
        name__startswith='Allowance Year',
        start_date__gt=date).first()


def get_previous_allowance_year_period():
    """Return the AllocationPeriod representing the previous allowance
    year, of which there should be at most one.

    Parameters:
        - None

    Returns:
        - An AllocationPeriod object, or None.

    Raises:
        - None
    """
    date = display_time_zone_current_date()
    allocation_periods = AllocationPeriod.objects.filter(
        name__startswith='Allowance Year',
        end_date__lt=date)
    if not allocation_periods.exists():
        return None
    return allocation_periods.latest('end_date')


def get_pi_active_unique_project(pi_user, computing_allowance,
                                 allocation_period):
    """Given a User object representing a PI, return its active, unique
    Project having the given allowance during the given period.

    The allowance is expected to be one which a PI may have at most one
    of during a single period.

    A Project is considered active during the period if it was exactly
    one of the following: (a) successfully created or (b) successfully
    renewed during the period.

    Parameters:
        - pi_user: A user object.
        - computing_allowance: A ComputingAllowance object.
        - allocation_period: An AllocationPeriod object.

    Raises:
        - AllocationRenewalRequest.MultipleObjectsReturned, if the PI
          has more than one 'Complete' renewal request during the
          current AllocationPeriod.
        - Project.DoesNotExist, if none are found.
        - Project.MultipleObjectsReturned, if multiple are found.
        - SavioProjectAllocationRequest.MultipleObjectsReturned, if the
          PI has more than one 'Approved - Complete' request.
        - Exception, if any other errors occur.
    """
    assert isinstance(pi_user, User)
    assert isinstance(computing_allowance, ComputingAllowance)
    assert isinstance(allocation_period, AllocationPeriod)
    assert computing_allowance.is_one_per_pi()

    project = None

    allowance_name = computing_allowance.get_name()
    allowance_resource = computing_allowance.get_resource()

    # Check AllocationRenewalRequests.
    renewal_request_status = AllocationRenewalRequestStatusChoice.objects.get(
        name='Complete')
    renewal_requests = AllocationRenewalRequest.objects.filter(
        computing_allowance=allowance_resource,
        allocation_period=allocation_period,
        pi=pi_user,
        status=renewal_request_status)
    if renewal_requests.exists():
        if renewal_requests.count() > 1:
            message = (
                f'PI {pi_user.username} unexpectedly has more than one '
                f'completed AllocationRenewalRequest for allowance '
                f'"{allowance_name}" during AllocationPeriod '
                f'"{allocation_period.name}".')
            logger.error(message)
            raise AllocationRenewalRequest.MultipleObjectsReturned(message)
        project = renewal_requests.first().post_project

    # Check new project requests.
    new_project_request_status = \
        ProjectAllocationRequestStatusChoice.objects.get(
            name='Approved - Complete')
    new_project_requests = SavioProjectAllocationRequest.objects.filter(
        computing_allowance=allowance_resource,
        allocation_period=allocation_period,
        pi=pi_user,
        status=new_project_request_status)
    if new_project_requests.exists():
        if new_project_requests.count() > 1:
            message = (
                f'PI {pi_user.username} unexpectedly has more than one '
                f'completed new project request for allowance '
                f'"{allowance_name}" during AllocationPeriod '
                f'"{allocation_period.name}".')
            logger.error(message)
            raise SavioProjectAllocationRequest.MultipleObjectsReturned(
                message)
        # The PI should not have both a completed renewal request and a
        # completed new project request.
        if project:
            message = (
                f'PI {pi_user.username} unexpectedly has both a completed '
                f'AllocationRenewalRequest and a completed new project '
                f'request for allowance "{allowance_name}" during '
                f'AllocationPeriod "{allocation_period.name}".')
            raise Exception(message)
        project = new_project_requests.first().project

    if not project:
        message = (
            f'PI {pi_user.username} has no active Project with allowance '
            f'"{allowance_name}" during AllocationPeriod '
            f'"{allocation_period.name}".')
        raise Project.DoesNotExist(message)

    return project


def has_non_denied_renewal_request(pi, allocation_period):
    """Return whether the given PI User has a non-"Denied"
    AllocationRenewalRequest for the given AllocationPeriod."""
    if not isinstance(pi, User):
        raise TypeError(f'{pi} is not a User object.')
    if not isinstance(allocation_period, AllocationPeriod):
        raise TypeError(
            f'{allocation_period} is not an AllocationPeriod object.')
    status_names = ['Under Review', 'Approved', 'Complete']
    return AllocationRenewalRequest.objects.filter(
        pi=pi,
        allocation_period=allocation_period,
        status__name__in=status_names).exists()


def is_any_project_pi_renewable(project, allocation_period):
    """Return whether the Project has at least one PI who is eligible to
    make an AllocationRenewalRequest during the given
    AllocationPeriod."""
    for pi in project.pis():
        if not has_non_denied_renewal_request(pi, allocation_period):
            return True
    return False


def non_denied_renewal_request_statuses():
    """Return a queryset of AllocationRenewalRequestStatusChoices that
    do not have the name 'Denied'."""
    return AllocationRenewalRequestStatusChoice.objects.filter(
        ~Q(name='Denied'))


def pis_with_renewal_requests_pks(allocation_period, computing_allowance=None,
                                  request_status_names=[]):
    """Return a list of primary keys of PIs of allocation renewal
    requests for the given AllocationPeriod that match the given filters.

    Parameters:
        - allocation_period (AllocationPeriod): The AllocationPeriod to
                                                filter with
        - computing_allowance (Resource): An optional computing
                                          allowance to filter with
        - request_status_names (list[str]): A list of names of request
                                            statuses to filter with

    Returns:
        - A list of integers representing primary keys of matching PIs.

    Raises:
        - AssertionError, if an input has an unexpected type.
        - ComputingAllowanceInterfaceError, if allowance-related values
          cannot be retrieved.
    """
    assert isinstance(allocation_period, AllocationPeriod)
    f = Q(allocation_period=allocation_period)
    if computing_allowance is not None:
        assert isinstance(computing_allowance, Resource)
        interface = ComputingAllowanceInterface()
        project_prefix = interface.code_from_name(computing_allowance.name)
        f = f & Q(post_project__name__startswith=project_prefix)
    if request_status_names:
        f = f & Q(status__name__in=request_status_names)
    return set(
        AllocationRenewalRequest.objects.filter(
            f).values_list('pi__pk', flat=True))


def send_allocation_renewal_request_approval_email(request, num_service_units):
    """Send a notification email to the requester and PI associated with
    the given AllocationRenewalRequest stating that the request has been
    approved, and the given number of service units will be added when
    the request is processed."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = f'{str(request)} Approved'
    template_name = (
        'email/project_renewal/project_renewal_request_approved.txt')

    context = {
        'allocation_period': request.allocation_period,
        'center_name': settings.CENTER_NAME,
        'num_service_units': str(num_service_units),
        'pi_name': f'{request.pi.first_name} {request.pi.last_name}',
        'requested_project_name': request.post_project.name,
        'requested_project_url': project_detail_url(request.post_project),
        'signature': settings.EMAIL_SIGNATURE,
        'support_email': settings.CENTER_HELP_EMAIL,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [request.requester.email, request.pi.email]
    cc = settings.REQUEST_APPROVAL_CC_LIST

    send_email_template(
        subject, template_name, context, sender, receiver_list, cc=cc)


def send_allocation_renewal_request_denial_email(request):
    """Send a notification email to the requester and PI associated with
    the given AllocationRenewalRequest stating that the request has been
    denied."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = f'{str(request)} Denied'
    template_name = 'email/project_renewal/project_renewal_request_denied.txt'
    reason = allocation_renewal_request_denial_reason(request)

    context = {
        'center_name': settings.CENTER_NAME,
        'current_project_name': (
            request.pre_project.name if request.pre_project else 'N/A'),
        'pi_name': f'{request.pi.first_name} {request.pi.last_name}',
        'reason_category': reason.category,
        'reason_justification': reason.justification,
        'requested_project_name': request.post_project.name,
        'signature': settings.EMAIL_SIGNATURE,
        'support_email': settings.CENTER_HELP_EMAIL,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [request.requester.email, request.pi.email]
    cc = settings.REQUEST_APPROVAL_CC_LIST

    send_email_template(
        subject, template_name, context, sender, receiver_list, cc=cc)


def send_allocation_renewal_request_processing_email(request,
                                                     num_service_units):
    """Send a notification email to the requester and PI associated with
    the given AllocationRenewalRequest stating that the request has been
    processed, and the given number of service units have been added."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = f'{str(request)} Processed'
    template_name = (
        'email/project_renewal/project_renewal_request_processed.txt')

    context = {
        'center_name': settings.CENTER_NAME,
        'num_service_units': str(num_service_units),
        'pi_name': f'{request.pi.first_name} {request.pi.last_name}',
        'requested_project_name': request.post_project.name,
        'requested_project_url': project_detail_url(request.post_project),
        'signature': settings.EMAIL_SIGNATURE,
        'support_email': settings.CENTER_HELP_EMAIL,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [request.requester.email, request.pi.email]
    cc = settings.REQUEST_APPROVAL_CC_LIST

    send_email_template(
        subject, template_name, context, sender, receiver_list, cc=cc)


def send_new_allocation_renewal_request_admin_notification_email(request):
    """Send an email to admins notifying them of a new
    AllocationRenewalRequest."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = 'New Allocation Renewal Request'
    template_name = (
        'email/project_renewal/admins_new_project_renewal_request.txt')

    requester = request.requester
    requester_str = (
        f'{requester.first_name} {requester.last_name} ({requester.email})')

    pi = request.pi
    pi_str = f'{pi.first_name} {pi.last_name} ({pi.email})'

    detail_view_name = 'pi-allocation-renewal-request-detail'
    review_url = urljoin(
        settings.CENTER_BASE_URL,
        reverse(detail_view_name, kwargs={'pk': request.pk}))

    context = {
        'pi_str': pi_str,
        'requester_str': requester_str,
        'review_url': review_url,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = settings.EMAIL_ADMIN_LIST

    send_email_template(subject, template_name, context, sender, receiver_list)


def send_new_allocation_renewal_request_pi_notification_email(request):
    """Send an email to the PI of the given request notifying them that
    someone has made a new AllocationRenewalRequest under their name.

    It is the caller's responsibility to ensure that the requester and
    PI are different (so the PI does not get a notification for their
    own request)."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = 'New Allocation Renewal Request under Your Name'
    template_name = 'email/project_renewal/pi_new_project_renewal_request.txt'

    requester = request.requester
    requester_str = (
        f'{requester.first_name} {requester.last_name} ({requester.email})')

    pi = request.pi
    pi_str = f'{pi.first_name} {pi.last_name}'

    detail_view_name = 'pi-allocation-renewal-request-detail'
    center_base_url = settings.CENTER_BASE_URL
    review_url = urljoin(
        center_base_url, reverse(detail_view_name, kwargs={'pk': request.pk}))
    login_url = urljoin(center_base_url, reverse('login'))

    context = {
        'PORTAL_NAME': settings.PORTAL_NAME,
        'login_url': login_url,
        'pi_str': pi_str,
        'requested_project_name': request.post_project.name,
        'requester_str': requester_str,
        'review_url': review_url,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [pi.email]

    send_email_template(subject, template_name, context, sender, receiver_list)


def send_new_allocation_renewal_request_pooling_notification_email(request):
    """Send a notification email to the managers and PIs of the project
    being requested to pool with stating that someone is attempting to
    pool."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = (
        f'New request to pool with your project {request.post_project.name}')
    template_name = (
        'email/project_renewal/'
        'managers_new_pooled_project_renewal_request.txt')

    requester = request.requester
    requester_str = (
        f'{requester.first_name} {requester.last_name} ({requester.email})')

    pi = request.pi
    pi_str = f'{pi.first_name} {pi.last_name} ({pi.email})'

    context = {
        'center_name': settings.CENTER_NAME,
        'requested_project_name': request.post_project.name,
        'requester_str': requester_str,
        'pi_str': pi_str,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = request.post_project.managers_and_pis_emails()

    send_email_template(subject, template_name, context, sender, receiver_list)


def allocation_renewal_request_denial_reason(request):
    """Return the reason why the given AllocationRenewalRequest was
    denied, based on its 'state' field and/or an associated
    SavioProjectAllocationRequest."""
    if not isinstance(request, AllocationRenewalRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(request)}.')

    state = request.state
    eligibility = state['eligibility']
    other = state['other']

    DenialReason = namedtuple(
        'DenialReason', 'category justification timestamp')

    new_project_request = request.new_project_request

    if other['timestamp']:
        category = 'Other'
        justification = other['justification']
        timestamp = other['timestamp']
    elif eligibility['status'] == 'Denied':
        category = 'PI Ineligible'
        justification = eligibility['justification']
        timestamp = eligibility['timestamp']
    elif new_project_request and new_project_request.status.name == 'Denied':
        reason = new_project_request.denial_reason()
        category = reason.category
        justification = reason.justification
        timestamp = reason.timestamp
    else:
        raise ValueError('Provided request has an unexpected state.')

    return DenialReason(
        category=category, justification=justification, timestamp=timestamp)


def allocation_renewal_request_latest_update_timestamp(request):
    """Return the latest timestamp stored in the given
    AllocationRenewalRequest's 'state' field, or the empty string.

    The expected values are ISO 8601 strings, or the empty string, so
    taking the maximum should provide the correct output."""
    if not isinstance(request, AllocationRenewalRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(request)}.')

    state = request.state
    max_timestamp = ''
    for field in state:
        max_timestamp = max(max_timestamp, state[field].get('timestamp', ''))

    new_project_request = request.new_project_request
    if new_project_request:
        request_updated = new_project_request.latest_update_timestamp()
        max_timestamp = max(max_timestamp, request_updated)

    return max_timestamp


def allocation_renewal_request_state_status(request):
    """Return an AllocationRenewalRequestStatusChoice, based on the
    'state' field of the given AllocationRenewalRequest, and/or an
    associated SavioProjectAllocationRequest.

    This method returns one of only two states: 'Denied' or 'Under
    Review'. The other two possible states, 'Approved' and 'Complete',
    should be set by some other process.
        - 'Approved' should be set when the request is scheduled for
           processing.
        - 'Complete' should be set when the request is actually
          processed.
    """
    if not isinstance(request, AllocationRenewalRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(request)}.')

    state = request.state
    eligibility = state['eligibility']
    other = state['other']

    denied_status = AllocationRenewalRequestStatusChoice.objects.get(
        name='Denied')

    # The request was denied for some other non-listed reason.
    if other['timestamp']:
        return denied_status

    new_project_request = request.new_project_request
    if new_project_request:
        # The request was for a new Project, which was denied.
        status_name = new_project_request.status.name
        if status_name == 'Denied':
            return denied_status
    else:
        # The PI was ineligible.
        if eligibility['status'] == 'Denied':
            return denied_status

    # The request has not been denied, so it is under review.
    return AllocationRenewalRequestStatusChoice.objects.get(
        name='Under Review')


class AllocationRenewalRunnerBase(object):
    """A base class that Runners for handling AllocationRenewalsRequests
    should inherit from."""

    def __init__(self, request_obj, *args, **kwargs):
        self.request_obj = request_obj
        self.current_display_tz_date = display_time_zone_current_date()
        self.computing_allowance_interface = ComputingAllowanceInterface()
        self.computing_allowance = self.request_obj.computing_allowance

    def run(self):
        raise NotImplementedError('This method is not implemented.')

    def assert_request_not_status(self, unexpected_status):
        """Raise an assertion error if the request has the given
        unexpected status."""
        if not isinstance(
                unexpected_status, AllocationRenewalRequestStatusChoice):
            raise TypeError(
                'Status is not an AllocationRenewalRequestStatusChoice.')
        message = f'The request must not have status \'{unexpected_status}\'.'
        assert self.request_obj.status != unexpected_status, message

    def assert_request_status(self, expected_status):
        """Raise an assertion error if the request does not have the
        given expected status."""
        if not isinstance(
                expected_status, AllocationRenewalRequestStatusChoice):
            raise TypeError(
                'Status is not an AllocationRenewalRequestStatusChoice.')
        message = f'The request must have status \'{expected_status}\'.'
        assert self.request_obj.status == expected_status, message

    def handle_by_preference(self):
        request = self.request_obj
        pre_project = request.pre_project
        post_project = request.post_project
        is_pooled_pre = pre_project and pre_project.is_pooled()
        is_pooled_post = post_project.is_pooled()

        def log_message():
            pre_str = 'non-pooling' if not is_pooled_pre else 'pooling'
            post_str = 'non-pooling' if not is_pooled_post else 'pooling'
            return (
                f'AllocationRenewalRequest {request.pk}: {pre_str} in '
                f'pre-project {pre_project.name if pre_project else None} to '
                f'{post_str} in post-project {post_project.name}.')

        try:
            preference_case = request.get_pooling_preference_case()
        except ValueError as e:
            logger.error(log_message())
            raise e
        if preference_case == request.UNPOOLED_TO_UNPOOLED:
            logger.info(log_message())
            self.handle_unpooled_to_unpooled()
        elif preference_case == request.UNPOOLED_TO_POOLED:
            logger.info(log_message())
            self.handle_unpooled_to_pooled()
        elif preference_case == request.POOLED_TO_POOLED_SAME:
            logger.info(log_message())
            self.handle_pooled_to_pooled_same()
        elif preference_case == request.POOLED_TO_POOLED_DIFFERENT:
            logger.info(log_message())
            self.handle_pooled_to_pooled_different()
        elif preference_case == request.POOLED_TO_UNPOOLED_OLD:
            logger.info(log_message())
            self.handle_pooled_to_unpooled_old()
        elif preference_case == request.POOLED_TO_UNPOOLED_NEW:
            logger.info(log_message())
            self.handle_pooled_to_unpooled_new()

    def handle_unpooled_to_unpooled(self):
        """Handle the case when the preference is to stay unpooled."""
        raise NotImplementedError('This method is not implemented.')

    def handle_unpooled_to_pooled(self):
        """Handle the case when the preference is to start pooling."""
        raise NotImplementedError('This method is not implemented.')

    def handle_pooled_to_pooled_same(self):
        """Handle the case when the preference is to stay pooled with
        the same project."""
        raise NotImplementedError('This method is not implemented.')

    def handle_pooled_to_pooled_different(self):
        """Handle the case when the preference is to stop pooling with
        the current project and start pooling with a different
        project."""
        raise NotImplementedError('This method is not implemented.')

    def handle_pooled_to_unpooled_old(self):
        """Handle the case when the preference is to stop pooling and
        reuse another existing project owned by the PI."""
        raise NotImplementedError('This method is not implemented.')

    def handle_pooled_to_unpooled_new(self):
        """Handle the case when the preference is to stop pooling and
        create a new project."""
        raise NotImplementedError('This method is not implemented.')


class AllocationRenewalApprovalRunner(AllocationRenewalRunnerBase):
    """An object that performs necessary database changes when an
    AllocationRenewalRequest is approved."""

    def __init__(self, request_obj, num_service_units, email_strategy=None):
        super().__init__(request_obj)
        self.request_obj.allocation_period.assert_not_ended()
        expected_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Under Review')
        self.assert_request_status(expected_status)
        validate_num_service_units(num_service_units)
        self.num_service_units = num_service_units
        self._email_strategy = validate_email_strategy_or_get_default(
            email_strategy=email_strategy)

    def run(self):
        with transaction.atomic():
            self.approve_request()
        self.send_email()

    def approve_request(self):
        """Set the status of the request to 'Approved' and set its
        approval_time."""
        self.request_obj.status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Approved')
        self.request_obj.approval_time = utc_now_offset_aware()
        self.request_obj.save()

    def handle_unpooled_to_unpooled(self):
        """Handle the case when the preference is to stay unpooled."""
        pass

    def handle_unpooled_to_pooled(self):
        """Handle the case when the preference is to start pooling."""
        pass

    def handle_pooled_to_pooled_same(self):
        """Handle the case when the preference is to stay pooled with
        the same project."""
        pass

    def handle_pooled_to_pooled_different(self):
        """Handle the case when the preference is to stop pooling with
        the current project and start pooling with a different
        project."""
        pass

    def handle_pooled_to_unpooled_old(self):
        """Handle the case when the preference is to stop pooling and
        reuse another existing project owned by the PI."""
        pass

    def handle_pooled_to_unpooled_new(self):
        """Handle the case when the preference is to stop pooling and
        create a new project."""
        pass

    def send_email(self):
        """Send a notification email to the requester and PI."""
        request = self.request_obj
        try:
            email_method = send_allocation_renewal_request_approval_email
            email_args = (request, self.num_service_units)
            self._email_strategy.process_email(email_method, *email_args)
        except Exception as e:
            logger.exception(
                f'Failed to send notification email. Details:\n{e}')


class AllocationRenewalDenialRunner(AllocationRenewalRunnerBase):
    """An object that performs necessary database changes when an
    AllocationRenewalRequest is denied."""

    def __init__(self, request_obj):
        super().__init__(request_obj)
        unexpected_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Complete')
        self.assert_request_not_status(unexpected_status)

    def run(self):
        with transaction.atomic():
            self.handle_by_preference()
            self.deny_request()
        self.send_email()

    def deny_post_project(self):
        """Set the post_project's status to 'Denied'."""
        project = self.request_obj.post_project
        project.status = ProjectStatusChoice.objects.get(name='Denied')
        project.save()
        return project

    def deny_request(self):
        """Set the status of the request to 'Denied'."""
        self.request_obj.status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Denied')
        self.request_obj.save()

    def handle_unpooled_to_unpooled(self):
        """Handle the case when the preference is to stay unpooled."""
        pass

    def handle_unpooled_to_pooled(self):
        """Handle the case when the preference is to start pooling."""
        pass

    def handle_pooled_to_pooled_same(self):
        """Handle the case when the preference is to stay pooled with
        the same project."""
        pass

    def handle_pooled_to_pooled_different(self):
        """Handle the case when the preference is to stop pooling with
        the current project and start pooling with a different
        project."""
        pass

    def handle_pooled_to_unpooled_old(self):
        """Handle the case when the preference is to stop pooling and
        reuse another existing project owned by the PI."""
        pass

    def handle_pooled_to_unpooled_new(self):
        """Handle the case when the preference is to stop pooling and
        create a new project."""
        self.deny_post_project()

    def send_email(self):
        """Send a notification email to the requester and PI."""
        request = self.request_obj
        try:
            send_allocation_renewal_request_denial_email(request)
        except Exception as e:
            logger.exception(
                'Failed to send notification email. Details:\n{e}')


class AllocationRenewalProcessingRunner(AllocationRenewalRunnerBase):
    """An object that performs necessary database changes when an
    AllocationRenewalRequest is processed."""

    def __init__(self, request_obj, num_service_units, email_strategy=None):
        super().__init__(request_obj)
        self.request_obj.allocation_period.assert_started()
        self.request_obj.allocation_period.assert_not_ended()
        expected_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Approved')
        self.assert_request_status(expected_status)
        validate_num_service_units(num_service_units)
        self.num_service_units = num_service_units

        self._email_strategy = validate_email_strategy_or_get_default(
            email_strategy=email_strategy)

    def run(self):
        request = self.request_obj
        post_project = request.post_project
        old_project_status = post_project.status

        with transaction.atomic():
            self.upgrade_pi_user()
            post_project = self.activate_project(post_project)

            allocation, new_value = self.update_allocation(old_project_status)
            self.update_existing_user_allocations(new_value)

            create_project_users(
                post_project, request.requester, request.pi,
                AllocationRenewalRequest, email_strategy=self._email_strategy)

            self.update_pre_projects_of_future_period_requests()

            self.handle_by_preference()
            self.complete_request(self.num_service_units)
        self.send_email()

        return post_project, allocation

    @staticmethod
    def activate_project(project):
        """Set the given Project's status to 'Active'."""
        status = ProjectStatusChoice.objects.get(name='Active')
        project.status = status
        project.save()
        return project

    def complete_request(self, num_service_units):
        """Set the status of the request to 'Complete', set its number
        of service units, and set its completion_time."""
        self.request_obj.status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Complete')
        self.request_obj.num_service_units = num_service_units
        self.request_obj.completion_time = utc_now_offset_aware()
        self.request_obj.save()

    def demote_pi_to_user_on_pre_project(self):
        """If the pre_project is pooled (i.e., it has more than one PI),
        demote the PI from 'Principal Investigator' to 'User'.

        If the pre_project is None, do nothing."""
        request = self.request_obj
        pi = request.pi
        pre_project = request.pre_project
        if not pre_project:
            logger.info(
                f'AllocationRenewalRequest {request.pk} has no pre-Project. '
                f'Skipping demotion.')
            return
        if pre_project.pis().count() > 1:
            try:
                pi_project_user = pre_project.projectuser_set.get(user=pi)
            except ProjectUser.DoesNotExist:
                message = (
                    f'No ProjectUser exists for PI {pi.username} of Project '
                    f'{pre_project.name}, for which the PI has '
                    f'AllocationRenewalRequest {request.pk} to stop pooling '
                    f'under it.')
                logger.error(message)
            else:
                pi_project_user.role = ProjectUserRoleChoice.objects.get(
                    name='User')
                pi_project_user.save()
                message = (
                    f'Demoted {pi.username} from \'Principal Investigator\' '
                    f'to \'User\' on Project {pre_project.name}.')
                logger.info(message)
        else:
            message = (
                f'Project {pre_project.name} only has one PI. Skipping '
                f'demotion.')
            logger.info(message)

    def handle_unpooled_to_unpooled(self):
        """Handle the case when the preference is to stay unpooled."""
        pass

    def handle_unpooled_to_pooled(self):
        """Handle the case when the preference is to start pooling."""
        pass

    def handle_pooled_to_pooled_same(self):
        """Handle the case when the preference is to stay pooled with
        the same project."""
        pass

    def handle_pooled_to_pooled_different(self):
        """Handle the case when the preference is to stop pooling with
        the current project and start pooling with a different
        project."""
        self.demote_pi_to_user_on_pre_project()

    def handle_pooled_to_unpooled_old(self):
        """Handle the case when the preference is to stop pooling and
        reuse another existing project owned by the PI."""
        self.demote_pi_to_user_on_pre_project()

    def handle_pooled_to_unpooled_new(self):
        """Handle the case when the preference is to stop pooling and
        create a new project."""
        self.demote_pi_to_user_on_pre_project()

    def send_email(self):
        """Send a notification email to the requester and PI."""
        try:
            email_method = send_allocation_renewal_request_processing_email
            email_args = (self.request_obj, self.num_service_units)
            self._email_strategy.process_email(email_method, *email_args)
        except Exception as e:
            logger.exception(
                f'Failed to send notification email. Details:\n{e}')

    def update_allocation(self, old_project_status):
        """Perform allocation-related handling. Use the given
        ProjectStatusChoice, which the post_project had prior to being
        activated, to potentially set the start and end dates."""
        project = self.request_obj.post_project
        allocation_period = self.request_obj.allocation_period

        allocation = get_project_compute_allocation(project)
        allocation.status = AllocationStatusChoice.objects.get(name='Active')
        # For the start and end dates, if the Project is not 'Active' or the
        # date is not set, set it.
        if old_project_status.name != 'Active' or not allocation.start_date:
            allocation.start_date = display_time_zone_current_date()
        if old_project_status.name != 'Active' or not allocation.end_date:
            allocation.end_date = getattr(allocation_period, 'end_date', None)
        allocation.save()

        # Increase the allocation's service units.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        allocation_attribute, _ = \
            AllocationAttribute.objects.get_or_create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation)
        existing_value = (
            Decimal(allocation_attribute.value) if allocation_attribute.value
            else settings.ALLOCATION_MIN)
        new_value = existing_value + self.num_service_units
        validate_num_service_units(new_value)
        allocation_attribute.value = str(new_value)
        allocation_attribute.save()

        # Create a ProjectTransaction to store the change in service units.
        ProjectTransaction.objects.create(
            project=project,
            date_time=utc_now_offset_aware(),
            allocation=Decimal(new_value))

        return allocation, new_value

    def update_existing_user_allocations(self, value):
        """Perform user-allocation-related handling.

        In particular, update the Service Units for existing Users to
        the given value. The requester and/or PI will have their values
        set once their cluster account requests are approved."""
        project = self.request_obj.post_project
        date_time = utc_now_offset_aware()
        for project_user in project.projectuser_set.all():
            user = project_user.user
            allocation_updated = set_project_user_allocation_value(
                user, project, value)
            if allocation_updated:
                ProjectUserTransaction.objects.create(
                    project_user=project_user,
                    date_time=date_time,
                    allocation=Decimal(value))

    def upgrade_pi_user(self):
        """Set the is_pi field of the request's PI UserProfile to
        True."""
        pi = self.request_obj.pi
        pi.userprofile.is_pi = True
        pi.userprofile.save()

    def update_pre_projects_of_future_period_requests(self):
        """Update the pre_project fields of any 'Under Review',
        same-allowance-type AllocationRenewalRequests under future
        AllocationPeriods and under this request's PI to this request's
        post_project.

        This is necessary to cover the following case:
            - A request R1 is made to go from Project A to B under
              AllocationPeriod P1.
            - A request R2 is made to go from Project A to C under
              AllocationPeriod P2.
            - R1 is processed first, potentially demoting the PI on
              Project A, and promoting the PI on Project B.
            - When R2 is processed, the PI must be demoted on Project B,
              not Project A, before being promoted on Project C.

        Warning: This only applies to pooling-eligible allowance types.
        """
        request_pk = self.request_obj.pk
        pi = self.request_obj.pi
        post_project = self.request_obj.post_project

        future_period_requests = AllocationRenewalRequest.objects.filter(
            ~Q(pk=request_pk) &
            ~Q(status__name__in=['Complete', 'Denied']) &
            Q(computing_allowance=self.computing_allowance) &
            Q(allocation_period__start_date__gt=self.current_display_tz_date) &
            Q(pi=pi) &
            ~Q(pre_project=post_project))
        if future_period_requests.exists():
            message_template = (
                f'Updated AllocationRenewalRequest {{0}}\'s pre_project from '
                f'{{1}} to {post_project.pk} since AllocationRenewalRequest '
                f'{request_pk} updated PI {pi.username}\'s active '
                f'"{self.computing_allowance.name}" Project to '
                f'{post_project.name}.')
            for future_period_request in future_period_requests:
                tmp_pre_project = future_period_request.pre_project
                future_period_request.pre_project = post_project
                future_period_request.save()
                message = message_template.format(
                    future_period_request.pk, tmp_pre_project.pk)
                logger.info(message)

def get_gspread_wks(sheet_id, wks_id):
    """ TODO """
    try:
        gc = gspread.service_account(filename='tmp/credentials.json')
    except:
        return None
    sh = gc.open_by_key(sheet_id)
    wks = sh.get_worksheet(wks_id)

    return wks

def get_renewal_survey(allocation_period_name):
    """ Given the name of the allocation period, returns Google Form
     Survey info depending on LRC/BRC. The information is a dict containing:
        deployment: 'BRC/LRC',
        sheet_id: string,
        form_id: string,
        allocation_period: string,
        sheet_data: {
            allocation_period_col: int,
            pi_username_col: int,
            project_name_col: int
        } 
    The sheet_data values refer to the column coordinates of information used
    to enforce automatic check/block for the renewal form."""

    # TODO: How to get file path corrrectly onto file without hardcoding?
    with open("coldfront/core/project/utils_/data/survey_data.json") as fp:
        data = json.load(fp)
        deployment = ''
        if flag_enabled('BRC_ONLY'):
            deployment = 'BRC'
        else:
            deployment = 'LRC'
        for elem in data:
            if elem["allocation_period"] == allocation_period_name and elem["deployment"] == deployment:
                return elem
    
    return None

def renewal_survey_answer_conversion(question, all_answers):
    """ TODO """
    new_answer = ''
    if question == 'timestamp':
        new_answer = str(all_answers.request_time)
    elif question == 'which_brc_services_used':
        brc_services_converter = {
            'savio_hpc': 'Savio High Performance Computing and consulting',
            'condo_storage': 'Condo storage on Savio',
            'srdc': 'Secure Research Data & Computing (SRDC)',
            'aeod': 'Analytic Environments on Demand',
            'cloud_consulting': 'Cloud consulting (e.g., Amazon, Google, ' 
                        'Microsoft, XSEDE, UCB\'s Cloud Working Group)',
            'other': 'Other BRC consulting (e.g. assessing the '
                        'computation platform or resources appropriate '
                        'for your research workflow)',
            'none': 'None of the above'
        }

        answer = all_answers.renewal_survey_answers[question]
        for service in answer:
            new_answer += brc_services_converter[service] + ', '
    elif question == 'how_important_to_research_is_brc':
        answer = all_answers.renewal_survey_answers[question]
        if answer == '1':
            new_answer = 'Not at all important'
        elif answer == '2':
            new_answer = 'Somewhat important'
        elif answer == '3':
            new_answer = 'Important' 
        elif answer == '4':
            new_answer = 'Very important'
        elif answer == '5':
            new_answer = 'Essential'
        elif answer == '6':
            new_answer = 'Not applicable'
    elif question == 'which_open_ondemand_apps_used':
        ondemand_apps_converter = {
            'desktop': 'Desktop',
            'matlab': 'Matlab',
            'jupyter_notebook': 'Jupyter Notebook/Lab',
            'vscode_server': 'VS Code Server',
            'none': 'None of the above',
            'other': 'Other'
        }

        answer = all_answers.renewal_survey_answers[question]
        for app in answer:
            new_answer += ondemand_apps_converter[app] + ', '
    elif question == 'indicate_topic_interests':
        topic_interests_converter = {
            'have_visited_rdmp_website': 'I have visited the Research Data '
                    'Management Program web site.',
            'have_had_rdmp_event_or_consultation': 'I have participated in a '
                    'Research Data Management Program event or consultation.',
            'want_to_learn_more_and_have_rdm_consult': 'I am interested in the '
                    'Research Data Management Program; please have an RDM '
                    'consultant follow up with me.',
            'want_to_learn_security_and_have_rdm_consult': 'I am interested in '
                    'learning more about securing research data and/or secure '
                    'computation; please have an RDM consultant follow up with '
                    'me.',
            'interested_in_visualization_services': 'I am interested in '
                    'resources or services that support visualization of '
                    'research data.',
            'none_of_the_above': 'None of the above.'
        }

        answer = all_answers.renewal_survey_answers[question]
        for interest in answer:
            new_answer += topic_interests_converter[interest] + ', '
    elif question == 'allocation_period':
        new_answer = all_answers.allocation_period.name
    elif question == 'pi_name':
        new_answer = f'{all_answers.pi.first_name} {all_answers.pi.last_name}'
    elif question == 'pi_username':
        new_answer = all_answers.pi.username
    elif question == 'project_name':
        new_answer = all_answers.post_project.name
    elif question == 'requester_name':
        new_answer = f'{all_answers.requester.first_name} ' \
                        f'{all_answers.requester.last_name}'
    elif question == 'requester_username':
        new_answer = all_answers.requester.username
    else:
        answer = all_answers.renewal_survey_answers[question]
        new_answer = str(answer)
    new_answer = new_answer.rstrip(', ')
    return new_answer
