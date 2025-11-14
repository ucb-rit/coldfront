import pytest
from http import HTTPStatus

from django.contrib.auth.models import User
from rest_framework.test import APIClient

from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures('api_test_data')
class TestProjectUserViewSetList:
    """Test GET /api/projects/{pk}/users/"""

    def test_authorization_token_required(self, api_client, api_test_data):
        """Test that requests without an authorization token are
        rejected."""
        project0 = api_test_data['projects']['project0']
        url = f'/api/projects/{project0.pk}/users/'

        # No credentials
        client = APIClient()
        response = client.get(url)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert 'Authentication credentials were not provided.' in response.json()['detail']

        # Invalid credentials
        client.credentials(HTTP_AUTHORIZATION='Token invalid')
        response = client.get(url)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert 'Invalid token.' in response.json()['detail']

        # Valid credentials
        response = api_client.get(url)
        assert response.status_code != HTTPStatus.UNAUTHORIZED

    def test_permissions(self, api_test_data):
        """Test that only superusers and staff can access the
        endpoint."""
        project0 = api_test_data['projects']['project0']
        url = f'/api/projects/{project0.pk}/users/'

        users_permissions = [
            ('user0', False),
            ('staff', True),
            ('superuser', True),
        ]

        for username, should_succeed in users_permissions:
            client = APIClient()
            token = api_test_data['tokens'][username]
            client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
            response = client.get(url)

            if should_succeed:
                assert response.status_code != HTTPStatus.FORBIDDEN
            else:
                assert response.status_code == HTTPStatus.FORBIDDEN

    def test_nested_url_filters_by_project(self, api_client, api_test_data):
        """Test that the nested URL only returns users for the
        specified project."""
        project0 = api_test_data['projects']['project0']

        # Get users for project0
        url = f'/api/projects/{project0.pk}/users/'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        project0_user_count = ProjectUser.objects.filter(
            project=project0).count()
        assert json['count'] == project0_user_count

        # Verify all returned users belong to project0 and are ordered by id
        project_users = ProjectUser.objects.filter(
            project=project0).order_by('id')
        for i, result in enumerate(json['results']):
            assert result['id'] == project_users[i].pk
            project_user = ProjectUser.objects.get(pk=result['id'])
            assert project_user.project == project0

    def test_filter_by_status(self, api_client, api_test_data):
        """Test filtering by status query parameter."""
        project0 = api_test_data['projects']['project0']

        # Create a new user not already on the project
        new_user = User.objects.create(
            username='removed_user', email='removed@nonexistent.com')

        # Create a removed user on project0
        inactive_status = ProjectUserStatusChoice.objects.get(name='Removed')
        user_role = ProjectUserRoleChoice.objects.get(name='User')
        inactive_pu = ProjectUser.objects.create(
            user=new_user, project=project0,
            role=user_role, status=inactive_status)

        url = f'/api/projects/{project0.pk}/users/?status=Active'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        active_count = ProjectUser.objects.filter(
            project=project0, status__name='Active').count()
        assert json['count'] == active_count

        # Verify all returned users have Active status
        for result in json['results']:
            assert result['status'] == 'Active'

    def test_filter_by_role(self, api_client, api_test_data):
        """Test filtering by role query parameter."""
        project0 = api_test_data['projects']['project0']

        url = f'/api/projects/{project0.pk}/users/?role=User'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        user_count = ProjectUser.objects.filter(
            project=project0, role__name='User').count()
        assert json['count'] == user_count

        # Verify all returned users have User role
        for result in json['results']:
            assert result['role'] == 'User'

    def test_filter_by_status_and_role(self, api_client, api_test_data):
        """Test filtering by both status and role query parameters."""
        project0 = api_test_data['projects']['project0']

        url = f'/api/projects/{project0.pk}/users/?status=Active&role=User'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        filtered_count = ProjectUser.objects.filter(
            project=project0,
            status__name='Active',
            role__name='User').count()
        assert json['count'] == filtered_count

        # Verify all returned users match both filters
        for result in json['results']:
            assert result['status'] == 'Active'
            assert result['role'] == 'User'

    def test_filter_with_multiple_values(self, api_client, api_test_data):
        """Test filtering with multiple values for status or role."""
        project0 = api_test_data['projects']['project0']

        url = (f'/api/projects/{project0.pk}/users/'
               f'?role=User&role=Principal Investigator')
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        # Should return both Users and PIs
        filtered_count = ProjectUser.objects.filter(
            project=project0,
            role__name__in=['User', 'Principal Investigator']).count()
        assert json['count'] == filtered_count

    def test_response_format(self, api_client, api_test_data):
        """Test that the response has the expected structure and
        fields."""
        project0 = api_test_data['projects']['project0']

        url = f'/api/projects/{project0.pk}/users/'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        # Check pagination structure
        assert 'count' in json
        assert 'next' in json
        assert 'previous' in json
        assert 'results' in json

        # Check individual result fields
        if json['results']:
            result = json['results'][0]
            expected_fields = {'id', 'user', 'project', 'role', 'status'}
            assert set(result.keys()) == expected_fields

            # Verify field types
            assert isinstance(result['id'], int)
            assert isinstance(result['user'], int)
            assert isinstance(result['project'], int)
            assert isinstance(result['role'], str)
            assert isinstance(result['status'], str)


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures('api_test_data')
class TestProjectUserViewSetDetail:
    """Test GET /api/projects/{pk}/users/{id}/"""

    def test_authorization_token_required(self, api_client, api_test_data):
        """Test that requests without an authorization token are
        rejected."""
        project0 = api_test_data['projects']['project0']
        project_user = ProjectUser.objects.filter(project=project0).first()
        url = f'/api/projects/{project0.pk}/users/{project_user.pk}/'

        # No credentials
        client = APIClient()
        response = client.get(url)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # Invalid credentials
        client.credentials(HTTP_AUTHORIZATION='Token invalid')
        response = client.get(url)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # Valid credentials
        response = api_client.get(url)
        assert response.status_code != HTTPStatus.UNAUTHORIZED

    def test_permissions(self, api_test_data):
        """Test that only superusers and staff can access the
        endpoint."""
        project0 = api_test_data['projects']['project0']
        project_user = ProjectUser.objects.filter(project=project0).first()
        url = f'/api/projects/{project0.pk}/users/{project_user.pk}/'

        users_permissions = [
            ('user0', False),
            ('staff', True),
            ('superuser', True),
        ]

        for username, should_succeed in users_permissions:
            client = APIClient()
            token = api_test_data['tokens'][username]
            client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
            response = client.get(url)

            if should_succeed:
                assert response.status_code != HTTPStatus.FORBIDDEN
            else:
                assert response.status_code == HTTPStatus.FORBIDDEN

    def test_retrieve_valid_project_user(self, api_client, api_test_data):
        """Test retrieving a valid project user."""
        project0 = api_test_data['projects']['project0']
        project_user = ProjectUser.objects.filter(project=project0).first()

        url = f'/api/projects/{project0.pk}/users/{project_user.pk}/'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        assert json['id'] == project_user.pk
        assert json['user'] == project_user.user.pk
        assert json['project'] == project_user.project.pk
        assert json['role'] == project_user.role.name
        assert json['status'] == project_user.status.name

    def test_retrieve_nonexistent_project_user(self, api_client, api_test_data):
        """Test that attempting to retrieve a nonexistent project user
        returns 404."""
        project0 = api_test_data['projects']['project0']
        nonexistent_id = 99999

        url = f'/api/projects/{project0.pk}/users/{nonexistent_id}/'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_response_format(self, api_client, api_test_data):
        """Test that the response has the expected structure and
        fields."""
        project0 = api_test_data['projects']['project0']
        project_user = ProjectUser.objects.filter(project=project0).first()

        url = f'/api/projects/{project0.pk}/users/{project_user.pk}/'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        expected_fields = {'id', 'user', 'project', 'role', 'status'}
        assert set(json.keys()) == expected_fields

        # Verify field types
        assert isinstance(json['id'], int)
        assert isinstance(json['user'], int)
        assert isinstance(json['project'], int)
        assert isinstance(json['role'], str)
        assert isinstance(json['status'], str)
