import os
import logging

from urllib.parse import urljoin

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse

from coldfront.config import settings
from coldfront.core.allocation.models import Allocation, AllocationStatusChoice, \
    AllocationAttributeType, AllocationAttribute, SecureDirAddUserRequest, \
    SecureDirRemoveUserRequest, SecureDirAddUserRequestStatusChoice, \
    SecureDirRemoveUserRequestStatusChoice, SecureDirRequest, \
    SecureDirRequestStatusChoice, AllocationUser, AllocationUserStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.resource.models import Resource, ResourceAttribute
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterfaceError
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.email.email_strategy import validate_email_strategy_or_get_default
from coldfront.core.utils.mail import send_email_template

logger = logging.getLogger(__name__)


# All project-specific secure subdirectories begin with the following prefix.
SECURE_DIRECTORY_NAME_PREFIX = 'pl1_'


def create_secure_dirs(project, subdirectory_name, scratch_or_groups):
    """
    Creates one secure directory allocation: either a group directory or a
    scratch2 directory, depending on scratch_or_groups. Additionally creates
    an AllocationAttribute for the new allocation that corresponds to the
    directory path on the cluster.
    Parameters:
        - project (Project): a Project object to create a secure directory
                            allocation for
        - subdirectory_name (str): the name of the subdirectory on the cluster
        - scratch_or_groups (str): one of either 'scratch' or 'groups'
    Returns:
        - allocation
    Raises:
        - TypeError, if subdirectory_name has an invalid type
        - ValueError, if scratch_or_groups does not have a valid value
        - ValidationError, if the Allocations already exist
    """

    if not isinstance(project, Project):
        raise TypeError(f'Invalid Project {project}.')
    if not isinstance(subdirectory_name, str):
        raise TypeError(f'Invalid subdirectory_name {subdirectory_name}.')
    if scratch_or_groups not in ['scratch', 'groups']:
        raise ValueError(f'Invalid scratch_or_groups arg {scratch_or_groups}.')

    if scratch_or_groups == 'scratch':
        p2p3_directory = Resource.objects.get(name='Scratch P2/P3 Directory')
    else:
        p2p3_directory = Resource.objects.get(name='Groups P2/P3 Directory')

    query = Allocation.objects.filter(project=project,
                                      resources__in=[p2p3_directory])

    if query.exists():
        raise ValidationError('Allocation already exist')

    allocation = Allocation.objects.create(
        project=project,
        status=AllocationStatusChoice.objects.get(name='Active'),
        start_date=utc_now_offset_aware())

    p2p3_path = p2p3_directory.resourceattribute_set.get(
        resource_attribute_type__name='path')

    allocation.resources.add(p2p3_directory)

    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Cluster Directory Access')

    p2p3_subdirectory = AllocationAttribute.objects.create(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation,
        value=os.path.join(p2p3_path.value, subdirectory_name))

    return allocation


def get_secure_dir_manage_user_request_objects(self, action):
    """
    Sets attributes pertaining to a secure directory based on the
    action being performed.

    Parameters:
        - self (object): object to set attributes for
        - action (str): the action being performed, either 'add' or 'remove'

    Raises:
        - TypeError, if the 'self' object is not an object
        - ValueError, if action is not one of 'add' or 'remove'
    """

    action = action.lower()
    if not isinstance(self, object):
        raise TypeError(f'Invalid self {self}.')
    if action not in ['add', 'remove']:
        raise ValueError(f'Invalid action {action}.')

    add_bool = action == 'add'

    request_obj = SecureDirAddUserRequest \
        if add_bool else SecureDirRemoveUserRequest
    request_status_obj = SecureDirAddUserRequestStatusChoice \
        if add_bool else SecureDirRemoveUserRequestStatusChoice

    language_dict = {
        'preposition': 'to' if add_bool else 'from',
        'noun': 'addition' if add_bool else 'removal',
        'verb': 'add' if add_bool else 'remove'
    }

    setattr(self, 'action', action.lower())
    setattr(self, 'add_bool', add_bool)
    setattr(self, 'request_obj', request_obj)
    setattr(self, 'request_status_obj', request_status_obj)
    setattr(self, 'language_dict', language_dict)


