import pytest

from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.user.models import ExpiringToken
from coldfront.core.user.models import UserProfile
from django.contrib.auth.models import User


@pytest.fixture
def api_test_data(django_db_setup, db):
    """Create test data for project membership API tests."""
    staff_user, _ = User.objects.get_or_create(
        username='staff',
        defaults={'email': 'staff@nonexistent.com', 'is_staff': True})

    superuser, _ = User.objects.get_or_create(
        username='superuser',
        defaults={
            'email': 'superuser@nonexistent.com',
            'is_superuser': True,
            'is_staff': True,
        })
    if not superuser.is_superuser:
        superuser.is_superuser = True
        superuser.is_staff = True
        superuser.save()

    pi, _ = User.objects.get_or_create(
        username='pi',
        defaults={
            'first_name': 'Dr.',
            'last_name': 'Smith',
            'email': 'pi@nonexistent.com',
        })
    UserProfile.objects.get_or_create(user=pi)

    users = []
    for i in range(3):
        user, _ = User.objects.get_or_create(
            username=f'user{i}',
            defaults={'email': f'user{i}@nonexistent.com'})
        UserProfile.objects.get_or_create(user=user)
        users.append(user)

    active_project_status = ProjectStatusChoice.objects.get(name='Active')
    active_user_status = ProjectUserStatusChoice.objects.get(name='Active')
    user_role = ProjectUserRoleChoice.objects.get(name='User')
    pi_role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')

    projects = {}
    for i in range(2):
        project, created = Project.objects.get_or_create(
            name=f'test-project-{i}',
            defaults={'status': active_project_status,
                      'title': f'Test Project {i}'})
        projects[f'project{i}'] = project

        if created:
            for user in users:
                ProjectUser.objects.create(
                    user=user, project=project,
                    role=user_role, status=active_user_status)
            ProjectUser.objects.create(
                user=pi, project=project,
                role=pi_role, status=active_user_status)

    tokens = {}
    for user in [superuser, staff_user, pi] + users:
        token, _ = ExpiringToken.objects.get_or_create(user=user)
        tokens[user.username] = token

    return {
        'superuser': superuser,
        'staff_user': staff_user,
        'pi': pi,
        'users': {f'user{i}': users[i] for i in range(3)},
        'projects': projects,
        'tokens': tokens,
    }
