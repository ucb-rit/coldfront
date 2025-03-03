from django.contrib.auth.models import User

from flags.state import flag_enabled

from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.models import ProjectUser
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.user.utils_.host_user_utils import is_lbl_employee


class ComputingAllowanceEligibilityManager(object):
    """A class for managing whether a User is eligible for a computing
    allowance of a given type, optionally under a particular
    AllocationPeriod. The following constraints apply:
        - On LRC, computing allowances may only be allocated to PIs who
          are LBL employees.
        - If the computing allowance is limited to one per PI and is
          periodic:
              - A PI may not have an existing renewal request with the
                same computing allowance type in the period.
              - A PI may not have an existing new project request with
                the same computing allowance type in the period.
              - A PI may not already have an active Project with the
                same computing allowance type, except in the case of
                renewal.
    """

    def __init__(self, computing_allowance, allocation_period=None):
        """Take a ComputingAllowance and an optional AllocationPeriod.
        The period is required if the allowance is periodic."""
        assert isinstance(computing_allowance, ComputingAllowance)
        self._computing_allowance = computing_allowance

        if allocation_period is not None:
            assert isinstance(allocation_period, AllocationPeriod)
        self._allocation_period = allocation_period

        if self._computing_allowance.is_periodic():
            assert self._allocation_period is not None

    def get_ineligible_users(self, is_renewal=False, pks_only=False):
        """Return a QuerySet of Users who are ineligible for the
        computing allowance. Optionally return a set of User primary
        keys instead."""
        ineligible_user_pks = set()

        if flag_enabled('LRC_ONLY'):
            non_lbl_employee_user_pks = {
                user.pk
                for user in User.objects.all()
                if not is_lbl_employee(user)}
            ineligible_user_pks.update(non_lbl_employee_user_pks)

        if self._computing_allowance.is_one_per_pi():

            if self._computing_allowance.is_periodic():

                existing_renewal_requests = self._existing_renewal_requests(
                    self._allocation_period)
                renewal_request_pi_pks = existing_renewal_requests.values_list(
                    'pi', flat=True)
                ineligible_user_pks.update(set(renewal_request_pi_pks))

                existing_new_project_requests = \
                    self._existing_new_project_requests(self._allocation_period)
                new_project_request_pi_pks = \
                    existing_new_project_requests.values_list('pi', flat=True)
                ineligible_user_pks.update(set(new_project_request_pi_pks))

                if not is_renewal:
                    existing_pi_project_users = \
                        self._existing_pi_project_users()
                    existing_pk_pks = existing_pi_project_users.values_list(
                        'user', flat=True)
                    ineligible_user_pks.update(set(existing_pk_pks))

        if pks_only:
            return ineligible_user_pks
        return User.objects.filter(pk__in=ineligible_user_pks)

    def is_user_eligible(self, user, is_renewal=False):
        """Return whether the given User is eligible for the computing
        allowance."""
        if flag_enabled('LRC_ONLY'):
            if not is_lbl_employee(user):
                return False

        if self._computing_allowance.is_one_per_pi():

            if self._computing_allowance.is_periodic():

                existing_renewal_requests = self._existing_renewal_requests(
                    user, self._allocation_period)
                if existing_renewal_requests.exists():
                    return False

                existing_new_project_requests = \
                    self._existing_new_project_requests(
                        user, self._allocation_period)
                if existing_new_project_requests.exists():
                    return False

                if not is_renewal:
                    existing_pi_project_users = \
                        self._existing_pi_project_users(user)
                    if existing_pi_project_users.exists():
                        return False

        return True

    def _existing_new_project_requests(self, allocation_period, pi=None):
        """Return a QuerySet of new project request objects:
            - Under the given AllocationPeriod
            - With the given computing allowance
            - With a status that would render the associated PI
              ineligible to make another one
            - Optionally belonging to the given PI
        """
        ineligible_statuses = self._ineligible_new_project_request_statuses()
        kwargs = {
            'allocation_period': allocation_period,
            'computing_allowance': self._computing_allowance.get_resource(),
            'status__in': ineligible_statuses,
        }
        if pi is not None:
            kwargs['pi'] = pi
        return SavioProjectAllocationRequest.objects.filter(**kwargs)

    def _existing_pi_project_users(self, pi=None):
        """Return a QuerySet of ProjectUser objects:
            - With the given computing allowance
            - With the "Principal Investigator" ProjectUser role
            - With the "Active" ProjectUser status
            - With a project status that would render the associated PIs
              ineligible to be the PI of another project with the same
              computing allowance
            - Optionally belonging to the given PI
        """
        computing_allowance_interface = ComputingAllowanceInterface()
        project_prefix = computing_allowance_interface.code_from_name(
            self._computing_allowance.get_name())
        
        ineligible_project_statuses = self._ineligible_project_statuses()
        kwargs = {
            'project__name__startswith': project_prefix,
            'role__name': 'Principal Investigator',
            'status__name': 'Active',
            'project__status__in': ineligible_project_statuses,
        }
        if pi is not None:
            kwargs['user'] = pi
        return ProjectUser.objects.filter(**kwargs)

    def _existing_renewal_requests(self, allocation_period, pi=None):
        """Return a QuerySet of AllocationRenewalRequest objects:
            - Under the given AllocationPeriod
            - With the given computing allowance
            - With a status that would render the associated PI
              ineligible to make another one
            - Optionally belonging to the given PI
        """
        ineligible_statuses = self._ineligible_renewal_request_statuses()
        kwargs = {
            'allocation_period': allocation_period,
            'computing_allowance': self._computing_allowance.get_resource(),
            'status__in': ineligible_statuses,
        }
        if pi is not None:
            kwargs['pi'] = pi
        return AllocationRenewalRequest.objects.filter(**kwargs)

    @staticmethod
    def _ineligible_new_project_request_statuses():
        """Return a QuerySet of ProjectAllocationRequestStatusChoice
        objects. If a PI has a relevant request with one of these
        statuses, they are considered ineligible for a computing
        allowance."""
        return ProjectAllocationRequestStatusChoice.objects.exclude(
            name='Denied')

    @staticmethod
    def _ineligible_project_statuses():
        """Return a QuerySet of ProjectStatusChoice objects. If the
        computing allowance is one-per-PI, and a user is the PI of a
        project with one of these statuses, they are considered
        ineligible to receive another computing allowance of the same
        type."""
        return ProjectStatusChoice.objects.exclude(
            name__in=['Archived', 'Denied'])

    @staticmethod
    def _ineligible_renewal_request_statuses():
        """Return a QuerySet of AllocationRenewalRequestStatusChoice
        objects. If a PI has a relevant request with one of these
        statuses, they are considered ineligible for a computing
        allowance."""
        return AllocationRenewalRequestStatusChoice.objects.exclude(
            name='Denied')
