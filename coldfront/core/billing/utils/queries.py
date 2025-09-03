import logging
import re

from collections import namedtuple

from django.contrib.auth.models import User
from django.db import transaction

from flags.state import flag_enabled

from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.models import BillingProject
from coldfront.core.billing.utils.billing_activity_managers import ProjectBillingActivityManager
from coldfront.core.billing.utils.billing_activity_managers import ProjectUserBillingActivityManager
from coldfront.core.billing.utils.billing_activity_managers import UserBillingActivityManager
from coldfront.core.project.models import Project
from coldfront.core.resource.utils import get_computing_allowance_project_prefixes
from coldfront.core.user.models import UserProfile


logger = logging.getLogger(__name__)


def find_and_replace_billing_activity(find_obj, replace_obj, project_obj,
                                      dry_run=False):
    """Find and replace all instances of the given old BillingActivity
    with the given new BillingActivity within the given Project.

    These include:
        - The Project's default BillingActivity instance
        - BillingActivity instances associated with ProjectUsers
        - BillingActivity instances associated with Users (via
          ProjectUser)

    Return a list of BillingActivityManager instances that are found to
    have the old instance and are (or would be, in the dry run case)
    replaced, as well as a count of how many of each type were found.

    Parameters:
        - find_obj (BillingActivity): The old instance to find. This may
            be None, in which case entities will only be updated if they
            have no BillingActivity.
        - replace_obj (BillingActivity): The new instance to replace old
            instances with
        - project_obj (Project): A Project instance
        - dry_run (bool): If True, return the proposed changes without
            applying them

    Returns:
        - A list of BillingActivityManager instances
        - A dict with counts of how many of each type were found and
          updated (or would be updated)
    """
    assert isinstance(find_obj, BillingActivity) or find_obj is None
    assert isinstance(replace_obj, BillingActivity)
    assert isinstance(project_obj, Project)

    if find_obj == replace_obj:
        return [], {'project': 0, 'project_user': 0, 'user': 0}

    billing_activity_managers, update_counts = find_billing_activity(
        find_obj, project_obj)

    if not dry_run:
        with transaction.atomic():
            for manager in billing_activity_managers:
                manager.billing_activity = replace_obj

    return billing_activity_managers, update_counts


def find_billing_activity(billing_activity_obj, project_obj):
    """Find all instances of the given BillingActivity within the given
    Project.

    These include:
        - The Project's default BillingActivity instance
        - BillingActivity instances associated with ProjectUsers
        - BillingActivity instances associated with Users (via
          ProjectUser)

    Return a list of BillingActivityManager instances that are found to
    have the BillingActivity, as well as a count of how many of each
    type were found.

    Parameters:
        - billing_activity_obj (BillingActivity): The instance to find.
            This may be None, in which case entities will only be
            returned if they have no BillingActivity.
        - project_obj (Project): A Project instance

    Returns:
        - A list of BillingActivityManager instances
        - A dict with counts of how many of each type were found
    """
    assert (
        isinstance(billing_activity_obj, BillingActivity) or
        billing_activity_obj is None)
    assert isinstance(project_obj, Project)

    billing_activity_managers = []
    find_counts = {
        'project': 0,
        'project_user': 0,
        'user': 0,
    }

    project_manager = ProjectBillingActivityManager(project_obj)
    if project_manager.billing_activity == billing_activity_obj:
        billing_activity_managers.append(project_manager)
        find_counts['project'] += 1

    project_user_objs = project_obj.projectuser_set.all()
    for project_user_obj in project_user_objs:
        project_user_manager = ProjectUserBillingActivityManager(
            project_user_obj)
        if project_user_manager.billing_activity == billing_activity_obj:
            billing_activity_managers.append(project_user_manager)
            find_counts['project_user'] += 1
        user_manager = UserBillingActivityManager(project_user_obj.user)
        if user_manager.billing_activity == billing_activity_obj:
            billing_activity_managers.append(user_manager)
            find_counts['user'] += 1

    return billing_activity_managers, find_counts


def get_billing_activity_from_full_id(full_id):
    """Given a fully-formed billing ID, get the matching
    BillingActivity, if it exists, or None."""
    project_identifier, activity_identifier = full_id.split('-')
    try:
        billing_project = BillingProject.objects.get(
            identifier=project_identifier)
    except BillingProject.DoesNotExist:
        return None
    try:
        billing_activity = BillingActivity.objects.get(
            billing_project=billing_project, identifier=activity_identifier)
    except BillingActivity.DoesNotExist:
        return None
    return billing_activity


