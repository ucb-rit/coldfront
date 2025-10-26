"""Unit tests for project eligibility utilities."""

import pytest

from coldfront.core.project.models import Project
from coldfront.plugins.cluster_storage.utils import (
    is_project_eligible_for_cluster_storage,
)


@pytest.mark.unit
class TestProjectEligibilityForClusterStorage:
    """Test is_project_eligible_for_cluster_storage function."""

    def test_fca_project_is_eligible(
        self, db, project_status_choice_active
    ):
        """Test FCA (Faculty Computing Allowance) project is eligible."""
        # Create an FCA project (fc_ prefix)
        fca_project = Project.objects.create(
            name='fc_test_faculty',
            title='Test Faculty Project',
            status=project_status_choice_active
        )

        assert is_project_eligible_for_cluster_storage(fca_project) is True

    def test_ica_project_is_not_eligible(
        self, db, project_status_choice_active
    ):
        """Test ICA (Instructional Computing Allowance) project is not eligible."""
        # Create an ICA project (ic_ prefix)
        ica_project = Project.objects.create(
            name='ic_test_instructional',
            title='Test Instructional Project',
            status=project_status_choice_active
        )

        assert is_project_eligible_for_cluster_storage(ica_project) is False

    def test_pca_project_is_not_eligible(
        self, db, project_status_choice_active
    ):
        """Test PCA (Partner Computing Allowance) project is not eligible."""
        # Create a PCA project (pc_ prefix)
        pca_project = Project.objects.create(
            name='pc_test_partner',
            title='Test Partner Project',
            status=project_status_choice_active
        )

        assert is_project_eligible_for_cluster_storage(pca_project) is False

    def test_condo_project_is_not_eligible(
        self, db, project_status_choice_active
    ):
        """Test Condo project is not eligible."""
        # Create a Condo project (co_ prefix)
        condo_project = Project.objects.create(
            name='co_test_condo',
            title='Test Condo Project',
            status=project_status_choice_active
        )

        assert is_project_eligible_for_cluster_storage(condo_project) is False

    def test_recharge_project_is_not_eligible(
        self, db, project_status_choice_active
    ):
        """Test Recharge project is not eligible."""
        # Create a Recharge project (ac_ prefix for BRC)
        recharge_project = Project.objects.create(
            name='ac_test_recharge',
            title='Test Recharge Project',
            status=project_status_choice_active
        )

        assert is_project_eligible_for_cluster_storage(recharge_project) is False
