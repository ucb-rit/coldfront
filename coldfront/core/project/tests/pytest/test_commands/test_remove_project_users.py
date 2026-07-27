"""Tests for the remove_project_users management command."""

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
import pytest

from coldfront.core.project.models import (
    ProjectUser,
    ProjectUserRemovalRequest,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)


@pytest.mark.component
@pytest.mark.django_db
class TestRemoveProjectUsersCommand:
    """Tests for the remove_project_users management command."""

    def _make_user(self, username):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
        )

    def _add_user_to_project(self, user, project):
        """Add a user to a project with Active status and User role."""
        return ProjectUser.objects.create(
            project=project,
            user=user,
            role=ProjectUserRoleChoice.objects.get(name="User"),
            status=ProjectUserStatusChoice.objects.get(name="Active"),
        )

    def _write_input_file(self, tmp_path, usernames):
        f = tmp_path / "users.txt"
        f.write_text("\n".join(usernames) + "\n")
        return str(f)

    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------

    def test_unknown_requester_raises_command_error(self, tmp_path):
        """An unknown requester username raises CommandError immediately."""
        input_file = self._write_input_file(tmp_path, [])
        with pytest.raises(CommandError, match='Requester "no_such_user" not found'):
            call_command(
                "remove_project_users",
                input_file,
                requester="no_such_user",
            )

    def test_missing_input_file_raises_command_error(self, tmp_path):
        """A non-existent input file raises CommandError."""
        requester = self._make_user("req_missing_file")
        with pytest.raises(CommandError, match="not found"):
            call_command(
                "remove_project_users",
                str(tmp_path / "nonexistent.txt"),
                requester=requester.username,
            )

    def test_empty_input_file_exits_cleanly(self, tmp_path):
        """An empty input file creates no requests and raises no error."""
        requester = self._make_user("req_empty_file")
        input_file = self._write_input_file(tmp_path, [])
        call_command(
            "remove_project_users",
            input_file,
            requester=requester.username,
        )
        assert ProjectUserRemovalRequest.objects.count() == 0

    # -------------------------------------------------------------------------
    # Skip behaviour
    # -------------------------------------------------------------------------

    def test_unknown_username_skipped(self, tmp_path):
        """A username not in the database is skipped without raising."""
        requester = self._make_user("req_unknown_user")
        input_file = self._write_input_file(tmp_path, ["ghost_user"])
        call_command(
            "remove_project_users",
            input_file,
            requester=requester.username,
        )
        assert ProjectUserRemovalRequest.objects.count() == 0

    def test_user_with_no_active_memberships_skipped(self, tmp_path):
        """A user with no Active project memberships is skipped without raising."""
        requester = self._make_user("req_no_memberships")
        user = self._make_user("user_no_memberships")
        input_file = self._write_input_file(tmp_path, [user.username])
        call_command(
            "remove_project_users",
            input_file,
            requester=requester.username,
        )
        assert ProjectUserRemovalRequest.objects.count() == 0

    # -------------------------------------------------------------------------
    # Core behaviour
    # -------------------------------------------------------------------------

    def test_single_membership_creates_one_request(
        self, tmp_path, create_active_project_with_pi
    ):
        """A user with one Active membership gets one removal request."""
        pi = self._make_user("pi_single")
        project = create_active_project_with_pi("fc_cmd_single", pi)
        requester = self._make_user("req_single")
        user = self._make_user("user_single")
        self._add_user_to_project(user, project)

        input_file = self._write_input_file(tmp_path, [user.username])
        call_command(
            "remove_project_users",
            input_file,
            requester=requester.username,
        )
        assert (
            ProjectUserRemovalRequest.objects.filter(project_user__user=user).count()
            == 1
        )

    def test_multiple_memberships_create_multiple_requests(
        self, tmp_path, create_active_project_with_pi
    ):
        """A user with multiple Active memberships gets one request per project."""
        pi = self._make_user("pi_multi")
        project_a = create_active_project_with_pi("fc_cmd_multi_a", pi)
        project_b = create_active_project_with_pi("fc_cmd_multi_b", pi)
        requester = self._make_user("req_multi")
        user = self._make_user("user_multi")
        self._add_user_to_project(user, project_a)
        self._add_user_to_project(user, project_b)

        input_file = self._write_input_file(tmp_path, [user.username])
        call_command(
            "remove_project_users",
            input_file,
            requester=requester.username,
        )
        assert (
            ProjectUserRemovalRequest.objects.filter(project_user__user=user).count()
            == 2
        )

    def test_reason_stored_on_requests(self, tmp_path, create_active_project_with_pi):
        """The --reason value is persisted on each removal request."""
        pi = self._make_user("pi_reason")
        project = create_active_project_with_pi("fc_cmd_reason", pi)
        requester = self._make_user("req_reason")
        user = self._make_user("user_reason")
        self._add_user_to_project(user, project)

        input_file = self._write_input_file(tmp_path, [user.username])
        call_command(
            "remove_project_users",
            input_file,
            requester=requester.username,
            reason="End of semester.",
        )
        req = ProjectUserRemovalRequest.objects.get(project_user__user=user)
        assert req.reason == "End of semester."

    def test_duplicate_usernames_deduplicated(
        self, tmp_path, create_active_project_with_pi
    ):
        """Duplicate usernames in the input file are processed only once."""
        pi = self._make_user("pi_dedup")
        project = create_active_project_with_pi("fc_cmd_dedup", pi)
        requester = self._make_user("req_dedup")
        user = self._make_user("user_dedup")
        self._add_user_to_project(user, project)

        # Same username listed twice.
        input_file = self._write_input_file(tmp_path, [user.username, user.username])
        call_command(
            "remove_project_users",
            input_file,
            requester=requester.username,
        )
        assert (
            ProjectUserRemovalRequest.objects.filter(project_user__user=user).count()
            == 1
        )

    # -------------------------------------------------------------------------
    # Dry run
    # -------------------------------------------------------------------------

    def test_dry_run_creates_no_requests(self, tmp_path, create_active_project_with_pi):
        """With --dry_run, no database changes are made."""
        pi = self._make_user("pi_dry")
        project = create_active_project_with_pi("fc_cmd_dry", pi)
        requester = self._make_user("req_dry")
        user = self._make_user("user_dry")
        self._add_user_to_project(user, project)

        input_file = self._write_input_file(tmp_path, [user.username])
        call_command(
            "remove_project_users",
            input_file,
            requester=requester.username,
            dry_run=True,
        )
        assert (
            ProjectUserRemovalRequest.objects.filter(project_user__user=user).count()
            == 0
        )

    # -------------------------------------------------------------------------
    # Error path
    # -------------------------------------------------------------------------

    def test_runner_rejection_creates_no_request(
        self, tmp_path, create_active_project_with_pi
    ):
        """A runner rejection (e.g. removing a PI) creates no request and
        does not raise — the error is handled internally."""
        pi = self._make_user("pi_err")
        create_active_project_with_pi("fc_cmd_err", pi)
        requester = self._make_user("req_err")

        # Attempt to remove the PI — the runner blocks this.
        input_file = self._write_input_file(tmp_path, [pi.username])
        call_command(
            "remove_project_users",
            input_file,
            requester=requester.username,
        )
        assert ProjectUserRemovalRequest.objects.count() == 0