def get_billing_id_usages(full_id=None, project_obj=None, user_obj=None):
    """Return all database objects storing billing IDs, with optional
    filtering for a specific ID, for IDs associated with a specific
    Project, or for IDs associated with a specific User.

    Parameters:
        - full_id (str): A fully-formed billing ID
        - project_obj (Project): A Project instance
        - user_obj (User): A User instance

    Returns:
        - BillingIdUsages (namedtuple): A namedtuple with the following
          keys and values:
              project_default: An AllocationAttribute queryset
              recharge: An AllocationUserAttribute queryset
              user_account: A UserProfile queryset
    """
    BillingIdUsages = namedtuple(
        'BillingIdUsages', 'project_default recharge user_account')
    output_kwargs = {
        'project_default': AllocationAttribute.objects.none(),
        'recharge': AllocationUserAttribute.objects.none(),
        'user_account': UserProfile.objects.none(),
    }

    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Billing Activity')

    allocation_attribute_kwargs = {}
    allocation_user_attribute_kwargs = {}
    user_profile_kwargs = {}

    if full_id is not None:
        assert isinstance(full_id, str)
        if not is_billing_id_well_formed(full_id):
            return BillingIdUsages(**output_kwargs)
        billing_activity = get_billing_activity_from_full_id(full_id)
        if billing_activity is None:
            return BillingIdUsages(**output_kwargs)
        pk_str = str(billing_activity.pk)
        allocation_attribute_kwargs['value'] = pk_str
        allocation_user_attribute_kwargs['value'] = pk_str
        user_profile_kwargs['billing_activity'] = billing_activity
    if project_obj is not None:
        assert isinstance(project_obj, Project)
        allocation_attribute_kwargs['allocation__project'] = project_obj
        allocation_user_attribute_kwargs['allocation__project'] = project_obj
    if user_obj is not None:
        assert isinstance(user_obj, User)
        allocation_user_attribute_kwargs['allocation_user__user'] = user_obj
        user_profile_kwargs['user'] = user_obj

    if allocation_attribute_kwargs:
        allocation_attributes = AllocationAttribute.objects.filter(
            allocation_attribute_type=allocation_attribute_type,
            **allocation_attribute_kwargs).order_by('id')
    else:
        allocation_attributes = AllocationAttribute.objects.none()
    output_kwargs['project_default'] = allocation_attributes

    if allocation_user_attribute_kwargs:
        allocation_user_attributes = AllocationUserAttribute.objects.filter(
            allocation_attribute_type=allocation_attribute_type,
            **allocation_user_attribute_kwargs).order_by('id')
    else:
        allocation_user_attributes = AllocationUserAttribute.objects.none()
    output_kwargs['recharge'] = allocation_user_attributes

    if user_profile_kwargs:
        user_profiles = UserProfile.objects.filter(
            **user_profile_kwargs).order_by('id')
    else:
        user_profiles = UserProfile.objects.none()
    output_kwargs['user_account'] = user_profiles

    return BillingIdUsages(**output_kwargs)


def get_or_create_billing_activity_from_full_id(full_id):
    """Given a fully-formed billing ID, get or create a matching
    BillingActivity, creating a BillingProject as needed."""
    project_identifier, activity_identifier = full_id.split('-')
    billing_project, _ = BillingProject.objects.get_or_create(
        identifier=project_identifier)
    billing_activity, _ = BillingActivity.objects.get_or_create(
        billing_project=billing_project, identifier=activity_identifier)
    return billing_activity


def is_billing_id_well_formed(full_id):
    """Given a fully-formed billing ID, return whether it conforms to
    the expected format."""
    regex = r'^\d{6}-\d{3}$'
    return re.match(regex, full_id)


def is_project_billing_id_required_and_missing(project_obj):
    """Return whether the given Project is expected to have a default
    billing ID, and, if so, whether it has one."""
    assert isinstance(project_obj, Project)
    if not flag_enabled('LRC_ONLY'):
        return False
    computing_allowance_project_prefixes = \
        get_computing_allowance_project_prefixes()
    if not project_obj.name.startswith(computing_allowance_project_prefixes):
        return False
    allocation = get_project_compute_allocation(project_obj)
    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Billing Activity')
    billing_attribute = allocation.allocationattribute_set.filter(
        allocation_attribute_type=allocation_attribute_type).first()
    if billing_attribute is None:
        return True
    try:
        billing_activity_pk = int(billing_attribute.value.strip())
        BillingActivity.objects.get(pk=billing_activity_pk)
    except Exception as e:
        logger.exception(e)
        return True
    return False
