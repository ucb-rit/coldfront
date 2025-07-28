"""
Utility class for tracking project join request statuses.
Provides a unified interface to determine the current status of a user's
project join and cluster access request.
"""
from enum import Enum
from typing import Optional, Dict, Any, List
import logging

from django.contrib.auth.models import User
from django.db.models import Q

from coldfront.core.allocation.models import ClusterAccessRequest
from coldfront.core.project.models import (
    Project, ProjectUser, ProjectUserJoinRequest, ProjectUserStatusChoice
)
from coldfront.core.utils.tracking import ModelBasedTracker, TrackingStep

logger = logging.getLogger(__name__)


class JoinRequestStatus(Enum):
    """Enumeration of possible join request statuses."""
    REQUEST_SENT = "Request Sent"
    PI_APPROVED_QUEUED = "PI Approved & Queued"
    ADMIN_PROCESSING = "Admin Processing"
    ACCESS_GRANTED = "Access Granted"
    DIRECTLY_ADDED = "Directly Added by PI"
    ERROR = "Error"
    NO_REQUEST = "No Request"


class JoinRequestTracker(ModelBasedTracker):
    """
    Tracks the status of a user's project join request and cluster access.

    This class consolidates the logic for determining where a user is in the
    project join and cluster access flow.
    """

    def __init__(self, user: User, project: Project):
        super().__init__(user, project)
        self.project = project  # Keep backward compatibility
        self._project_user = None
        self._join_request = None
        self._cluster_access_request = None

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the user's join request.

        Maintains backward compatibility with the original interface.

        Returns:
            Dict containing status information for template usage
        """
        result = super().get_status()
        return result.to_dict()

    def _load_data(self):
        """Load relevant data for status determination."""
        # Get ProjectUser
        try:
            self._project_user = ProjectUser.objects.get(
                user=self.user,
                project=self.project
            )
        except ProjectUser.DoesNotExist:
            self._project_user = None

        # Get latest join request if exists
        if self._project_user:
            join_requests = ProjectUserJoinRequest.objects.filter(
                project_user=self._project_user
            ).order_by('-created')
            self._join_request = join_requests.first() if join_requests.exists() else None

            # Get cluster access request
            allocation = self.project.allocation_set.filter(
                resources__name__icontains='Compute',
                status__name__in=['Active', 'New', 'Renewal Requested']
            ).first()

            if allocation:
                try:
                    allocation_user = allocation.allocationuser_set.get(user=self.user)
                    cluster_requests = ClusterAccessRequest.objects.filter(
                        allocation_user=allocation_user
                    ).order_by('-created')
                    self._cluster_access_request = cluster_requests.first() if cluster_requests.exists() else None
                except:
                    self._cluster_access_request = None

    def _determine_status(self) -> JoinRequestStatus:
        """Determine the current status based on loaded data."""
        if not self._project_user:
            return JoinRequestStatus.NO_REQUEST

        # Check if user was directly added (no join request)
        if not self._join_request and self._project_user.status.name == 'Active':
            return JoinRequestStatus.DIRECTLY_ADDED

        # Check join request status
        if self._project_user.status.name == 'Pending - Add':
            return JoinRequestStatus.REQUEST_SENT

        if self._project_user.status.name == 'Denied':
            return JoinRequestStatus.NO_REQUEST

        # User is active, check cluster access
        if self._project_user.status.name == 'Active':
            if not self._cluster_access_request:
                return JoinRequestStatus.PI_APPROVED_QUEUED

            cluster_status = self._cluster_access_request.status.name
            if cluster_status in ['Pending - Add', 'Processing']:
                if cluster_status == 'Processing':
                    return JoinRequestStatus.ADMIN_PROCESSING
                else:
                    return JoinRequestStatus.PI_APPROVED_QUEUED
            elif cluster_status == 'Complete':
                return JoinRequestStatus.ACCESS_GRANTED
            elif cluster_status == 'Denied':
                return JoinRequestStatus.PI_APPROVED_QUEUED  # Show as queued if cluster denied

        return JoinRequestStatus.ERROR

    def _get_status_message(self, status: JoinRequestStatus) -> str:
        """Get a human-readable message for the status."""
        messages = {
            JoinRequestStatus.REQUEST_SENT: "Your request to join the project has been sent and is awaiting approval.",
            JoinRequestStatus.PI_APPROVED_QUEUED: "Your request has been approved by the PI and is queued for cluster access setup.",
            JoinRequestStatus.ADMIN_PROCESSING: "Administrators are processing your cluster access request.",
            JoinRequestStatus.ACCESS_GRANTED: "You have been granted access to the cluster under this project.",
            JoinRequestStatus.DIRECTLY_ADDED: "You were directly added to this project by a PI or manager.",
            JoinRequestStatus.ERROR: "Unable to determine the status of your request.",
            JoinRequestStatus.NO_REQUEST: "No active request found for this project."
        }
        return messages.get(status, "Unknown status")

    def _get_status_details(self, status: JoinRequestStatus) -> Optional[Dict[str, Any]]:
        """Get additional details about the current status."""
        details = {}

        if self._join_request:
            details['request_date'] = self._join_request.created
            details['reason'] = self._join_request.reason

        if self._project_user:
            details['project_user_status'] = self._project_user.status.name
            details['role'] = self._project_user.role.name

        if self._cluster_access_request:
            details['cluster_request_status'] = self._cluster_access_request.status.name
            details['cluster_request_date'] = self._cluster_access_request.request_time

        return details if details else None

    def _get_progress_steps(self, current_status: JoinRequestStatus) -> List[TrackingStep]:
        """Get the progress steps with their completion status."""
        if current_status == JoinRequestStatus.DIRECTLY_ADDED:
            return [
                TrackingStep(
                    label='Directly Added by PI',
                    completed=True,
                    current=False
                ),
                TrackingStep(
                    label='Admin Processing',
                    completed=self._cluster_access_request and self._cluster_access_request.status.name == 'Complete',
                    current=self._cluster_access_request and self._cluster_access_request.status.name == 'Processing'
                ),
                TrackingStep(
                    label='Access Granted',
                    completed=self._cluster_access_request and self._cluster_access_request.status.name == 'Complete',
                    current=False
                )
            ]
        else:
            return [
                TrackingStep(
                    label='Request Sent',
                    completed=current_status.value != 'No Request',
                    current=current_status == JoinRequestStatus.REQUEST_SENT
                ),
                TrackingStep(
                    label='PI Approved & Queued',
                    completed=current_status in [
                        JoinRequestStatus.PI_APPROVED_QUEUED,
                        JoinRequestStatus.ADMIN_PROCESSING,
                        JoinRequestStatus.ACCESS_GRANTED
                    ],
                    current=current_status == JoinRequestStatus.PI_APPROVED_QUEUED
                ),
                TrackingStep(
                    label='Admin Processing',
                    completed=current_status in [
                        JoinRequestStatus.ADMIN_PROCESSING,
                        JoinRequestStatus.ACCESS_GRANTED
                    ],
                    current=current_status == JoinRequestStatus.ADMIN_PROCESSING
                ),
                TrackingStep(
                    label='Access Granted',
                    completed=current_status == JoinRequestStatus.ACCESS_GRANTED,
                    current=False
                )
            ]

    def _can_view_status(self) -> bool:
        """Determine if the user can view the status for this project."""
        # User can view if they have an active join request or have been added to the project
        return self._project_user is not None

    def get_error_status(self) -> JoinRequestStatus:
        """Get the error status enum value."""
        return JoinRequestStatus.ERROR

    def get_default_error_message(self) -> str:
        """Get the default error message for project join requests."""
        return "Our system encountered an issue gathering the join status of your project, please contact support."