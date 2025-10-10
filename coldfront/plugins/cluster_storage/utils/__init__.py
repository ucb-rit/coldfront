from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface


def is_project_eligible_for_cluster_storage(project):
    """Return whether the given Project is eligible to request cluster
    storage."""
    computing_allowance_interface = ComputingAllowanceInterface()
    allowance = computing_allowance_interface.allowance_from_project(project)
    computing_allowance = ComputingAllowance(allowance)
    allowance_name = computing_allowance.get_name()
    # It is assumed that this plugin will only be enabled on BRC instances.
    return allowance_name == BRCAllowances.FCA


__all__ = ['is_project_eligible_for_cluster_storage']
