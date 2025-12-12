import pytest
from http import HTTPStatus

from rest_framework.test import APIClient

from coldfront.core.project.models import Project


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures('api_test_data')
class TestProjectViewSetList:
    """Test GET /api/projects/"""

    def test_authorization_token_required(self, api_client, api_test_data):
        """Test that requests without an authorization token are
        rejected."""
        url = '/api/projects/'

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
        """Test that admin users and read-only access work correctly."""
        url = '/api/projects/'

        users_permissions = [
            ('user0', True),  # Read-only allowed
            ('staff', True),
            ('superuser', True),
        ]

        for username, should_succeed in users_permissions:
            client = APIClient()
            token = api_test_data['tokens'][username]
            client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
            response = client.get(url)

            if should_succeed:
                assert response.status_code == HTTPStatus.OK
            else:
                assert response.status_code == HTTPStatus.FORBIDDEN

    def test_list_returns_all_projects(self, api_client, api_test_data):
        """Test that listing returns all projects ordered by id."""
        url = '/api/projects/'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        total_projects = Project.objects.count()
        assert json['count'] == total_projects

        # Verify projects are ordered by id
        projects = Project.objects.order_by('id')
        for i, result in enumerate(json['results'][:len(projects)]):
            assert result['id'] == projects[i].pk

    def test_filter_by_status(self, api_client, api_test_data):
        """Test filtering by status query parameter."""
        url = '/api/projects/?status=Active'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        active_count = Project.objects.filter(status__name='Active').count()
        assert json['count'] == active_count

        # Verify all returned projects have Active status
        for result in json['results']:
            project = Project.objects.get(pk=result['id'])
            assert project.status.name == 'Active'

    def test_filter_by_name(self, api_client, api_test_data):
        """Test filtering by name query parameter."""
        project0 = api_test_data['projects']['project0']
        url = f'/api/projects/?name={project0.name}'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        assert json['count'] == 1
        assert json['results'][0]['name'] == project0.name

    def test_filter_by_allowance_type(self, api_client, api_test_data):
        """Test filtering by allowance_type query parameter."""
        # Get the first project and extract its code prefix
        project0 = api_test_data['projects']['project0']
        code = project0.name.split('project')[0]  # e.g., 'ac_' from 'ac_project0'

        # Test filtering for this code
        url = f'/api/projects/?allowance_type={code}'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        expected_count = Project.objects.filter(name__istartswith=code).count()
        assert json['count'] == expected_count
        assert json['count'] >= 1  # Should have at least one project with this code

        # Verify all returned projects start with the expected code
        for result in json['results']:
            assert result['name'].startswith(code)

        # Test filtering for another code if we have more than one type
        if len(api_test_data['projects']) > 1:
            project1 = api_test_data['projects']['project1']
            code2 = project1.name.split('project')[0]

            url = f'/api/projects/?allowance_type={code2}'
            response = api_client.get(url)
            assert response.status_code == HTTPStatus.OK

            json = response.json()
            expected_count = Project.objects.filter(name__istartswith=code2).count()
            assert json['count'] == expected_count

            # Verify all returned projects start with the expected code
            for result in json['results']:
                assert result['name'].startswith(code2)

    def test_filter_with_multiple_allowance_types(self, api_client, api_test_data):
        """Test filtering with multiple allowance_type values."""
        # Get unique codes from the test projects
        codes = set()
        for project_key in ['project0', 'project1', 'project2', 'project3', 'project4']:
            if project_key in api_test_data['projects']:
                project = api_test_data['projects'][project_key]
                code = project.name.split('project')[0]
                codes.add(code)

        codes_list = list(codes)

        # Test with the first two codes if we have them
        if len(codes_list) >= 2:
            code1, code2 = codes_list[0], codes_list[1]
            url = f'/api/projects/?allowance_type={code1}&allowance_type={code2}'
            response = api_client.get(url)
            assert response.status_code == HTTPStatus.OK

            json = response.json()
            # Count projects with either code
            count1 = Project.objects.filter(name__istartswith=code1).count()
            count2 = Project.objects.filter(name__istartswith=code2).count()
            combined_count = count1 + count2
            assert json['count'] == combined_count

            # Verify all returned projects start with one of the expected codes
            for result in json['results']:
                assert result['name'].startswith(code1) or result['name'].startswith(code2)

        # Test with three codes if we have them
        if len(codes_list) >= 3:
            code1, code2, code3 = codes_list[0], codes_list[1], codes_list[2]
            url = f'/api/projects/?allowance_type={code1}&allowance_type={code2}&allowance_type={code3}'
            response = api_client.get(url)
            assert response.status_code == HTTPStatus.OK

            json = response.json()
            count1 = Project.objects.filter(name__istartswith=code1).count()
            count2 = Project.objects.filter(name__istartswith=code2).count()
            count3 = Project.objects.filter(name__istartswith=code3).count()
            combined_count = count1 + count2 + count3
            assert json['count'] == combined_count

            # Verify all returned projects match expected prefixes
            for result in json['results']:
                assert (result['name'].startswith(code1) or
                        result['name'].startswith(code2) or
                        result['name'].startswith(code3))

    def test_filter_combined(self, api_client, api_test_data):
        """Test filtering with multiple parameters combined."""
        # Get the first project's code
        project0 = api_test_data['projects']['project0']
        code = project0.name.split('project')[0]

        url = f'/api/projects/?status=Active&allowance_type={code}'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        combined_count = Project.objects.filter(
            status__name='Active',
            name__istartswith=code).count()
        assert json['count'] == combined_count

        # Verify all returned projects match both filters
        for result in json['results']:
            project = Project.objects.get(pk=result['id'])
            assert project.status.name == 'Active'
            assert result['name'].startswith(code)

    def test_response_format(self, api_client, api_test_data):
        """Test that the response has the expected structure and
        fields."""
        url = '/api/projects/'
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
            # ProjectSerializer uses '__all__' so it includes all model fields
            assert 'id' in result
            assert 'name' in result
            assert 'status' in result


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures('api_test_data')
class TestProjectViewSetDetail:
    """Test GET /api/projects/{id}/"""

    def test_authorization_token_required(self, api_client, api_test_data):
        """Test that requests without an authorization token are
        rejected."""
        project0 = api_test_data['projects']['project0']
        url = f'/api/projects/{project0.pk}/'

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
        """Test that admin users and read-only access work correctly."""
        project0 = api_test_data['projects']['project0']
        url = f'/api/projects/{project0.pk}/'

        users_permissions = [
            ('user0', True),  # Read-only allowed
            ('staff', True),
            ('superuser', True),
        ]

        for username, should_succeed in users_permissions:
            client = APIClient()
            token = api_test_data['tokens'][username]
            client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
            response = client.get(url)

            if should_succeed:
                assert response.status_code == HTTPStatus.OK
            else:
                assert response.status_code == HTTPStatus.FORBIDDEN

    def test_retrieve_valid_project(self, api_client, api_test_data):
        """Test retrieving a valid project."""
        project0 = api_test_data['projects']['project0']

        url = f'/api/projects/{project0.pk}/'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        assert json['id'] == project0.pk
        assert json['name'] == project0.name
        assert json['status'] == project0.status.pk

    def test_retrieve_nonexistent_project(self, api_client, api_test_data):
        """Test that attempting to retrieve a nonexistent project
        returns 404."""
        nonexistent_id = 99999

        url = f'/api/projects/{nonexistent_id}/'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_response_format(self, api_client, api_test_data):
        """Test that the response has the expected structure and
        fields."""
        project0 = api_test_data['projects']['project0']

        url = f'/api/projects/{project0.pk}/'
        response = api_client.get(url)
        assert response.status_code == HTTPStatus.OK

        json = response.json()
        # ProjectSerializer uses '__all__' so it includes all model fields
        assert 'id' in json
        assert 'name' in json
        assert 'status' in json

        # Verify field types
        assert isinstance(json['id'], int)
        assert isinstance(json['name'], str)
