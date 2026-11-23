from http import HTTPStatus

from django.contrib.auth.models import User
import pytest
from rest_framework.test import APIClient

from coldfront.core.project.models import (
    ProjectStatusChoice,
    ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)

URL = "/api/users/project_memberships/"


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures("api_test_data")
class TestProjectMembershipsAuth:
    """Test authentication requirements for POST /api/users/project_memberships/."""

    def test_no_token(self, api_test_data):
        client = APIClient()
        response = client.post(URL, {"users": []}, format="json")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_invalid_token(self, api_test_data):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token invalid")
        response = client.post(URL, {"users": []}, format="json")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_valid_token(self, api_client, api_test_data):
        response = api_client.post(URL, {"users": []}, format="json")
        assert response.status_code != HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures("api_test_data")
class TestProjectMembershipsPermissions:
    """Test that only superusers or users with the explicit permission can access the endpoint."""

    def test_regular_user_forbidden(self, api_test_data):
        token = api_test_data["tokens"]["user0"]
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = client.post(URL, {"users": []}, format="json")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_staff_without_perm_forbidden(self, api_test_data):
        """Staff without the explicit permission are denied."""
        token = api_test_data["tokens"]["staff"]
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = client.post(URL, {"users": []}, format="json")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_superuser_allowed(self, api_client, api_test_data):
        response = api_client.post(URL, {"users": []}, format="json")
        assert response.status_code != HTTPStatus.FORBIDDEN

    def test_user_with_perm_allowed(self, api_test_data):
        """A non-superuser granted can_view_project_memberships is allowed."""
        from django.contrib.auth.models import Permission

        user0 = api_test_data["users"]["user0"]
        perm = Permission.objects.get(codename="can_view_project_memberships")
        user0.user_permissions.add(perm)
        token = api_test_data["tokens"]["user0"]
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = client.post(URL, {"users": []}, format="json")
        assert response.status_code != HTTPStatus.FORBIDDEN


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures("api_test_data")
class TestProjectMembershipsValidation:
    """Test request body validation."""

    def test_unknown_username_returns_400(self, api_client, api_test_data):
        response = api_client.post(URL, {"users": ["does_not_exist"]}, format="json")
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert "unknown_users" in response.json()
        assert "does_not_exist" in response.json()["unknown_users"]

    def test_unknown_username_lists_all_unknown(self, api_client, api_test_data):
        response = api_client.post(
            URL, {"users": ["no_such_user_a", "no_such_user_b"]}, format="json"
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        data = response.json()
        assert set(data["unknown_users"]) == {"no_such_user_a", "no_such_user_b"}

    def test_non_list_users_returns_400(self, api_client, api_test_data):
        response = api_client.post(URL, {"users": "alice"}, format="json")
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_string_username_returns_400(self, api_client, api_test_data):
        response = api_client.post(URL, {"users": [1]}, format="json")
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert "users" in response.json()

    def test_empty_users_list_returns_200(self, api_client, api_test_data):
        response = api_client.post(URL, {"users": []}, format="json")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == []

    def test_usernames_are_stripped(self, api_client, api_test_data):
        """Leading/trailing whitespace in usernames is stripped."""
        user0 = api_test_data["users"]["user0"]
        response = api_client.post(
            URL, {"users": [f"  {user0.username}  "]}, format="json"
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json()[0]["user"] == user0.username

    def test_duplicate_usernames_deduplicated(self, api_client, api_test_data):
        """Duplicate usernames produce a single result entry."""
        user0 = api_test_data["users"]["user0"]
        response = api_client.post(
            URL, {"users": [user0.username, user0.username]}, format="json"
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.json()) == 1


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures("api_test_data")
class TestProjectMembershipsDefaultResponse:
    """Test the default (normalized) response."""

    def test_returns_pk_list(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        response = api_client.post(URL, {"users": [user0.username]}, format="json")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["user"] == user0.username
        assert isinstance(data[0]["projects"], list)
        for pk in data[0]["projects"]:
            assert isinstance(pk, int)

    def test_default_status_is_active(self, api_client, api_test_data):
        """Without ?status=, only Active memberships are returned."""
        user0 = api_test_data["users"]["user0"]
        project0 = api_test_data["projects"]["project0"]

        # Add a Removed membership for user0 on project0
        removed_status = ProjectUserStatusChoice.objects.get(name="Removed")
        pu = ProjectUser.objects.get(user=user0, project=project0)
        pu.status = removed_status
        pu.save()

        response = api_client.post(URL, {"users": [user0.username]}, format="json")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert project0.pk not in data[0]["projects"]

    def test_user_with_no_active_memberships(self, api_client, api_test_data):
        """A user with no Active memberships returns projects: []."""
        User.objects.get_or_create(
            username="no_projects", defaults={"email": "np@nonexistent.com"}
        )
        response = api_client.post(URL, {"users": ["no_projects"]}, format="json")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data[0]["user"] == "no_projects"
        assert data[0]["projects"] == []

    def test_input_order_preserved(self, api_client, api_test_data):
        """Response entries appear in the same order as input usernames."""
        usernames = ["user2", "user0", "user1"]
        response = api_client.post(URL, {"users": usernames}, format="json")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert [entry["user"] for entry in data] == usernames


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures("api_test_data")
class TestProjectMembershipsStatusFilter:
    """Test ?status= query parameter filtering."""

    def test_single_non_default_status(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        project0 = api_test_data["projects"]["project0"]

        # Change user0's membership on project0 to Removed
        removed_status = ProjectUserStatusChoice.objects.get(name="Removed")
        pu = ProjectUser.objects.get(user=user0, project=project0)
        pu.status = removed_status
        pu.save()

        response = api_client.post(
            f"{URL}?status=Removed", {"users": [user0.username]}, format="json"
        )
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert project0.pk in data[0]["projects"]

    def test_multiple_statuses(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        project0 = api_test_data["projects"]["project0"]
        project1 = api_test_data["projects"]["project1"]

        # project0: Active, project1: Removed
        removed_status = ProjectUserStatusChoice.objects.get(name="Removed")
        pu1 = ProjectUser.objects.get(user=user0, project=project1)
        pu1.status = removed_status
        pu1.save()

        response = api_client.post(
            f"{URL}?status=Active&status=Removed",
            {"users": [user0.username]},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        project_ids = data[0]["projects"]
        assert project0.pk in project_ids
        assert project1.pk in project_ids

    def test_explicit_active_matches_default(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]

        default_response = api_client.post(
            URL, {"users": [user0.username]}, format="json"
        )
        explicit_response = api_client.post(
            f"{URL}?status=Active", {"users": [user0.username]}, format="json"
        )

        assert default_response.json() == explicit_response.json()


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures("api_test_data")
class TestProjectMembershipsExpand:
    """Test ?expand=project query parameter."""

    def test_expand_returns_objects(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        response = api_client.post(
            f"{URL}?expand=project", {"users": [user0.username]}, format="json"
        )
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        for project_entry in data[0]["projects"]:
            assert isinstance(project_entry, dict)
            assert "id" in project_entry
            assert "name" in project_entry
            assert "pis" in project_entry

    def test_pis_is_list(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        response = api_client.post(
            f"{URL}?expand=project", {"users": [user0.username]}, format="json"
        )
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        for project_entry in data[0]["projects"]:
            assert isinstance(project_entry["pis"], list)

    def test_pi_has_name_and_email(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        pi = api_test_data["pi"]
        response = api_client.post(
            f"{URL}?expand=project", {"users": [user0.username]}, format="json"
        )
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        pis = data[0]["projects"][0]["pis"]
        assert len(pis) >= 1
        pi_entry = pis[0]
        assert "name" in pi_entry
        assert "email" in pi_entry
        assert pi_entry["email"] == pi.email

    def test_multiple_pis_on_project(self, api_client, api_test_data):
        """A second PI on a project appears in the pis list."""
        from django.contrib.auth.models import User

        user0 = api_test_data["users"]["user0"]
        project0 = api_test_data["projects"]["project0"]

        pi2, _ = User.objects.get_or_create(
            username="pi2",
            defaults={
                "first_name": "Dr.",
                "last_name": "Jones",
                "email": "pi2@nonexistent.com",
            },
        )
        pi_role = ProjectUserRoleChoice.objects.get(name="Principal Investigator")
        active_status = ProjectUserStatusChoice.objects.get(name="Active")
        ProjectUser.objects.get_or_create(
            user=pi2,
            project=project0,
            defaults={"role": pi_role, "status": active_status},
        )

        response = api_client.post(
            f"{URL}?expand=project", {"users": [user0.username]}, format="json"
        )
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        project0_entry = next(p for p in data[0]["projects"] if p["id"] == project0.pk)
        assert len(project0_entry["pis"]) >= 2
        emails = {p["email"] for p in project0_entry["pis"]}
        assert "pi2@nonexistent.com" in emails

    def test_removed_pi_excluded(self, api_client, api_test_data):
        """A PI whose project membership is not Active does not appear in pis."""
        from django.contrib.auth.models import User

        user0 = api_test_data["users"]["user0"]
        project0 = api_test_data["projects"]["project0"]

        removed_pi, _ = User.objects.get_or_create(
            username="removed_pi",
            defaults={
                "first_name": "Former",
                "last_name": "PI",
                "email": "removed_pi@nonexistent.com",
            },
        )
        pi_role = ProjectUserRoleChoice.objects.get(name="Principal Investigator")
        removed_status = ProjectUserStatusChoice.objects.get(name="Removed")
        ProjectUser.objects.get_or_create(
            user=removed_pi,
            project=project0,
            defaults={"role": pi_role, "status": removed_status},
        )

        response = api_client.post(
            f"{URL}?expand=project", {"users": [user0.username]}, format="json"
        )
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        project0_entry = next(p for p in data[0]["projects"] if p["id"] == project0.pk)
        emails = {p["email"] for p in project0_entry["pis"]}
        assert "removed_pi@nonexistent.com" not in emails

    def test_no_expand_returns_pks(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        response = api_client.post(URL, {"users": [user0.username]}, format="json")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        for pk in data[0]["projects"]:
            assert isinstance(pk, int)


def _set_membership_status(user, project, status_name):
    pu = ProjectUser.objects.get(user=user, project=project)
    pu.status = ProjectUserStatusChoice.objects.get(name=status_name)
    pu.save()


def _add_pi(project, username, status_name):
    pi, _ = User.objects.get_or_create(
        username=username,
        defaults={
            "first_name": "Other",
            "last_name": "PI",
            "email": f"{username}@nonexistent.com",
        },
    )
    ProjectUser.objects.get_or_create(
        user=pi,
        project=project,
        defaults={
            "role": ProjectUserRoleChoice.objects.get(name="Principal Investigator"),
            "status": ProjectUserStatusChoice.objects.get(name=status_name),
        },
    )
    return pi


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures("api_test_data")
class TestProjectMembershipsMembershipFilter:
    """Test ?membership= query parameter filtering."""

    def _project_ids(self, api_client, user, query=""):
        response = api_client.post(
            f"{URL}{query}", {"users": [user.username]}, format="json"
        )
        assert response.status_code == HTTPStatus.OK
        return set(response.json()[0]["projects"])

    def test_default_includes_pending_remove(self, api_client, api_test_data):
        """A user is still a current member while a removal is pending."""
        user0 = api_test_data["users"]["user0"]
        project0 = api_test_data["projects"]["project0"]
        _set_membership_status(user0, project0, "Pending - Remove")
        assert project0.pk in self._project_ids(api_client, user0)

    def test_current_past_all(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        project0 = api_test_data["projects"]["project0"]
        project1 = api_test_data["projects"]["project1"]
        _set_membership_status(user0, project1, "Removed")

        current = self._project_ids(api_client, user0, "?membership=current")
        past = self._project_ids(api_client, user0, "?membership=past")
        all_ = self._project_ids(api_client, user0, "?membership=all")

        assert project0.pk in current and project1.pk not in current
        assert past == {project1.pk}
        assert all_ == current | past

    def test_default_matches_current(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        assert self._project_ids(api_client, user0) == self._project_ids(
            api_client, user0, "?membership=current"
        )

    @pytest.mark.parametrize("status_name", ["Denied", "Pending - Add"])
    def test_all_excludes_never_members(self, api_client, api_test_data, status_name):
        user0 = api_test_data["users"]["user0"]
        project0 = api_test_data["projects"]["project0"]
        _set_membership_status(user0, project0, status_name)
        assert project0.pk not in self._project_ids(
            api_client, user0, "?membership=all"
        )

    def test_invalid_membership_returns_400(self, api_client, api_test_data):
        response = api_client.post(
            f"{URL}?membership=ever", {"users": []}, format="json"
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert "membership" in response.json()

    def test_membership_with_status_returns_400(self, api_client, api_test_data):
        response = api_client.post(
            f"{URL}?membership=all&status=Active", {"users": []}, format="json"
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert "membership" in response.json()

    def test_unknown_status_name_returns_400(self, api_client, api_test_data):
        response = api_client.post(
            f"{URL}?status=removed", {"users": []}, format="json"
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json() == {"unknown_statuses": ["removed"]}


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures("api_test_data")
class TestProjectMembershipsExpandedFields:
    """Test the status and role fields added to expanded projects."""

    def _project_entry(self, api_client, user, project, query="?expand=project"):
        response = api_client.post(
            f"{URL}{query}", {"users": [user.username]}, format="json"
        )
        assert response.status_code == HTTPStatus.OK
        return next(p for p in response.json()[0]["projects"] if p["id"] == project.pk)

    def test_project_fields(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        project0 = api_test_data["projects"]["project0"]
        entry = self._project_entry(api_client, user0, project0)
        assert entry["project_status"] == "Active"
        assert entry["role"] == "User"
        assert entry["membership_status"] == "Active"

    def test_past_membership_status(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        project0 = api_test_data["projects"]["project0"]
        _set_membership_status(user0, project0, "Removed")
        entry = self._project_entry(
            api_client, user0, project0, "?expand=project&membership=all"
        )
        assert entry["membership_status"] == "Removed"

    def test_pi_fields(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        pi = api_test_data["pi"]
        project0 = api_test_data["projects"]["project0"]
        entry = self._project_entry(api_client, user0, project0)
        assert {
            "username": pi.username,
            "name": pi.get_full_name(),
            "email": pi.email,
            "status": "Active",
        } in entry["pis"]


@pytest.mark.django_db
@pytest.mark.component
@pytest.mark.usefixtures("api_test_data")
class TestProjectMembershipsPisFilter:
    """Test ?pis= query parameter filtering."""

    def _pi_usernames(self, api_client, user, project, query):
        response = api_client.post(
            f"{URL}?expand=project{query}", {"users": [user.username]}, format="json"
        )
        assert response.status_code == HTTPStatus.OK
        entry = next(p for p in response.json()[0]["projects"] if p["id"] == project.pk)
        return {p["username"] for p in entry["pis"]}

    def test_default_excludes_removed_pi(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        project0 = api_test_data["projects"]["project0"]
        _add_pi(project0, "removed_pi", "Removed")
        assert "removed_pi" not in self._pi_usernames(api_client, user0, project0, "")

    def test_current_includes_pending_remove_pi(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        project0 = api_test_data["projects"]["project0"]
        _add_pi(project0, "leaving_pi", "Pending - Remove")
        assert "leaving_pi" in self._pi_usernames(
            api_client, user0, project0, "&pis=current"
        )

    def test_all_includes_removed_pi(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        pi = api_test_data["pi"]
        project0 = api_test_data["projects"]["project0"]
        _add_pi(project0, "removed_pi", "Removed")
        assert {pi.username, "removed_pi"} <= self._pi_usernames(
            api_client, user0, project0, "&pis=all"
        )

    def test_all_excludes_denied_pi(self, api_client, api_test_data):
        user0 = api_test_data["users"]["user0"]
        project0 = api_test_data["projects"]["project0"]
        _add_pi(project0, "denied_pi", "Denied")
        assert "denied_pi" not in self._pi_usernames(
            api_client, user0, project0, "&pis=all"
        )

    def test_retired_project_history(self, api_client, api_test_data):
        """A retired project, with its PI and members removed, still
        reports its former PI under membership=all&pis=all."""
        user0 = api_test_data["users"]["user0"]
        pi = api_test_data["pi"]
        project0 = api_test_data["projects"]["project0"]
        project0.status = ProjectStatusChoice.objects.get(name="Inactive")
        project0.save()
        _set_membership_status(user0, project0, "Removed")
        _set_membership_status(pi, project0, "Removed")

        response = api_client.post(
            f"{URL}?expand=project&membership=all&pis=all",
            {"users": [user0.username]},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK
        entry = next(
            p for p in response.json()[0]["projects"] if p["id"] == project0.pk
        )
        assert entry["project_status"] == "Inactive"
        assert entry["membership_status"] == "Removed"
        assert {"username": pi.username, "status": "Removed"}.items() <= next(
            p for p in entry["pis"] if p["username"] == pi.username
        ).items()

    def test_invalid_pis_returns_400(self, api_client, api_test_data):
        response = api_client.post(
            f"{URL}?expand=project&pis=past", {"users": []}, format="json"
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert "pis" in response.json()
