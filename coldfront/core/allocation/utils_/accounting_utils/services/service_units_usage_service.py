from decimal import Decimal
from typing import Optional

from ..domain import AllowanceUsage

from coldfront.core.project.utils import is_primary_cluster_project
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface


class ServiceUnitsUsageService:
    """A service class for displaying service unit usage of a
    project."""

    N_A = 'N/A'
    FAILED_TO_COMPUTE = 'Failed to compute'
    RECHARGE_MESSAGE = 'Usage-based'
    UNLIMITED_MESSAGE = 'Unlimited'

    # Messages that indicate usage should not be displayed
    NO_USAGE_DISPLAY_MESSAGES = (
        N_A, FAILED_TO_COMPUTE, RECHARGE_MESSAGE, UNLIMITED_MESSAGE)

    def __init__(
            self,
            computing_allowance_interface: Optional[
                ComputingAllowanceInterface] = None):
        self._computing_allowance_interface = (
            computing_allowance_interface or ComputingAllowanceInterface())

    def get_usage_display(self, project, allocation_attribute=None) -> str:
        """Return a str representing the service unit usage for the
        given Project (and optional AllocationAttribute)."""
        # NOTE: These policy checks could be refactored into a domain
        # policy class if they become more complex.

        if not is_primary_cluster_project(project):
            return self.UNLIMITED_MESSAGE

        if project.status.name != 'Active':
            return self.N_A

        try:
            computing_allowance = self._get_computing_allowance(project)
        except Exception:
            return self.N_A

        special_display = self._handle_special_allowance_types(
            computing_allowance)
        if special_display:
            return special_display

        try:
            allocation_attribute, allocation_attribute_usage = (
                self._get_allocation_attributes(
                    project, allocation_attribute=allocation_attribute))
        except Exception:
            return self.N_A

        return self._calculate_usage_display(
            allocation_attribute, allocation_attribute_usage)

    def should_display_usage(self, project, allocation_attribute=None) -> bool:
        """Determine whether usage details should be displayed."""
        usage_display = self.get_usage_display(project, allocation_attribute)
        return usage_display not in self.NO_USAGE_DISPLAY_MESSAGES

    def _calculate_usage_display(
            self, allocation_attribute, allocation_attribute_usage) -> str:
        """Calculate and format usage display."""
        try:
            allowance = Decimal(allocation_attribute.value)
            usage = Decimal(allocation_attribute_usage.value)
            allowance_usage = AllowanceUsage(allowance=allowance, usage=usage)
            return allowance_usage.format_display()
        except Exception:
            return self.FAILED_TO_COMPUTE

    def _get_allocation_attributes(self, project, allocation_attribute=None):
        """Get or retrieve allocation attributes."""
        if allocation_attribute is None:
            from coldfront.api.statistics.utils import (
                get_accounting_allocation_objects)
            accounting_allocation_objects = (
                get_accounting_allocation_objects(project))
            allocation_attribute = (
                accounting_allocation_objects.allocation_attribute)
            allocation_attribute_usage = (
                accounting_allocation_objects.allocation_attribute_usage)
        else:
            assert hasattr(
                allocation_attribute, 'allocationattributeusage')
            allocation_attribute_usage = (
                allocation_attribute.allocationattributeusage)

        return allocation_attribute, allocation_attribute_usage

    def _get_computing_allowance(self, project) -> ComputingAllowance:
        """Retrieve the ComputingAllowance for the given Project."""
        allowance = (
            self._computing_allowance_interface.allowance_from_project(
                project))
        return ComputingAllowance(allowance)

    def _handle_special_allowance_types(
            self, computing_allowance: ComputingAllowance) -> Optional[str]:
        """Handle special allowance types (recharge, unlimited)."""
        if computing_allowance.is_recharge_postpaid():
            return self.RECHARGE_MESSAGE
        elif computing_allowance.has_infinite_service_units():
            return self.UNLIMITED_MESSAGE
        return None
