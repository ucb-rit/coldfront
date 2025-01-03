import logging

from abc import ABC
from abc import abstractmethod

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.urls import reverse

from coldfront.core.allocation.models import SecureDirAddUserRequest
from coldfront.core.allocation.models import SecureDirAddUserRequestStatusChoice
from coldfront.core.allocation.models import SecureDirRemoveUserRequest
from coldfront.core.allocation.models import SecureDirRemoveUserRequestStatusChoice
from coldfront.core.allocation.utils_.secure_dir_utils.secure_dir import SecureDirectory

from coldfront.core.utils.email.email_strategy import validate_email_strategy_or_get_default
from coldfront.core.utils.mail import send_email_template


logger = logging.getLogger(__name__)


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


class SecureDirectoryManageUserRequestRunner(ABC):
    """An abstract class that performs processing when a user is
    requested to be added to or removed from a secure directory."""

    # TODO: Add success_messages and error_messages?

    request_model = None
    request_status_model = None

    @abstractmethod
    def __init__(self, secure_directory, user, email_strategy=None):
        assert isinstance(secure_directory, SecureDirectory)
        assert isinstance(user, User)
        self._secure_directory = secure_directory
        self._user = user
        self._request_obj = None
        self._email_strategy = validate_email_strategy_or_get_default(
            email_strategy=email_strategy)

    def run(self):
        """Create a request object and send notification emails."""
        with transaction.atomic():
            self._request_obj = self._create_request_obj()

        self._send_emails_safe()

    def _create_request_obj(self):
        """Create a request object from provided arguments."""
        pending_status = self.request_status_model.objects.get(
            name__icontains='Pending')
        directory_path = self._secure_directory.get_path()
        return self.request_model.objects.create(
            user=self._user,
            allocation=self._secure_directory._allocation_obj,
            status=pending_status,
            directory=directory_path)

    @abstractmethod
    def _send_email_to_admins(self):
        """Send an email notification to cluster admins, notifying them
        of the newly-created request."""
        pass

    def _send_emails(self):
        """Send email notifications."""
        # To cluster admins
        email_method = self._send_email_to_admins
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


class SecureDirectoryAddUserRequestRunner(SecureDirectoryManageUserRequestRunner):
    """A concrete class that performs processing when a user is
    requested to be added to a secure directory."""

    request_model = SecureDirAddUserRequest
    request_status_model = SecureDirAddUserRequestStatusChoice

    def _send_email_to_admins(self):
        user_str = f'{
            self._user.first_name} {self._user.last_name} ({self._user.email})'
        review_url = reverse(
            'secure-dir-manage-users-request-list',
            kwargs={'action': 'add', 'status': 'pending'})
        context = {
            'user_str': user_str,
            'directory_name': self._secure_directory.get_path(),
            'review_url': review_url,
        }
        subject = 'New Secure Directory Add User Request'
        template_name = (
            'email/secure_dir_request/new_secure_dir_add_user_request.txt')
        sender = settings.EMAIL_SENDER
        recipients = settings.EMAIL_ADMIN_LIST

        send_email_template(subject, template_name, context, sender, recipients)


class SecureDirectoryRemoveUserRequestRunner(SecureDirectoryManageUserRequestRunner):
    """A concrete class that performs processing when a user is
    requested to be removed from a secure directory."""

    request_model = SecureDirRemoveUserRequest
    request_status_model = SecureDirRemoveUserRequestStatusChoice

    def _send_email_to_admins(self):
        user_str = f'{
            self._user.first_name} {self._user.last_name} ({self._user.email})'
        review_url = reverse(
            'secure-dir-manage-users-request-list',
            kwargs={'action': 'remove', 'status': 'pending'})
        context = {
            'user_str': user_str,
            'directory_name': self._secure_directory.get_path(),
            'review_url': review_url,
        }
        subject = 'New Secure Directory Remove User Request'
        template_name = (
            'email/secure_dir_request/new_secure_dir_remove_user_request.txt')
        sender = settings.EMAIL_SENDER
        recipients = settings.EMAIL_ADMIN_LIST
        send_email_template(subject, template_name, context, sender, recipients)


class SecureDirectoryManageUserRequestRunnerFactory(object):
    """A factory for returning a class that performs processing when a
    user is requested to be added to or removed from a secure
    directory."""

    def get_runner(self, action, *args, **kwargs):
        """Return an instantiated runner for the given action with the
        given arguments and keyword arguments."""
        return self._get_runner_class(action)(*args, **kwargs)

    @staticmethod
    def _get_runner_class(action):
        if action == 'add':
            return SecureDirectoryAddUserRequestRunner
        elif action == 'remove':
            return SecureDirectoryRemoveUserRequestRunner
        else:
            raise ValueError(f'Invalid action {action}.')