def secure_dir_request_state_status(secure_dir_request):
    """Return a SecureDirRequestStatusChoice, based on the
    'state' field of the given SecureDirRequest."""
    if not isinstance(secure_dir_request, SecureDirRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(secure_dir_request)}.')

    state = secure_dir_request.state
    rdm_consultation = state['rdm_consultation']
    mou = state['mou']
    setup = state['setup']
    other = state['other']

    if (rdm_consultation['status'] == 'Denied' or
            mou['status'] == 'Denied' or
            setup['status'] == 'Denied' or
            other['timestamp']):
        return SecureDirRequestStatusChoice.objects.get(name='Denied')

    # One or more steps is pending.
    if (rdm_consultation['status'] == 'Pending' or
            mou['status'] == 'Pending'):
        return SecureDirRequestStatusChoice.objects.get(
            name='Under Review')

    # The request has been approved and is processing.
    return SecureDirRequestStatusChoice.objects.get(
        name='Approved - Processing')


class SecureDirRequestRunner(object):
    """An object that performs necessary checks and updates, and sends
     notifications, when a new secure directory is requested for a
     project."""

    def __init__(self, request_kwargs, email_strategy=None):
        self._request_kwargs = request_kwargs
        # Always create the request with 'Under Review' status.
        self._request_kwargs['status'] = \
            SecureDirRequestStatusChoice.objects.get(name='Under Review')
        self._project_obj = self._request_kwargs['project']
        self._request_obj = None

        self._email_strategy = validate_email_strategy_or_get_default(
            email_strategy=email_strategy)

    def run(self):
        """Perform checks and updates."""
        is_project_eligible = is_project_eligible_for_secure_dirs(
            self._project_obj)
        if not is_project_eligible:
            raise Exception(
                f'Project {self._project_obj.name} is ineligible for a secure '
                f'directory.')

        with transaction.atomic():
            self._request_obj = self._create_secure_dir_request_obj()

        self._send_emails_safe()

    def _create_secure_dir_request_obj(self):
        """Create a SecureDirRequest object from provided arguments, and
        return it."""
        return SecureDirRequest.objects.create(**self._request_kwargs)

    @staticmethod
    def _get_request_detail_url(request_pk):
        """Given the primary key of a SecureDirRequest, return a URL to
        the detail page for it."""
        domain = settings.CENTER_BASE_URL
        view = reverse('secure-dir-request-detail', kwargs={'pk': request_pk})
        return urljoin(domain, view)

    def _send_email_to_admins(self, secure_dir_request_obj):
        """Send an email notification to cluster admins, notifying them
        of the newly-created request."""
        requester = secure_dir_request_obj.requester
        requester_str = (
            f'{requester.first_name} {requester.last_name} ({requester.email})')

        pi = secure_dir_request_obj.pi
        pi_str = f'{pi.first_name} {pi.last_name} ({pi.email})'

        review_url = self._get_request_detail_url(secure_dir_request_obj.pk)

        context = {
            'pi_str': pi_str,
            'project_name': secure_dir_request_obj.project.name,
            'requester_str': requester_str,
            'review_url': review_url,
        }

        subject = 'New Secure Directory Request'
        template_name = (
            'email/secure_dir_request/secure_dir_new_request_admin.txt')
        sender = settings.EMAIL_SENDER
        recipients = settings.EMAIL_ADMIN_LIST

        send_email_template(subject, template_name, context, sender, recipients)

    def _send_email_to_pi(self, secure_dir_request_obj):
        """Send an email notification to the selected PI, notifying them
        that a request was made under their name."""
        requester = secure_dir_request_obj.requester
        requester_str = (
            f'{requester.first_name} {requester.last_name} ({requester.email})')

        pi = secure_dir_request_obj.pi
        pi_str = f'{pi.first_name} {pi.last_name}'

        review_url = self._get_request_detail_url(secure_dir_request_obj.pk)

        context = {
            'pi_str': pi_str,
            'PORTAL_NAME': settings.PORTAL_NAME,
            'project_name': secure_dir_request_obj.project.name,
            'requester_str': requester_str,
            'review_url': review_url,
        }

        subject = 'New Secure Directory Request'
        template_name = (
            'email/secure_dir_request/secure_dir_new_request_pi.txt')
        sender = settings.EMAIL_SENDER
        recipients = [pi.email]

        send_email_template(subject, template_name, context, sender, recipients)

    def _send_emails(self):
        """Send email notifications."""
        # To cluster admins
        email_method = self._send_email_to_admins
        email_args = (self._request_obj, )
        self._email_strategy.process_email(email_method, *email_args)

        # To the PI, if not the requester
        if self._request_obj.pi != self._request_obj.requester:
            email_method = self._send_email_to_pi
            email_args = (self._request_obj, )
            self._email_strategy.process_email(email_method, *email_args)

    def _send_emails_safe(self):
        """Send emails.

        Catch all exceptions to prevent rolling back any enclosing
        transaction.
        """
        try:
            self._send_emails()
        except Exception as e:
            message = (
                f'Encountered unexpected exception when sending notification '
                f'emails. Details:\n{e}')
            logger.exception(message)


