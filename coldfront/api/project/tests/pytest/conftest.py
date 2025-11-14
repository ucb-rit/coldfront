import pytest
from decimal import Decimal

from coldfront.api.statistics.utils import create_project_allocation, \
    create_user_project_allocation
from coldfront.core.allocation.models import AllocationAttributeType, \
    AllocationUserAttribute
from coldfront.core.project.models import ProjectStatusChoice, \
    ProjectUserStatusChoice, ProjectUserRoleChoice, Project, ProjectUser
from coldfront.core.user.models import UserProfile, ExpiringToken
from django.contrib.auth.models import User


@pytest.fixture
def api_test_data(django_db_setup, db):
    """Create test data for API tests.

    Note: This assumes django_db_setup from the top-level conftest.py has
    already run, which creates default choices and staff users.
    """
    # Create or get a staff user (may already exist from top-level setup)
    staff_user, _ = User.objects.get_or_create(
        username='staff',
        defaults={'email': 'staff@nonexistent.com', 'is_staff': True}
    )

    # Create a superuser
    superuser, _ = User.objects.get_or_create(
        username='superuser',
        defaults={
            'email': 'superuser@nonexistent.com',
            'is_superuser': True,
            'is_staff': True,
        }
    )
    if not superuser.is_superuser:
        superuser.is_superuser = True
        superuser.is_staff = True
        superuser.save()

    # Create a PI
    pi, _ = User.objects.get_or_create(
        username='pi',
        defaults={'email': 'pi@nonexistent.com'}
    )
    user_profile, _ = UserProfile.objects.get_or_create(user=pi)
    if not user_profile.is_pi:
        user_profile.is_pi = True
        user_profile.save()

    # Create three regular users
    users = []
    for i in range(3):
        user, _ = User.objects.get_or_create(
            username=f'user{i}',
            defaults={'email': f'user{i}@nonexistent.com'}
        )
        user_profile, _ = UserProfile.objects.get_or_create(user=user)
        if user_profile.cluster_uid != f'{i}':
            user_profile.cluster_uid = f'{i}'
            user_profile.save()
        users.append(user)

    # Create Projects and associate Users with them
    project_status = ProjectStatusChoice.objects.get(name='Active')
    project_user_status = ProjectUserStatusChoice.objects.get(name='Active')
    user_role = ProjectUserRoleChoice.objects.get(name='User')
    pi_role = ProjectUserRoleChoice.objects.get(
        name='Principal Investigator')

    # Create projects with different allowance type prefixes
    # Use prefixes that exist in the current deployment's ComputingAllowanceInterface
    from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
    interface = ComputingAllowanceInterface()
    allowances = interface.allowances()
    available_codes = []
    for allowance in allowances:
        try:
            code = interface._object_to_code.get(allowance)
            if code:
                available_codes.append(code)
        except (KeyError, AttributeError):
            pass

    # Create up to 5 projects using available codes from the deployment
    project_configs = []
    for i, code in enumerate(available_codes[:5]):
        project_configs.append((f'{code}project{i}', project_status))

    projects = {}
    for i, (project_name, status) in enumerate(project_configs):
        # Create a Project (or get if it exists)
        project, created = Project.objects.get_or_create(
            name=project_name,
            defaults={'status': status}
        )
        # Store by index for easy access
        projects[f'project{i}'] = project
        # Also store by full name for easier access in tests
        projects[project_name] = project

        # Create project users and allocations for the first two projects only
        # (to avoid creating too much test data)
        if created and i < 2:
            for user in users:
                ProjectUser.objects.create(
                    user=user, project=project,
                    role=user_role, status=project_user_status)
            ProjectUser.objects.create(
                user=pi, project=project, role=pi_role,
                status=project_user_status)

            # Create a compute allocation for the Project
            allocation = Decimal(f'{i + 1}000.00')
            alloc_obj = create_project_allocation(project, allocation)

            # Create a compute allocation for each User on the Project
            for user in users:
                alloc_user_obj = create_user_project_allocation(
                    user, project, allocation / 2)

                allocation_attribute_type = AllocationAttributeType.objects.get(
                    name='Cluster Account Status')
                allocation_user_attribute, _ = \
                    AllocationUserAttribute.objects.get_or_create(
                        allocation_attribute_type=allocation_attribute_type,
                        allocation=alloc_user_obj.allocation,
                        allocation_user=alloc_user_obj.allocation_user)
                allocation_user_attribute.value = 'Active'
                allocation_user_attribute.save()

    # Create or get ExpiringTokens for each User
    tokens = {}
    for user in [superuser, staff_user, pi] + users:
        token, _ = ExpiringToken.objects.get_or_create(user=user)
        tokens[user.username] = token

    # Return all test data
    return {
        'superuser': superuser,
        'staff_user': staff_user,
        'pi': pi,
        'users': {f'user{i}': users[i] for i in range(3)},
        'projects': projects,
        'tokens': tokens,
    }
