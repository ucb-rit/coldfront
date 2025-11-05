from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface

from coldfront.plugins.cluster_storage.services.eligibility_service import StorageRequestEligibilityService


def has_eligible_pi_for_storage_request(project):
    """Return whether the given Project has at least one PI that is
    eligible to submit a storage request."""
    eligibility_service = StorageRequestEligibilityService()
    pis = project.pis(active_only=True)
    for pi in pis:
        is_eligible, _ = eligibility_service.is_eligible_for_request(pi)
        if is_eligible:
            return True
    return False


def is_project_eligible_for_cluster_storage(project):
    """Return whether the given Project is eligible to request cluster
    storage."""
    computing_allowance_interface = ComputingAllowanceInterface()
    allowance = computing_allowance_interface.allowance_from_project(project)
    computing_allowance = ComputingAllowance(allowance)
    allowance_name = computing_allowance.get_name()
    # It is assumed that this plugin will only be enabled on BRC instances.
    return allowance_name == BRCAllowances.FCA


__all__ = [
    'has_eligible_pi_for_storage_request',
    'is_project_eligible_for_cluster_storage',
]
