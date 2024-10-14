from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.allocation.utils import get_project_compute_resource_name
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.resource.utils import get_primary_compute_resource
from coldfront.core.resource.utils import get_primary_compute_resource_name
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import utc_now_offset_aware
from datetime import datetime
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import transaction
import logging
import pytz


class AccountingAllocationObjects(object):
    """A container for related Allocation objects needed for
    accounting."""

    def __init__(self, allocation=None, allocation_user=None,
                 allocation_attribute=None, allocation_attribute_usage=None,
                 allocation_user_attribute=None,
                 allocation_user_attribute_usage=None):
        self.allocation = allocation
        self.allocation_user = allocation_user
        self.allocation_attribute = allocation_attribute
        self.allocation_attribute_usage = allocation_attribute_usage
        self.allocation_user_attribute = allocation_user_attribute
        self.allocation_user_attribute_usage = allocation_user_attribute_usage


def convert_utc_datetime_to_unix_timestamp(utc_dt):
    """Return the given UTC datetime object as the number of seconds
    since the beginning of the epoch.

    Parameters:
        - dt (datetime): the datetime object to convert, whose tzinfo
          must be pytz.utc

    Returns:
        - int

    Raises:
        - TypeError, if the input is not a datetime object
        - ValueError, if the datetime's tzinfo is not pytz.utc
    """
    if not isinstance(utc_dt, datetime):
        raise TypeError(f'Datetime {utc_dt} is not a datetime.')
    if utc_dt.tzinfo != pytz.utc:
        raise ValueError(f'Datetime {utc_dt}\'s tzinfo is not pytz.utc.')
    epoch_start_utc_dt = datetime(1970, 1, 1).replace(tzinfo=pytz.utc)
    return (utc_dt - epoch_start_utc_dt).total_seconds()


def create_project_allocation(project, value):
    """Create a compute allocation with the given value for the given
    Project; return the created objects.

    Parameters:
        - project (Project): an instance of the Project model
        - value (Decimal): the allocation value to be set

    Returns:
        - AccountingAllocationObjects with a subset of fields set

    Raises:
        - IntegrityError, if a database creation fails due to
        constraints
        - MultipleObjectsReturned, if a database retrieval returns more
        than one object
        - ObjectDoesNotExist, if a database retrieval returns less than
        one object
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')
    if not isinstance(value, Decimal):
        raise TypeError(f'Value {value} is not a Decimal.')

    resource = get_primary_compute_resource()

    status = AllocationStatusChoice.objects.get(name='Active')
    allocation = Allocation.objects.create(project=project, status=status)
    allocation.resources.add(resource)
    allocation.save()

    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Service Units')
    allocation_attribute = AllocationAttribute.objects.create(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation, value=str(value))

    # Create a ProjectTransaction to store the change in service units.
    ProjectTransaction.objects.create(
        project=project,
        date_time=utc_now_offset_aware(),
        allocation=value)

    return AccountingAllocationObjects(
        allocation=allocation,
        allocation_attribute=allocation_attribute)


def create_user_project_allocation(user, project, value):
    """Create a compute allocation with the given value for the given
    User and Project; return the created objects.

    Parameters:
        - user (User): an instance of the User model
        - project (Project): an instance of the Project model
        - value (Decimal): the allocation value to be set

    Returns:
        - AccountingAllocationObjects with a subset of fields set

    Raises:
        - IntegrityError, if a database creation fails due to
        constraints
        - MultipleObjectsReturned, if a database retrieval returns more
        than one object
        - ObjectDoesNotExist, if a database retrieval returns less than
        one object
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(user, User):
        raise TypeError(f'User {user} is not a User object.')
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')
    if not isinstance(value, Decimal):
        raise TypeError(f'Value {value} is not a Decimal.')

    resource = get_primary_compute_resource()

    status = AllocationStatusChoice.objects.get(name='Active')
    allocation = Allocation.objects.get(
        project=project, status=status, resources__name=resource.name)

    status = AllocationUserStatusChoice.objects.get(name='Active')
    allocation_user = AllocationUser.objects.create(
        allocation=allocation, user=user, status=status)

    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Service Units')
    allocation_user_attribute = AllocationUserAttribute.objects.create(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation, allocation_user=allocation_user,
        value=str(value))

    # Create a ProjectUserTransaction to store the change in service units.
    project_user = ProjectUser.objects.get(project=project, user=user)
    ProjectUserTransaction.objects.create(
        project_user=project_user,
        date_time=utc_now_offset_aware(),
        allocation=value)

    return AccountingAllocationObjects(
        allocation=allocation,
        allocation_user=allocation_user,
        allocation_user_attribute=allocation_user_attribute)


