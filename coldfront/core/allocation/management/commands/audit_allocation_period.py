import os
import re

from abc import ABC
from abc import abstractmethod

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand

from flags.state import flag_enabled

from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.project.utils_.renewal_survey import get_renewal_survey_response
from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceAttributeType
from coldfront.core.resource.models import TimedResourceAttribute
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances
from coldfront.core.utils.mail import send_email_template


class Command(BaseCommand):

    help = (
        'Perform a series of checks on an AllocationPeriod to ensure '
        'that it is fully configured.')

    def add_arguments(self, parser):
        parser.add_argument(
            'allocation_period_name',
            help='The name of the AllocationPeriod to audit.',
            type=str)
        parser.add_argument(
            '--email',
            help=(
                'A space-separated list of email addresses to send result '
                'notifications to.'),
            nargs='+',
            type=str)

    def handle(self, *args, **options):
        allocation_period_name = options['allocation_period_name']

        auditor = None
        if allocation_period_name.startswith('Allowance Year'):
            auditor = YearlyAllocationPeriodReadinessAuditor(
                allocation_period_name)
        else:
            if flag_enabled('BRC_ONLY'):
                if allocation_period_name.startswith(
                        ('Spring', 'Summer', 'Fall')):
                    auditor = InstructionalAllocationPeriodReadinessAuditor(
                        allocation_period_name)

        if not auditor:
            raise ValueError(
                f'Unexpected AllocationPeriod name {allocation_period_name}.')

        auditor.run_checks()
        audit_successful = auditor.audit_successful()
        check_results = auditor.check_results

        for check_result in check_results:
            if check_result.success:
                self.stdout.write(
                    self.style.SUCCESS(f'(SUCCEEDED) {check_result.message}'))
            else:
                self.stderr.write(
                    self.style.ERROR(f'(FAILED) {check_result.message}'))

        emails = options.get('email', []) or []
        if emails:
            self._send_email(
                allocation_period_name, audit_successful, check_results, emails)

        if not audit_successful:
            raise AuditFailure(
                'Audit of AllocationPeriod "{allocation_period_name}" failed.')

    def _send_email(self, allocation_period_name, audit_successful,
                    check_results, emails):
        """Send an email to the given set of email addresses, notifying
        them of the audit results."""
        subject_prefix = f'AllocationPeriod "{allocation_period_name}" Audit'
        template_dir = 'email/audit_allocation_period'
        context = {
            'allocation_period_name': allocation_period_name,
            'check_results': check_results,
        }
        sender = settings.EMAIL_SENDER
        receiver_list = emails

        if audit_successful:
            subject = f'{subject_prefix}: Success'
            template_base_name = 'audit_success'
        else:
            subject = f'{subject_prefix}: Failure'
            template_base_name = 'audit_failure'

        template_name = os.path.join(template_dir, f'{template_base_name}.txt')
        html_template = os.path.join(template_dir, f'{template_base_name}.html')

        send_email_template(
            subject, template_name, context, sender, receiver_list,
            html_template=html_template)


class AuditFailure(Exception):
    """An exception denoting that the audit failed."""

    pass


class CheckResult(object):
    """An object containing the results of an individual audit check."""

    def __init__(self, success, message, html_message=None):
        self.success = success
        self.message = message
        self.html_message = html_message


