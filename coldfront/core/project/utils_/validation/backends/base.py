from abc import ABC
from abc import abstractmethod


class BaseValidatorBackend(ABC):
    """An interface for checking whether the Google renewal survey has been
    completed using any of a number of backends."""

    @abstractmethod
    def is_renewal_survey_completed(self, sheet_id, survey_data, key):
        """Return whether the Google renewal survey has been completed"""
        pass