def get_accounting_allocation_objects(project, user=None,
                                      enforce_allocation_active=True):
    """Return a namedtuple of database objects related to accounting and
    allocation for the given project and optional user.

    Parameters:
        - project (Project): an instance of the Project model
        - user (User): an instance of the User model

    Returns:
        - AccountingAllocationObjects instance

    Raises:
        - MultipleObjectsReturned, if a database retrieval returns more
        than one object
        - ObjectDoesNotExist, if a database retrieval returns less than
        one object
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')

    objects = AccountingAllocationObjects()

    allocation_kwargs = {
        'project': project,
        'resources__name': get_project_compute_resource_name(project),
    }
    if enforce_allocation_active:
        # Check that the project has an active Allocation to the
        # 'CLUSTER_NAME Compute' resource.
        allocation_kwargs['status'] = AllocationStatusChoice.objects.get(
            name='Active')
    allocation = Allocation.objects.get(**allocation_kwargs)

    # Check that the allocation has an attribute for Service Units and
    # an associated usage.
    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Service Units')
    allocation_attribute = AllocationAttribute.objects.get(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation)
    allocation_attribute_usage = AllocationAttributeUsage.objects.get(
        allocation_attribute=allocation_attribute)

    objects.allocation = allocation
    objects.allocation_attribute = allocation_attribute
    objects.allocation_attribute_usage = allocation_attribute_usage

    if user is None:
        return objects

    if not isinstance(user, User):
        raise TypeError(f'User {user} is not a User object.')

    project_user_kwargs = {
        'user': user,
        'project': project,
    }
    if enforce_allocation_active:
        # Check that there is an active association between the user and
        # project.
        project_user_kwargs['status'] = ProjectUserStatusChoice.objects.get(
            name='Active')
    ProjectUser.objects.get(**project_user_kwargs)

    allocation_user_kwargs = {
        'allocation': allocation,
        'user': user,
    }
    if enforce_allocation_active:
        # Check that the user is an active member of the allocation.
        allocation_user_kwargs['status'] = \
            AllocationUserStatusChoice.objects.get(name='Active')
    allocation_user = AllocationUser.objects.get(**allocation_user_kwargs)

    # Check that the allocation user has an attribute for Service Units
    # and an associated usage.
    allocation_user_attribute = AllocationUserAttribute.objects.get(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation, allocation_user=allocation_user)
    allocation_user_attribute_usage = AllocationUserAttributeUsage.objects.get(
        allocation_user_attribute=allocation_user_attribute)

    objects.allocation_user = allocation_user
    objects.allocation_user_attribute = allocation_user_attribute
    objects.allocation_user_attribute_usage = allocation_user_attribute_usage

    return objects


def set_project_allocation_value(project, value):
    """Set the value of the compute allocation for the given Project;
    return whether or not the update was performed successfully.

    Parameters:
        - project (Project): an instance of the Project model
        - value (Decimal): the allocation value to be set

    Returns:
        - Boolean denoting success or failure

    Raises:
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')
    if not isinstance(value, Decimal):
        raise TypeError(f'Value {value} is not a Decimal.')
    try:
        allocation_objects = get_accounting_allocation_objects(project)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(e)
        return False
    project_allocation = allocation_objects.allocation_attribute
    project_allocation.value = str(value)
    project_allocation.save()
    return True


def set_project_usage_value(project, value):
    """Set the value of the usage for the compute allocation for the
    given Project; return whether or not the update was performed
    successfully.

    Parameters:
        - project (Project): an instance of the Project model
        - value (Decimal): the allocation value to be set

    Returns:
        - Boolean denoting success or failure

    Raises:
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')
    if not isinstance(value, Decimal):
        raise TypeError(f'Value {value} is not a Decimal.')
    try:
        allocation_objects = get_accounting_allocation_objects(project)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(e)
        return False
    with transaction.atomic():
        project_usage = \
            AllocationAttributeUsage.objects.select_for_update().get(
                pk=allocation_objects.allocation_attribute_usage.pk)
        project_usage.value = value
        project_usage.save()
    return True


def set_project_user_allocation_value(user, project, value):
    """Set the value of the compute allocation for the given User and
    Project; return whether or not the update was performed
    successfully.

    Parameters:
        - user (User): an instance of the User model
        - project (Project): an instance of the Project model
        - value (Decimal): the allocation value to be set

    Returns:
        - Boolean denoting success or failure

    Raises:
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(user, User):
        raise TypeError(f'User {user} is not a User object.')
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')
    if not isinstance(value, Decimal):
        raise TypeError(f'Value {value} is not a Decimal.')
    try:
        allocation_objects = get_accounting_allocation_objects(
            project, user=user)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(e)
        return False
    user_project_allocation = allocation_objects.allocation_user_attribute
    user_project_allocation.value = str(value)
    user_project_allocation.save()
    return True


def set_project_user_usage_value(user, project, value):
    """Set the usage value of the usage for the compute allocation for
    the given Project; return whether or not the update was performed
    successfully.

    Parameters:
        - user (User): an instance of the User model
        - project (Project): an instance of the Project model
        - value (Decimal): the allocation value to be set

    Returns:
        - Boolean denoting success or failure

    Raises:
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(user, User):
        raise TypeError(f'User {user} is not a User object.')
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')
    if not isinstance(value, Decimal):
        raise TypeError(f'Value {value} is not a Decimal.')
    try:
        allocation_objects = get_accounting_allocation_objects(
            project, user=user)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(e)
        return False
    with transaction.atomic():
        user_project_usage = \
            AllocationUserAttributeUsage.objects.select_for_update().get(
                pk=allocation_objects.allocation_user_attribute_usage.pk)
        user_project_usage.value = value
        user_project_usage.save()
    return True
