import logging

from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import SecureDirAddUserRequest
from coldfront.core.allocation.models import SecureDirAddUserRequestStatusChoice
from coldfront.core.allocation.models import SecureDirRemoveUserRequest
from coldfront.core.allocation.models import SecureDirRemoveUserRequestStatusChoice


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


def can_manage_secure_directory(allocation, user):
    """Return whether the given User has permissions to manage the given
    secure directory (Allocation). The following users do:
        - Superusers
        - Active PIs of the project, regardless of whether they have
          been added to the directory
        - Active managers of the project who have been added to the
          directory
    """
    if user.is_superuser:
        return True

    project = allocation.project
    if user in project.pis(active_only=True):
        return True

    if user in project.managers(active_only=True):
        user_on_allocation = AllocationUser.objects.filter(
            allocation=allocation,
            user=user,
            status__name='Active')
        if user_on_allocation:
            return True

    return False