class SecureDirRequestDenialRunner(object):
    """An object that performs necessary database changes when a new
    secure directory request is denied."""

    def __init__(self, request_obj):
        self.request_obj = request_obj

    def run(self):
        self.deny_request()
        self.send_email()

    def deny_request(self):
        """Set the status of the request to 'Denied'."""
        self.request_obj.status = \
            SecureDirRequestStatusChoice.objects.get(name='Denied')
        self.request_obj.save()

    def send_email(self):
        """Send a notification email to the requester and PI."""
        if settings.EMAIL_ENABLED:
            pis = self.request_obj.project.projectuser_set.filter(
                role__name='Principal Investigator',
                status__name='Active',
                enable_notifications=True)
            users_to_notify = [x.user for x in pis]
            users_to_notify.append(self.request_obj.requester)
            users_to_notify = set(users_to_notify)

            for user in users_to_notify:
                try:
                    context = {
                        'user_first_name': user.first_name,
                        'user_last_name': user.last_name,
                        'project': self.request_obj.project.name,
                        'reason': self.request_obj.denial_reason().justification,
                        'signature': settings.EMAIL_SIGNATURE,
                        'support_email': settings.CENTER_HELP_EMAIL,
                    }

                    send_email_template(
                        f'Secure Directory Request Denied',
                        'email/secure_dir_request/secure_dir_request_denied.txt',
                        context,
                        settings.EMAIL_SENDER,
                        [user.email])

                except Exception as e:
                    logger.error('Failed to send notification email. Details:\n')
                    logger.exception(e)


