"""Tests for ServiceUnitsUsageService."""

import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch

from coldfront.core.allocation.utils_.accounting_utils.services import (
    ServiceUnitsUsageService)


@pytest.mark.unit
class TestServiceUnitsUsageServiceUnit:
    """Unit tests for ServiceUnitsUsageService with mocked dependencies."""

    @patch('coldfront.core.allocation.utils_.accounting_utils.services.'
           'service_units_usage_service.is_primary_cluster_project')
    def test_get_usage_display_returns_unlimited_for_non_primary_cluster_project(
            self, mock_is_primary):
        """Test that non-primary cluster projects show unlimited."""
        mock_is_primary.return_value = False

        # Provide mock interface to prevent DB access
        mock_interface = Mock()
        service = ServiceUnitsUsageService(
            computing_allowance_interface=mock_interface)
        mock_project = Mock()
        mock_project.status.name = 'Active'

        result = service.get_usage_display(mock_project)

        assert result == ServiceUnitsUsageService.UNLIMITED_MESSAGE

    @patch('coldfront.core.allocation.utils_.accounting_utils.services.'
           'service_units_usage_service.is_primary_cluster_project')
    def test_get_usage_display_returns_na_for_inactive_project(
            self, mock_is_primary):
        """Test that inactive projects show N/A."""
        mock_is_primary.return_value = True

        # Provide mock interface to prevent DB access
        mock_interface = Mock()
        service = ServiceUnitsUsageService(
            computing_allowance_interface=mock_interface)
        mock_project = Mock()
        mock_project.status.name = 'Inactive'

        result = service.get_usage_display(mock_project)

        assert result == ServiceUnitsUsageService.N_A

    def test_get_usage_display_returns_recharge_message_for_recharge_allowance(
            self):
        """Test that recharge allowances show usage-based message."""
        # Mock computing allowance interface
        mock_interface = Mock()
        mock_allowance_obj = Mock()
        mock_interface.allowance_from_project.return_value = (
            mock_allowance_obj)

        # Mock computing allowance
        mock_computing_allowance = Mock()
        mock_computing_allowance.is_recharge_postpaid.return_value = True

        service = ServiceUnitsUsageService(
            computing_allowance_interface=mock_interface)

        mock_project = Mock()
        mock_project.status.name = 'Active'

        with patch(
            'coldfront.core.allocation.utils_.accounting_utils.services.'
            'service_units_usage_service.is_primary_cluster_project',
            return_value=True
        ):
            with patch(
                'coldfront.core.allocation.utils_.accounting_utils.services.'
                'service_units_usage_service.ComputingAllowance',
                return_value=mock_computing_allowance
            ):
                result = service.get_usage_display(mock_project)

        assert result == ServiceUnitsUsageService.RECHARGE_MESSAGE

    def test_get_usage_display_returns_unlimited_for_infinite_service_units(
            self):
        """Test that infinite service unit allowances show unlimited."""
        mock_interface = Mock()
        mock_allowance_obj = Mock()
        mock_interface.allowance_from_project.return_value = (
            mock_allowance_obj)

        mock_computing_allowance = Mock()
        mock_computing_allowance.is_recharge_postpaid.return_value = False
        mock_computing_allowance.has_infinite_service_units.return_value = (
            True)

        service = ServiceUnitsUsageService(
            computing_allowance_interface=mock_interface)

        mock_project = Mock()
        mock_project.status.name = 'Active'

        with patch(
            'coldfront.core.allocation.utils_.accounting_utils.services.'
            'service_units_usage_service.is_primary_cluster_project',
            return_value=True
        ):
            with patch(
                'coldfront.core.allocation.utils_.accounting_utils.services.'
                'service_units_usage_service.ComputingAllowance',
                return_value=mock_computing_allowance
            ):
                result = service.get_usage_display(mock_project)

        assert result == ServiceUnitsUsageService.UNLIMITED_MESSAGE

    @patch('coldfront.core.allocation.utils_.accounting_utils.services.'
           'service_units_usage_service.ComputingAllowance')
    @patch('coldfront.core.allocation.utils_.accounting_utils.services.'
           'service_units_usage_service.is_primary_cluster_project')
    def test_get_usage_display_returns_formatted_usage_for_normal_allocation(
            self, mock_is_primary, mock_computing_allowance_class):
        """Test normal allocation returns formatted usage string."""
        mock_is_primary.return_value = True

        mock_interface = Mock()
        mock_allowance_obj = Mock()
        mock_interface.allowance_from_project.return_value = (
            mock_allowance_obj)

        mock_computing_allowance = Mock()
        mock_computing_allowance.is_recharge_postpaid.return_value = False
        mock_computing_allowance.has_infinite_service_units.return_value = (
            False)
        mock_computing_allowance_class.return_value = mock_computing_allowance

        # Mock allocation attributes with proper relationship
        mock_allocation_attr = Mock()
        mock_allocation_attr.value = '1000'
        mock_allocation_attr_usage = Mock()
        mock_allocation_attr_usage.value = '750'
        # Link them together
        mock_allocation_attr.allocationattributeusage = mock_allocation_attr_usage

        service = ServiceUnitsUsageService(
            computing_allowance_interface=mock_interface)

        mock_project = Mock()
        mock_project.status.name = 'Active'

        result = service.get_usage_display(
            mock_project, mock_allocation_attr)

        # Should return formatted display like "750/1000 (75.00 %)"
        assert '750' in result
        assert '1000' in result
        assert '75.00' in result
        assert '%' in result

    def test_get_usage_display_returns_na_when_attribute_fetch_fails(self):
        """Test that failures in fetching attributes return N/A."""
        mock_interface = Mock()
        mock_allowance_obj = Mock()
        mock_interface.allowance_from_project.return_value = (
            mock_allowance_obj)

        mock_computing_allowance = Mock()
        mock_computing_allowance.is_recharge_postpaid.return_value = False
        mock_computing_allowance.has_infinite_service_units.return_value = (
            False)

        service = ServiceUnitsUsageService(
            computing_allowance_interface=mock_interface)

        mock_project = Mock()
        mock_project.status.name = 'Active'

        with patch(
            'coldfront.core.allocation.utils_.accounting_utils.services.'
            'service_units_usage_service.is_primary_cluster_project',
            return_value=True
        ):
            with patch(
                'coldfront.core.allocation.utils_.accounting_utils.services.'
                'service_units_usage_service.ComputingAllowance',
                return_value=mock_computing_allowance
            ):
                with patch.object(
                    service, '_get_allocation_attributes',
                    side_effect=Exception('Test error')
                ):
                    result = service.get_usage_display(mock_project)

        assert result == ServiceUnitsUsageService.N_A

    def test_get_usage_display_returns_failed_to_compute_on_calculation_error(
            self):
        """Test that calculation errors return failed to compute message."""
        mock_interface = Mock()
        mock_allowance_obj = Mock()
        mock_interface.allowance_from_project.return_value = (
            mock_allowance_obj)

        mock_computing_allowance = Mock()
        mock_computing_allowance.is_recharge_postpaid.return_value = False
        mock_computing_allowance.has_infinite_service_units.return_value = (
            False)

        # Mock allocation attributes with invalid values
        mock_allocation_attr = Mock()
        mock_allocation_attr.value = 'invalid'
        mock_allocation_attr_usage = Mock()
        mock_allocation_attr_usage.value = 'invalid'

        service = ServiceUnitsUsageService(
            computing_allowance_interface=mock_interface)

        mock_project = Mock()
        mock_project.status.name = 'Active'

        with patch(
            'coldfront.core.allocation.utils_.accounting_utils.services.'
            'service_units_usage_service.is_primary_cluster_project',
            return_value=True
        ):
            with patch(
                'coldfront.core.allocation.utils_.accounting_utils.services.'
                'service_units_usage_service.ComputingAllowance',
                return_value=mock_computing_allowance
            ):
                result = service.get_usage_display(
                    mock_project, mock_allocation_attr)

        assert result == ServiceUnitsUsageService.FAILED_TO_COMPUTE

    @patch('coldfront.core.allocation.utils_.accounting_utils.services.'
           'service_units_usage_service.is_primary_cluster_project')
    def test_should_display_usage_returns_false_for_unlimited(
            self, mock_is_primary):
        """Test should_display_usage returns False for unlimited message."""
        mock_is_primary.return_value = False

        # Provide mock interface to prevent DB access
        mock_interface = Mock()
        service = ServiceUnitsUsageService(
            computing_allowance_interface=mock_interface)
        mock_project = Mock()
        mock_project.status.name = 'Active'

        result = service.should_display_usage(mock_project)

        assert result is False

    @patch('coldfront.core.allocation.utils_.accounting_utils.services.'
           'service_units_usage_service.is_primary_cluster_project')
    def test_should_display_usage_returns_false_for_na(
            self, mock_is_primary):
        """Test should_display_usage returns False for N/A message."""
        mock_is_primary.return_value = True

        # Provide mock interface to prevent DB access
        mock_interface = Mock()
        service = ServiceUnitsUsageService(
            computing_allowance_interface=mock_interface)
        mock_project = Mock()
        mock_project.status.name = 'Inactive'

        result = service.should_display_usage(mock_project)

        assert result is False

    def test_should_display_usage_returns_false_for_recharge(self):
        """Test should_display_usage returns False for recharge message."""
        mock_interface = Mock()
        mock_allowance_obj = Mock()
        mock_interface.allowance_from_project.return_value = (
            mock_allowance_obj)

        mock_computing_allowance = Mock()
        mock_computing_allowance.is_recharge_postpaid.return_value = True

        service = ServiceUnitsUsageService(
            computing_allowance_interface=mock_interface)

        mock_project = Mock()
        mock_project.status.name = 'Active'

        with patch(
            'coldfront.core.allocation.utils_.accounting_utils.services.'
            'service_units_usage_service.is_primary_cluster_project',
            return_value=True
        ):
            with patch(
                'coldfront.core.allocation.utils_.accounting_utils.services.'
                'service_units_usage_service.ComputingAllowance',
                return_value=mock_computing_allowance
            ):
                result = service.should_display_usage(mock_project)

        assert result is False

    @patch('coldfront.core.allocation.utils_.accounting_utils.services.'
           'service_units_usage_service.ComputingAllowance')
    @patch('coldfront.core.allocation.utils_.accounting_utils.services.'
           'service_units_usage_service.is_primary_cluster_project')
    def test_should_display_usage_returns_true_for_normal_allocation(
            self, mock_is_primary, mock_computing_allowance_class):
        """Test should_display_usage returns True for normal allocations."""
        mock_is_primary.return_value = True

        mock_interface = Mock()
        mock_allowance_obj = Mock()
        mock_interface.allowance_from_project.return_value = (
            mock_allowance_obj)

        mock_computing_allowance = Mock()
        mock_computing_allowance.is_recharge_postpaid.return_value = False
        mock_computing_allowance.has_infinite_service_units.return_value = (
            False)
        mock_computing_allowance_class.return_value = mock_computing_allowance

        mock_allocation_attr = Mock()
        mock_allocation_attr.value = '1000'
        mock_allocation_attr_usage = Mock()
        mock_allocation_attr_usage.value = '750'
        # Link them together
        mock_allocation_attr.allocationattributeusage = mock_allocation_attr_usage

        service = ServiceUnitsUsageService(
            computing_allowance_interface=mock_interface)

        mock_project = Mock()
        mock_project.status.name = 'Active'

        result = service.should_display_usage(
            mock_project, mock_allocation_attr)

        assert result is True

    def test_no_usage_display_messages_constant_includes_all_special_cases(
            self):
        """Test that NO_USAGE_DISPLAY_MESSAGES contains all special cases."""
        assert ServiceUnitsUsageService.N_A in (
            ServiceUnitsUsageService.NO_USAGE_DISPLAY_MESSAGES)
        assert ServiceUnitsUsageService.FAILED_TO_COMPUTE in (
            ServiceUnitsUsageService.NO_USAGE_DISPLAY_MESSAGES)
        assert ServiceUnitsUsageService.RECHARGE_MESSAGE in (
            ServiceUnitsUsageService.NO_USAGE_DISPLAY_MESSAGES)
        assert ServiceUnitsUsageService.UNLIMITED_MESSAGE in (
            ServiceUnitsUsageService.NO_USAGE_DISPLAY_MESSAGES)
