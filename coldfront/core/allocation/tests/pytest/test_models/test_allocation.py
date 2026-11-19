"""Tests for the Allocation model."""

from django.utils.safestring import SafeString
import pytest

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationAttributeType,
    AllocationStatusChoice,
    AttributeType,
)
from coldfront.core.project.models import Project, ProjectStatusChoice


@pytest.mark.django_db
@pytest.mark.component
class TestAllocationGetInformation:
    """Tests for ``Allocation.get_information``."""

    def test_attribute_values_are_escaped(self):
        """Attribute values containing HTML are escaped, not rendered."""
        project = Project.objects.create(
            name="test_project",
            title="test_project",
            status=ProjectStatusChoice.objects.get(name="Active"),
        )
        allocation = Allocation.objects.create(
            project=project,
            status=AllocationStatusChoice.objects.get(name="Active"),
        )
        attribute_type, _ = AttributeType.objects.get_or_create(name="Text")
        allocation_attribute_type, _ = AllocationAttributeType.objects.get_or_create(
            name="Cluster Directory Access",
            defaults={"attribute_type": attribute_type},
        )
        AllocationAttribute.objects.create(
            allocation=allocation,
            allocation_attribute_type=allocation_attribute_type,
            value="<script>alert(1)</script>",
        )

        information = allocation.get_information

        assert isinstance(information, SafeString)
        assert "<script>" not in information
        assert "Directory Name: &lt;script&gt;alert(1)&lt;/script&gt;" in information
