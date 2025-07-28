"""
Generic tracking framework for various request/process tracking needs.
Provides base classes that can be extended for specific tracking scenarios.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class TrackingStep:
    """Represents a single step in a tracking process."""

    def __init__(self, label: str, completed: bool = False, current: bool = False):
        self.label = label
        self.completed = completed
        self.current = current

    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for template usage."""
        return {
            'label': self.label,
            'completed': self.completed,
            'current': self.current
        }


class TrackingResult:
    """Holds the result of a tracking status query."""

    def __init__(
            self,
            status: Union[Enum, str],
            message: str,
            details: Optional[Dict[str, Any]] = None,
            error: Optional[str] = None,
            steps: Optional[List[TrackingStep]] = None,
            can_view: bool = True
    ):
        self.status = status
        self.message = message
        self.details = details or {}
        self.error = error
        self.steps = steps or []
        self.can_view = can_view

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for template usage."""
        return {
            'status': self.status,
            'message': self.message,
            'details': self.details,
            'error': self.error,
            'steps': [step.to_dict() for step in self.steps],
            'can_view': self.can_view
        }


class BaseStatus(Enum):
    """Base class for tracking status enums."""

    ERROR = "Error"
    NO_REQUEST = "No Request"

    @property
    def value_str(self) -> str:
        """Get the string value of the status."""
        return self.value


class BaseTracker(ABC):
    """
    Abstract base class for all tracking implementations.

    Subclasses should implement:
    - _load_data(): Load relevant data for status determination
    - _determine_status(): Determine current status based on loaded data
    - _get_status_message(): Get human-readable message for status
    - _get_status_details(): Get additional details about status
    - _get_progress_steps(): Get progress steps with completion status
    - _can_view_status(): Determine if user can view status
    """

    def __init__(self, *args, **kwargs):
        """Initialize tracker with required parameters."""
        self._error_message = None

    def get_status(self) -> TrackingResult:
        """
        Get the current tracking status.

        Returns:
            TrackingResult containing all status information
        """
        try:
            self._load_data()
            status = self._determine_status()
            steps = self._get_progress_steps(status)

            return TrackingResult(
                status=status,
                message=self._get_status_message(status),
                details=self._get_status_details(status),
                error=self._error_message,
                steps=steps,
                can_view=self._can_view_status()
            )
        except Exception as e:
            logger.exception(f"Error determining tracking status: {e}")
            return TrackingResult(
                status=self.get_error_status(),
                message="Unable to determine status",
                details=None,
                error=self.get_default_error_message(),
                steps=[],
                can_view=True
            )

    @abstractmethod
    def _load_data(self):
        """Load relevant data for status determination."""
        pass

    @abstractmethod
    def _determine_status(self) -> Enum:
        """Determine the current status based on loaded data."""
        pass

    @abstractmethod
    def _get_status_message(self, status: Enum) -> str:
        """Get a human-readable message for the status."""
        pass

    @abstractmethod
    def _get_status_details(self, status: Enum) -> Optional[Dict[str, Any]]:
        """Get additional details about the current status."""
        pass

    @abstractmethod
    def _get_progress_steps(self, current_status: Enum) -> List[TrackingStep]:
        """Get the progress steps with their completion status."""
        pass

    @abstractmethod
    def _can_view_status(self) -> bool:
        """Determine if the user can view the status."""
        pass

    def get_error_status(self) -> Enum:
        """Get the error status enum value."""
        return BaseStatus.ERROR

    def get_default_error_message(self) -> str:
        """Get the default error message."""
        return "Our system encountered an issue gathering the status, please contact support."

    def set_error_message(self, message: str):
        """Set a custom error message."""
        self._error_message = message


class ModelBasedTracker(BaseTracker):
    """
    Extended base class for trackers that work with Django models.
    Provides common patterns for model-based tracking.
    """

    def __init__(self, user, target_object, *args, **kwargs):
        """
        Initialize with user and target object.

        Args:
            user: The user whose status is being tracked
            target_object: The object being tracked (project, allocation, etc.)
        """
        super().__init__(*args, **kwargs)
        self.user = user
        self.target_object = target_object

    def _get_base_queryset_filters(self) -> Dict[str, Any]:
        """Get base filters for querysets (user, target_object, etc.)."""
        return {
            'user': self.user,
        }

    def _filter_by_status_names(self, queryset, status_names: List[str], status_field: str = 'status__name'):
        """Helper to filter queryset by status names."""
        filter_kwargs = {f'{status_field}__in': status_names}
        return queryset.filter(**filter_kwargs)

    def _get_latest_by_field(self, queryset, field: str = 'created'):
        """Get the latest object from queryset by specified field."""
        return queryset.order_by(f'-{field}').first()


def create_tracking_steps(step_definitions: List[Dict[str, Any]],
                          current_status: Enum,
                          status_progression: Dict[Enum, int]) -> List[TrackingStep]:
    """
    Helper function to create tracking steps based on definitions and current status.

    Args:
        step_definitions: List of step definitions with 'label' and 'status_values'
        current_status: Current status enum
        status_progression: Maps status enums to their progression order

    Returns:
        List of TrackingStep objects
    """
    steps = []
    current_order = status_progression.get(current_status, 0)

    for i, step_def in enumerate(step_definitions):
        step_order = i + 1
        completed = step_order < current_order
        current = step_order == current_order

        steps.append(TrackingStep(
            label=step_def['label'],
            completed=completed,
            current=current
        ))

    return steps