class SecureDirRequestApprovalRunner(object):
    """An object that performs necessary database changes when a new
    secure directory request is approved and completed."""

    def __init__(self, request_obj):
        self.request_obj = request_obj
        self.success_messages = []
        self.error_messages = []

    def get_messages(self):
        return self.success_messages, self.error_messages

    def run(self):
        self.approve_request()
        groups_alloc, scratch_alloc = self.call_create_secure_dir()
        if groups_alloc and scratch_alloc:
            self.send_email(groups_alloc, scratch_alloc)
            message = f'The secure directory for ' \
                      f'{self.request_obj.project.name} ' \
                      f'was successfully created.'
            self.success_messages.append(message)

    def approve_request(self):
        """Set the status of the request to 'Approved - Complete'."""
        self.request_obj.status = \
            SecureDirRequestStatusChoice.objects.get(name='Approved - Complete')
        self.request_obj.completion_time = utc_now_offset_aware()
        self.request_obj.save()

    def call_create_secure_dir(self):
        """Creates the groups and scratch secure directories."""

        groups_alloc, scratch_alloc = None, None
        subdirectory_name = self.request_obj.directory_name
        try:
            groups_alloc = \
                create_secure_dirs(self.request_obj.project,
                                   subdirectory_name,
                                   'groups')
        except Exception as e:
            message = f'Failed to create groups secure directory for ' \
                      f'{self.request_obj.project.name}.'
            self.error_messages.append(message)
            logger.error(message)
            logger.exception(e)

        try:
            scratch_alloc = \
                create_secure_dirs(self.request_obj.project,
                                   subdirectory_name,
                                   'scratch')
        except Exception as e:
            message = f'Failed to create scratch secure directory for ' \
                      f'{self.request_obj.project.name}.'
            self.error_messages.append(message)
            logger.error(message)
            logger.exception(e)

        return groups_alloc, scratch_alloc

    def send_email(self, groups_alloc, scratch_alloc):
        """Send a notification email to the requester and PI."""
        if settings.EMAIL_ENABLED:
            pis = self.request_obj.project.projectuser_set.filter(
                role__name='Principal Investigator',
                status__name='Active',
                enable_notifications=True)
            users_to_notify = [x.user for x in pis]
            users_to_notify.append(self.request_obj.requester)
            users_to_notify = set(users_to_notify)

            allocation_attribute_type = AllocationAttributeType.objects.get(
                name='Cluster Directory Access')

            groups_dir = AllocationAttribute.objects.get(
                allocation_attribute_type=allocation_attribute_type,
                allocation=groups_alloc).value

            scratch_dir = AllocationAttribute.objects.get(
                allocation_attribute_type=allocation_attribute_type,
                allocation=scratch_alloc).value

            for user in users_to_notify:
                try:
                    context = {
                        'user_first_name': user.first_name,
                        'user_last_name': user.last_name,
                        'project': self.request_obj.project.name,
                        'groups_dir': groups_dir,
                        'scratch_dir': scratch_dir,
                        'signature': settings.EMAIL_SIGNATURE,
                        'support_email': settings.CENTER_HELP_EMAIL,
                    }

                    send_email_template(
                        f'Secure Directory Request Approved',
                        'email/secure_dir_request/secure_dir_request_approved.txt',
                        context,
                        settings.EMAIL_SENDER,
                        [user.email])

                except Exception as e:
                    logger.error('Failed to send notification email. Details:\n')
                    logger.exception(e)


def get_secure_dir_allocations(project=None):
    """Returns a queryset of all active secure directory allocations.
    Optionally, return those for a specific project."""
    scratch_directory = Resource.objects.get(name='Scratch P2/P3 Directory')
    groups_directory = Resource.objects.get(name='Groups P2/P3 Directory')

    kwargs = {
        'resources__in': [scratch_directory, groups_directory],
        'status__name': 'Active',
    }
    if project is not None:
        assert isinstance(project, Project)
        kwargs['project'] = project

    return Allocation.objects.filter(**kwargs)


def get_default_secure_dir_paths():
    """Returns the default Groups and Scratch secure directory paths."""

    groups_path = \
        ResourceAttribute.objects.get(
            resource_attribute_type__name='path',
            resource__name='Groups P2/P3 Directory').value
    scratch_path = \
        ResourceAttribute.objects.get(
            resource_attribute_type__name='path',
            resource__name='Scratch P2/P3 Directory').value

    return groups_path, scratch_path


def is_project_eligible_for_secure_dirs(project):
    """Return whether the given Project is eligible to request a secure
    directory. The following criteria are considered:
        - Is active;
        - Has a Condo, FCA, or ICA computing allowance;
        - Does not already have secure directories;
        - Does not have a non-"Denied" request for secure directories.
    """
    assert isinstance(project, Project)

    # Is active
    active_project_status = ProjectStatusChoice.objects.get(name='Active')
    if project.status != active_project_status:
        return False

    # Has a Condo, FCA, or ICA computing allowance
    eligible_computing_allowance_names = {
        BRCAllowances.CO,
        BRCAllowances.FCA,
        BRCAllowances.ICA,
    }
    computing_allowance_interface = ComputingAllowanceInterface()
    try:
        computing_allowance = \
            computing_allowance_interface.allowance_from_project(project)
    except ComputingAllowanceInterfaceError:
        # Non-primary-cluster projects (ineligible) raise this error.
        return False
    if computing_allowance.name not in eligible_computing_allowance_names:
        return False

    eligible_project_prefixes = tuple(
        computing_allowance_interface.code_from_name(computing_allowance_name)
        for computing_allowance_name in eligible_computing_allowance_names)
    if not project.name.startswith(eligible_project_prefixes):
        return False

    # Does not already have secure directories
    if get_secure_dir_allocations(project=project).exists():
        return False

    # Does not have a non-"Denied" request for secure directories
    denied_request_status = SecureDirRequestStatusChoice.objects.get(
        name='Denied')
    non_denied_requests = SecureDirRequest.objects.filter(
        Q(project=project) & ~Q(status=denied_request_status))
    if non_denied_requests.exists():
        return False

    return True


