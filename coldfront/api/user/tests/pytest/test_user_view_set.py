from http import HTTPStatus

from django.contrib.auth.models import Permission, User
import pytest
from rest_framework.test import APIClient

URL = "/api/users/"


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures("api_test_data")
class TestUserViewSetList:
    """Test GET /api/users/"""

    def test_no_token(self):
        client = APIClient()
        response = client.get(URL)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_invalid_token(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token invalid")
        response = client.get(URL)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_regular_user_forbidden(self, api_test_data):
        """Regular users have no read access."""
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {api_test_data['tokens']['user0'].key}"
        )
        response = client.get(URL)
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_staff_and_superuser_allowed(self, api_test_data):
        """Staff and superusers have read access."""
        for key in ("staff", "superuser"):
            client = APIClient()
            client.credentials(
                HTTP_AUTHORIZATION=f"Token {api_test_data['tokens'][key].key}"
            )
            response = client.get(URL)
            assert response.status_code == HTTPStatus.OK, key

    def test_regular_user_with_view_profiles_perm_allowed(self, api_test_data):
        """Regular users with the can_view_user_profiles permission have read
        access."""
        user1 = api_test_data["users"]["user1"]
        user1.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="user", codename="can_view_user_profiles"
            )
        )
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {api_test_data['tokens']['user1'].key}"
        )
        response = client.get(URL)
        assert response.status_code == HTTPStatus.OK
        response = client.get(f"{URL}{user1.pk}/")
        assert response.status_code == HTTPStatus.OK

    def test_no_filter_returns_all_users(self, api_client):
        response = api_client.get(URL)
        assert response.status_code == HTTPStatus.OK
        assert response.json()["count"] == User.objects.count()

    def test_filter_single_username(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        response = api_client.get(URL, {"username": user0.username})
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["username"] == user0.username

    def test_filter_multiple_usernames(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        user1 = api_test_data["users"]["user1"]
        response = api_client.get(
            f"{URL}?username={user0.username}&username={user1.username}"
        )
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["count"] == 2
        returned = {r["username"] for r in data["results"]}
        assert returned == {user0.username, user1.username}

    def test_filter_unknown_username(self, api_client):
        response = api_client.get(URL, {"username": "does_not_exist"})
        assert response.status_code == HTTPStatus.OK
        assert response.json()["count"] == 0

    def test_response_fields(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        response = api_client.get(URL, {"username": user0.username})
        assert response.status_code == HTTPStatus.OK
        result = response.json()["results"][0]
        for field in ("username", "first_name", "last_name", "email", "last_login"):
            assert field in result