class AllocationPeriodReadinessAuditor(ABC):
    """An object for checking that an AllocationPeriod is fully
    configured."""

    def __init__(self, period_name):
        self._allocation_period_name = period_name
        self._allocation_period = None
        self._check_results = []

    def audit_successful(self):
        if not self._check_results:
            raise Exception('The audit has not been run yet.')
        return all(result.success for result in self._check_results)

    @property
    def check_results(self):
        if not self._check_results:
            raise Exception('The audit has not been run yet.')
        return self._check_results

    def run_checks(self):
        results = []

        exists_result = self._check_exists()
        results.append(exists_result)

        service_units_defined_result = self._check_service_units_defined()
        results.append(service_units_defined_result)

        custom_check_results = self._run_custom_checks()
        for check_result in custom_check_results:
            check_result.html_message = check_result.html_message
            results.append(check_result)

        self._check_results = results
        return results

    def _check_exists(self):
        """Check whether an AllocationPeriod object with the name
        exists."""
        try:
            self._allocation_period = AllocationPeriod.objects.get(
                name=self._allocation_period_name)
        except AllocationPeriod.DoesNotExist:
            success = False
        else:
            success = True
        message, html_message = self._get_exists_messages()
        return CheckResult(success, message, html_message)

    def _check_service_units_defined(self):
        """Check whether each of the computing allowances associated
        with the AllocationPeriod has a number of service units defined
        to be allocated for the period."""
        message, html_message = self._get_service_units_defined_messages()

        if not self._allocation_period:
            return CheckResult(False, message, html_message)
        
        resource_attribute_type = ResourceAttributeType.objects.get(
            name='Service Units')

        success = True

        for allowance in self._get_associated_allowances():
            resource = Resource.objects.get(name=allowance)
            try:
                TimedResourceAttribute.objects.get(
                    resource_attribute_type=resource_attribute_type,
                    resource=resource,
                    start_date=self._allocation_period.start_date,
                    end_date=self._allocation_period.end_date)
            except TimedResourceAttribute.DoesNotExist:
                success = False

        return CheckResult(success, message, html_message)

    def _get_associated_allowances(self):
        """Return the names of allowances (Resources) associated with
        the period."""
        raise NotImplementedError

    def _get_exists_messages(self):
        message = 'Create an AllocationPeriod.'
        html_message = 'Create an <code>AllocationPeriod</code>.'
        return message, html_message

    def _get_service_units_defined_messages(self):
        allowances = ', '.join(self._get_associated_allowances())
        message = (
            f'Define service units to be allocated to each of the following '
            f'allowances during the AllocationPeriod: {allowances}.')
        html_message = (
            f'Define service units to be allocated to each of the following '
            f'allowances during the <code>AllocationPeriod</code>: '
            f'{allowances}.')
        return message, html_message

    @abstractmethod
    def _run_custom_checks(self):
        """Run additional checks."""
        raise NotImplementedError


class InstructionalAllocationPeriodReadinessAuditor(AllocationPeriodReadinessAuditor):
    """An object for checking that an AllocationPeriod representing an
    instructional period is fully configured."""

    def _get_associated_allowances(self):
        return [BRCAllowances.ICA]

    def _get_exists_messages(self):
        message, html_message = super()._get_exists_messages()
        url = self._get_url_to_ucb_academic_calendar_file()
        message += f' Refer to the UCB Academic Calendar: {url}.'
        html_message += (
            f'Refer to the <a href="{url}">UCB Academic Calendar</a>.')
        return message, html_message

    def _get_url_to_ucb_academic_calendar_file(self):
        """Return a URL to a PDF listing the instructional period that
        the AllocationPeriod represents."""
        url_format = (
            'https://registrar.berkeley.edu/wp-content/uploads/'
            'UCB_AcademicCalendar_{0}-{1}.pdf')

        match = re.search(r'\b\d{4}\b', self._allocation_period_name)
        if match:
            year = int(match.group())

        if self._allocation_period_name.startswith('Fall'):
            starting_year = year
        elif self._allocation_period_name.startswith(('Spring', 'Summer')):
            starting_year = year - 1

        ending_year_short = f'{(starting_year + 1) % 100:02}'

        return url_format.format(str(starting_year), ending_year_short)

    def _run_custom_checks(self):
        return []


class YearlyAllocationPeriodReadinessAuditor(AllocationPeriodReadinessAuditor):
    """An object for checking that an AllocationPeriod representing an
    allowance year is fully configured."""

    def _get_associated_allowances(self):
        if flag_enabled('BRC_ONLY'):
            return [BRCAllowances.FCA, BRCAllowances.PCA]
        elif flag_enabled('LRC_ONLY'):
            return [LRCAllowances.PCA]
        else:
            raise ImproperlyConfigured(
                'Exactly one of BRC_ONLY, LRC_ONLY should be enabled.')

    def _check_renewal_survey_configured(self):
        """Check whether the allowance renewal survey for the period is
        configured."""
        try:
            project_name = 'audit_project_name'
            pi_username = 'audit_pi_username'
            # If the survey is properly configured, a fetch of a survey response
            # should not raise an error.
            get_renewal_survey_response(
                self._allocation_period_name, project_name, pi_username)
        except Exception as e:
            success = False
        else:
            success = True

        message, html_message = self._get_renewal_survey_configured_messages()
        return CheckResult(success, message, html_message)

    def _get_renewal_survey_configured_messages(self):
        message = 'Configure the renewal survey.'
        html_message = message
        return message, html_message

    def _run_custom_checks(self):
        results = []

        survey_configured_result = self._check_renewal_survey_configured()
        results.append(survey_configured_result)

        return results