def get_all_secure_dir_paths():
    """Returns a set of all secure directory paths."""

    group_resource = Resource.objects.get(name='Groups P2/P3 Directory')
    scratch_resource = Resource.objects.get(name='Scratch P2/P3 Directory')

    paths = \
        set(AllocationAttribute.objects.filter(
            allocation_attribute_type__name='Cluster Directory Access',
            allocation__resources__in=[scratch_resource, group_resource]).
            values_list('value', flat=True))

    return paths


def is_secure_directory_name_suffix_available(proposed_directory_name_suffix,
                                              exclude_request_pk=None):
    """Returns True if the proposed secure directory name suffix is
    available and False otherwise. A name suffix is available if it is
    neither in use by an existing secure directory nor in use by a
    pending request for a new secure directory, with the possible
    exception of the request with the given primary key from which it
    came.

    Parameters:
        - proposed_directory_name_suffix (str): The name of the proposed
            directory, without SECURE_DIRECTORY_NAME_PREFIX
        - exclude_request_pk (int): The primary key of a SecureDirRequest
            object to exclude

    Returns:
        - bool: True if the proposed directory name suffix is available,
            False otherwise
    """

    def get_directory_name_suffix(_directory_name):
        if _directory_name.startswith(SECURE_DIRECTORY_NAME_PREFIX):
            _directory_name = _directory_name[
                len(SECURE_DIRECTORY_NAME_PREFIX):]
        return _directory_name

    assert not proposed_directory_name_suffix.startswith(
        SECURE_DIRECTORY_NAME_PREFIX)

    unavailable_name_suffixes = set()
    existing_secure_directory_paths = get_all_secure_dir_paths()
    for directory_path in existing_secure_directory_paths:
        directory_name = os.path.basename(directory_path)
        directory_name_suffix = get_directory_name_suffix(directory_name)
        unavailable_name_suffixes.add(directory_name_suffix)
    pending_requested_directory_names = list(
        SecureDirRequest.objects
            .exclude(status__name='Denied')
            .exclude(pk=exclude_request_pk)
            .values_list('directory_name', flat=True))
    for directory_name in pending_requested_directory_names:
        directory_name_suffix = get_directory_name_suffix(directory_name)
        unavailable_name_suffixes.add(directory_name_suffix)

    return proposed_directory_name_suffix not in unavailable_name_suffixes


def set_sec_dir_context(context_dict, request_obj):
    """
    Sets the sec_dir_request, groups_path, and scratch_path items in the given
    context dictionary.

    Parameters:
    - context_dir (dict): the dictionary in which values are being set
    - request_obj (SecureDirRequest): the relevant SecureDirRequest object

    Raises:
    - TypeError, if 'context_dir' is not a dictionary
    - TypeError, if 'request_obj' is not a SecureDirRequest
    """

    if not isinstance(context_dict, dict):
        raise TypeError(f'Passed context_dict {context_dict} is not a dict.')
    if not isinstance(request_obj, SecureDirRequest):
        raise TypeError(f'Invalid SecureDirRequest {request_obj}.')

    context_dict['secure_dir_request'] = request_obj
    context_dict['proposed_directory_name'] = request_obj.directory_name
    groups_path, scratch_path = get_default_secure_dir_paths()
    context_dict['proposed_groups_path'] = \
        os.path.join(groups_path, context_dict['proposed_directory_name'])
    context_dict['proposed_scratch_path'] = \
        os.path.join(scratch_path, context_dict['proposed_directory_name'])
