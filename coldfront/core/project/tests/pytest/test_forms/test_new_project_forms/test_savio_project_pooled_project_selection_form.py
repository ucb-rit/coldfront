"""Tests for SavioProjectPooledProjectSelectionForm and PooledProjectChoiceField."""

import pytest
from django.contrib.auth.models import User

from coldfront.core.project.forms_.new_project_forms.request_forms import (
    PooledProjectChoiceField,
    SavioProjectPooledProjectSelectionForm,
)
from coldfront.core.project.models import (
    Project,
    ProjectStatusChoice,
    ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)
from coldfront.core.resource.models import Resource


# =============================================================================
# Helpers
# =============================================================================

def _make_project(name, status_name='Active'):
    status = ProjectStatusChoice.objects.get(name=status_name)
    return Project.objects.create(name=name, title=name, status=status)


def _make_pi_project_user(project, user):
    role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')
    status = ProjectUserStatusChoice.objects.get(name='Active')
    return ProjectUser.objects.create(
        project=project, user=user, role=role, status=status)


# =============================================================================
# PooledProjectChoiceField.label_from_instance()
# =============================================================================

@pytest.mark.component
@pytest.mark.django_db
class TestPooledProjectChoiceFieldLabelFromInstance:
    """Tests for PooledProjectChoiceField.label_from_instance()."""

    def test_label_includes_project_name_and_pi_names(self):
        """Label should be '<project name> (<PI first last>)'."""
        project = _make_project('fc_test')
        pi = User.objects.create_user(
            username='pi_user', email='pi@example.com',
            first_name='Ada', last_name='Lovelace')
        _make_pi_project_user(project, pi)

        # Simulate the prefetch by setting the to_attr list directly.
        project.pi_project_users = list(
            ProjectUser.objects.filter(
                project=project, role__name='Principal Investigator'
            ).select_related('user'))

        field = PooledProjectChoiceField(queryset=Project.objects.none())
        assert field.label_from_instance(project) == 'fc_test (Ada Lovelace)'

    def test_label_sorts_multiple_pi_names_alphabetically(self):
        """PIs should appear in alphabetical order by full name."""
        project = _make_project('fc_multi')
        for first, last in [('Zara', 'Zebra'), ('Alan', 'Turing')]:
            user = User.objects.create_user(
                username=f'{first.lower()}_{last.lower()}',
                email=f'{first.lower()}@example.com',
                first_name=first, last_name=last)
            _make_pi_project_user(project, user)

        project.pi_project_users = list(
            ProjectUser.objects.filter(
                project=project, role__name='Principal Investigator'
            ).select_related('user'))

        field = PooledProjectChoiceField(queryset=Project.objects.none())
        assert field.label_from_instance(project) == (
            'fc_multi (Alan Turing, Zara Zebra)')

    def test_label_falls_back_to_queryset_when_no_prefetch_attr(self):
        """Without pi_project_users, label_from_instance() should fall back
        to a DB query and still return a correct label."""
        project = _make_project('fc_fallback')
        pi = User.objects.create_user(
            username='fallback_pi', email='fallback@example.com',
            first_name='Grace', last_name='Hopper')
        _make_pi_project_user(project, pi)

        # Do NOT set pi_project_users — exercise the fallback path.
        field = PooledProjectChoiceField(queryset=Project.objects.none())
        assert field.label_from_instance(project) == (
            'fc_fallback (Grace Hopper)')


# =============================================================================
# SavioProjectPooledProjectSelectionForm — prefetch correctness
# =============================================================================

@pytest.mark.component
@pytest.mark.django_db
class TestSavioProjectPooledProjectSelectionFormPrefetch:
    """Tests that the form queryset attaches pi_project_users via Prefetch."""

    def test_queryset_projects_have_pi_project_users_attribute(self):
        """Each project in the queryset should have a pi_project_users list
        populated by the Prefetch, avoiding per-project queries."""
        fca = Resource.objects.get(name='Faculty Computing Allowance')
        project = _make_project('fc_prefetch_test')
        pi = User.objects.create_user(
            username='prefetch_pi', email='prefetch@example.com',
            first_name='Charles', last_name='Babbage')
        _make_pi_project_user(project, pi)

        form = SavioProjectPooledProjectSelectionForm(
            computing_allowance=fca)
        projects = list(form.fields['project'].queryset)

        assert any(p.pk == project.pk for p in projects)
        for p in projects:
            assert hasattr(p, 'pi_project_users'), (
                f'Project {p.name} is missing the pi_project_users attribute')
            assert isinstance(p.pi_project_users, list)

    def test_label_rendering_issues_no_extra_queries_per_project(
            self, django_assert_num_queries):
        """Rendering labels for N projects should issue O(1) DB queries,
        not one per project."""
        fca = Resource.objects.get(name='Faculty Computing Allowance')
        for i in range(5):
            project = _make_project(f'fc_bulk_{i}')
            pi = User.objects.create_user(
                username=f'pi_{i}', email=f'pi_{i}@example.com',
                first_name=f'First{i}', last_name=f'Last{i}')
            _make_pi_project_user(project, pi)

        form = SavioProjectPooledProjectSelectionForm(
            computing_allowance=fca)
        field = form.fields['project']

        # Evaluate the queryset and render all labels. With the Prefetch fix,
        # this should require exactly 2 queries: one for projects, one for the
        # batch prefetch of PI project users (plus their users via
        # select_related, which is folded into the same query via JOIN).
        with django_assert_num_queries(2):
            labels = [field.label_from_instance(p)
                      for p in field.queryset]

        assert len(labels) == 5
