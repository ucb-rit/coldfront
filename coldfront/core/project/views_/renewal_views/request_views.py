from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.utils import prorated_allocation_amount
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectAllocationPeriodForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectDetailsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectSurveyForm
from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalPISelectionForm
from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalPoolingPreferenceForm
from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalProjectSelectionForm
from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalSurveyForm
from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalGoogleSurveyForm
from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalReviewAndSubmitForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.permissions_utils import is_user_manager_or_pi_of_project
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.project.utils_.renewal_utils import get_pi_active_unique_project
from coldfront.core.project.utils_.renewal_utils import has_non_denied_renewal_request
from coldfront.core.project.utils_.renewal_utils import send_new_allocation_renewal_request_admin_notification_email
from coldfront.core.project.utils_.renewal_utils import send_new_allocation_renewal_request_pi_notification_email
from coldfront.core.project.utils_.renewal_utils import send_new_allocation_renewal_request_pooling_notification_email
from coldfront.core.project.utils_.renewal_utils import get_renewal_survey
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils import get_primary_compute_resource
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.user.utils import access_agreement_signed
from coldfront.core.utils.common import session_wizard_all_form_data
from coldfront.core.utils.common import utc_now_offset_aware

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.base import TemplateView

from flags.state import flag_enabled
from formtools.wizard.views import SessionWizardView

import logging


logger = logging.getLogger(__name__)


class AllocationRenewalLandingView(LoginRequiredMixin, UserPassesTestMixin,
                                   TemplateView):
    template_name = 'project/project_renewal/request_landing.html'

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        if access_agreement_signed(self.request.user):
            return True
        message = (
            'You must sign the User Access Agreement before you can request '
            'to renew an allowance.')
        messages.error(self.request, message)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        allowances = []
        yearly_allowance_names = []
        renewal_supported_allowance_names = []
        renewal_not_supported_allowance_names = []
        interface = ComputingAllowanceInterface()
        for allowance in sorted(interface.allowances(), key=lambda a: a.pk):
            wrapper = ComputingAllowance(allowance)
            allowance_name = wrapper.get_name()
            entry = {
                'name': allowance_name,
                'name_long': interface.name_long_from_name(allowance_name),
            }
            allowances.append(entry)
            if wrapper.is_yearly():
                name_short = interface.name_short_from_name(allowance_name)
                yearly_allowance_names.append(f'{name_short}s')
            if wrapper.is_renewable():
                if wrapper.is_renewal_supported():
                    renewal_supported_allowance_names.append(allowance_name)
                else:
                    renewal_not_supported_allowance_names.append(
                        allowance_name)

        context['allowances'] = allowances
        context['yearly_allowance_names'] = ', '.join(yearly_allowance_names)
        context['renewal_supported_allowance_names'] = \
            renewal_supported_allowance_names
        context['renewal_not_supported_allowance_names'] = \
            renewal_not_supported_allowance_names

        return context


class AllocationRenewalMixin(object):

    success_message = (
        'Thank you for your submission. It will be reviewed and processed by '
        'administrators.')
    error_message = 'Unexpected failure. Please contact an administrator.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO: Set this dynamically when supporting other types.
        if flag_enabled('BRC_ONLY'):
            self.computing_allowance = Resource.objects.get(
                name=BRCAllowances.FCA)
        elif flag_enabled('LRC_ONLY'):
            self.computing_allowance = Resource.objects.get(
                name=LRCAllowances.PCA)
        else:
            raise ImproperlyConfigured(
                'One of the following flags must be enabled: BRC_ONLY, '
                'LRC_ONLY.')
        self.interface = ComputingAllowanceInterface()

    @staticmethod
    def create_allocation_renewal_request(requester, pi, computing_allowance,
                                          allocation_period, pre_project,
                                          post_project, 
                                          new_project_request=None):
        """Create a new AllocationRenewalRequest."""
        request_kwargs = dict()
        request_kwargs['requester'] = requester
        request_kwargs['pi'] = pi
        request_kwargs['computing_allowance'] = computing_allowance
        request_kwargs['allocation_period'] = allocation_period
        request_kwargs['status'] = \
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review')
        # request_kwargs['renewal_survey_answers'] = renewal_survey_answers
        request_kwargs['pre_project'] = pre_project
        request_kwargs['post_project'] = post_project
        request_kwargs['new_project_request'] = new_project_request
        request_kwargs['request_time'] = utc_now_offset_aware()
        return AllocationRenewalRequest.objects.create(**request_kwargs)

    @staticmethod
    def send_emails(request_obj):
        """Send emails to various recipients based on the given, newly-
        created AllocationRenewalRequest."""
        # Send a notification email to admins.
        try:
            send_new_allocation_renewal_request_admin_notification_email(
                request_obj)
        except Exception as e:
            logger.error(f'Failed to send notification email. Details:\n')
            logger.exception(e)
        # Send a notification email to the PI if the requester differs.
        if request_obj.requester != request_obj.pi:
            try:
                send_new_allocation_renewal_request_pi_notification_email(
                    request_obj)
            except Exception as e:
                logger.error(
                    f'Failed to send notification email. Details:\n')
                logger.exception(e)
        # If applicable, send a notification email to the managers and PIs of
        # the project being requested to pool with.
        if (request_obj.pi not in request_obj.post_project.pis() and
                not request_obj.new_project_request):
            try:
                send_new_allocation_renewal_request_pooling_notification_email(
                    request_obj)
            except Exception as e:
                logger.error(
                    f'Failed to send notification email. Details:\n')
                logger.exception(e)

    def _get_service_units_to_allocate(self, allocation_period):
        """Return the number of service units to allocate to the project
        if the renewal were to be approved now for the given
        AllocationPeriod."""
        # TODO: Modify this as needed when supporting other types.
        num_service_units = Decimal(
            self.interface.service_units_from_name(
                self.computing_allowance.name, is_timed=True,
                allocation_period=allocation_period))
        return prorated_allocation_amount(
            num_service_units, utc_now_offset_aware(), allocation_period)


class AllocationRenewalRequestView(LoginRequiredMixin, UserPassesTestMixin,
                                   AllocationRenewalMixin, SessionWizardView):

    FORMS = [
        ('allocation_period', SavioProjectAllocationPeriodForm),
        ('pi_selection', ProjectRenewalPISelectionForm),
        ('pooling_preference', ProjectRenewalPoolingPreferenceForm),
        ('project_selection', ProjectRenewalProjectSelectionForm),
        ('new_project_details', SavioProjectDetailsForm),
        ('new_project_survey', SavioProjectSurveyForm),
        ('google_renewal_survey', ProjectRenewalGoogleSurveyForm),
        ('review_and_submit', ProjectRenewalReviewAndSubmitForm),
    ]

    TEMPLATES = {
        'allocation_period': 'project/project_renewal/allocation_period.html',
        'pi_selection': 'project/project_renewal/pi_selection.html',
        'pooling_preference':
            'project/project_renewal/pooling_preference.html',
        'project_selection': 'project/project_renewal/project_selection.html',
        'new_project_details':
            'project/project_renewal/new_project_details.html',
        'new_project_survey':
            'project/project_renewal/new_project_survey.html',
        'google_renewal_survey':
            'project/project_renewal/project_google_renewal_survey.html',
        'review_and_submit': 'project/project_renewal/review_and_submit.html',
    }

    form_list = [
        SavioProjectAllocationPeriodForm,
        ProjectRenewalPISelectionForm,
        ProjectRenewalPoolingPreferenceForm,
        ProjectRenewalProjectSelectionForm,
        SavioProjectDetailsForm,
        SavioProjectSurveyForm,
        ProjectRenewalGoogleSurveyForm,
        ProjectRenewalReviewAndSubmitForm,
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define a lookup table from form name to step number.
        self.step_numbers_by_form_name = {
            name: i for i, (name, _) in enumerate(self.FORMS)}

    def test_func(self):
        """Allow superusers and users who are active Managers or
        Principal Investigators on at least one Project to access the
        view."""
        user = self.request.user
        if self.request.user.is_superuser:
            return True
        signed_date = (
            self.request.user.userprofile.access_agreement_signed_date)
        if signed_date is None:
            message = (
                'You must sign the User Access Agreement before you can '
                'request to renew a PI\'s allocation.')
            messages.error(self.request, message)
            return False
        role_names = ['Manager', 'Principal Investigator']
        status = ProjectUserStatusChoice.objects.get(name='Active')
        has_access = ProjectUser.objects.filter(
            user=user, role__name__in=role_names, status=status)
        if has_access:
            return True
        message = (
            'You must be an active Manager or Principal Investigator of a '
            'Project.')
        messages.error(self.request, message)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        current_step = int(self.steps.current)
        self.__set_data_from_previous_steps(current_step, context)
        return context

    def get_form_kwargs(self, step=None):
        kwargs = {}
        step = int(step)
        if step == self.step_numbers_by_form_name['allocation_period']:
            kwargs['computing_allowance'] = self.computing_allowance
        elif step == self.step_numbers_by_form_name['pi_selection']:
            kwargs['computing_allowance'] = self.computing_allowance
            tmp = {}
            self.__set_data_from_previous_steps(step, tmp)
            kwargs['allocation_period_pk'] = getattr(
                tmp.get('allocation_period', None), 'pk', None)
            project_pks = []
            user = self.request.user
            project_name_prefix = self.interface.code_from_name(
                self.computing_allowance.name)
            role_names = ['Manager', 'Principal Investigator']
            status = ProjectUserStatusChoice.objects.get(name='Active')
            project_users = user.projectuser_set.filter(
                project__name__startswith=project_name_prefix,
                role__name__in=role_names,
                status=status)
            for project_user in project_users:
                project_pks.append(project_user.project.pk)
            kwargs['project_pks'] = project_pks
        elif step == self.step_numbers_by_form_name['pooling_preference']:
            tmp = {}
            self.__set_data_from_previous_steps(step, tmp)
            kwargs['currently_pooled'] = ('current_project' in tmp and
                                          tmp['current_project'].is_pooled())
        elif step == self.step_numbers_by_form_name['project_selection']:
            kwargs['computing_allowance'] = self.computing_allowance
            tmp = {}
            self.__set_data_from_previous_steps(step, tmp)
            kwargs['pi_pk'] = tmp['PI'].user.pk
            form_class = ProjectRenewalPoolingPreferenceForm
            choices = (
                form_class.UNPOOLED_TO_POOLED,
                form_class.POOLED_TO_POOLED_DIFFERENT,
            )
            kwargs['non_owned_projects'] = tmp['preference'] in choices
            if 'current_project' in tmp:
                kwargs['exclude_project_pk'] = tmp['current_project'].pk
        elif step == self.step_numbers_by_form_name['new_project_details']:
            kwargs['computing_allowance'] = self.computing_allowance
        elif step == self.step_numbers_by_form_name['new_project_survey']:
            kwargs['computing_allowance'] = self.computing_allowance
        elif step == self.step_numbers_by_form_name['google_renewal_survey']:
            kwargs['user'] = self.request.user
            tmp = {}
            self.__set_data_from_previous_steps(step, tmp)
            kwargs['project_name'] = tmp['current_project'].name
            kwargs['pi'] = tmp['PI'].user
            kwargs['allocation_period'] = tmp['allocation_period'].name

        return kwargs

    def get_template_names(self):
        return [self.TEMPLATES[self.FORMS[int(self.steps.current)][0]]]

    def done(self, form_list, **kwargs):
        """Perform processing and store information in a request
        object."""
        redirect_url = '/'
        try:
            form_data = session_wizard_all_form_data(
                form_list, kwargs['form_dict'], len(self.form_list))
            tmp = {}
            self.__set_data_from_previous_steps(len(self.FORMS), tmp)
            pi = tmp['PI'].user
            allocation_period = tmp['allocation_period']

            # If the PI already has a non-denied request for the period, raise
            # an exception. Such PIs are not selectable in the 'pi_selection'
            # step, but a request could have been created between selection and
            # final submission.
            if has_non_denied_renewal_request(pi, allocation_period):
                raise Exception(
                    f'PI {pi.username} already has a non-denied '
                    f'AllocationRenewalRequest for AllocationPeriod '
                    f'{allocation_period.name}.')

            # If a new Project was requested, create it along with a
            # SavioProjectAllocationRequest.
            new_project_request = None
            form_class = ProjectRenewalPoolingPreferenceForm
            if tmp['preference'] == form_class.POOLED_TO_UNPOOLED_NEW:
                requested_project = self.__handle_create_new_project(form_data)
                survey_data = self.__get_survey_data(form_data)
                new_project_request = self.__handle_create_new_project_request(
                    pi, requested_project, survey_data)
            else:
                requested_project = tmp['requested_project']

            request = self.create_allocation_renewal_request(
                self.request.user, pi, self.computing_allowance,
                allocation_period, tmp['current_project'], requested_project,
                new_project_request=new_project_request)

            self.send_emails(request)
        except Exception as e:
            logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            messages.success(self.request, self.success_message)

        return HttpResponseRedirect(redirect_url)

    @staticmethod
    def condition_dict():
        view = AllocationRenewalRequestView
        return {
            '3': view.show_project_selection_form_condition,
            '4': view.show_new_project_forms_condition,
            '5': view.show_new_project_forms_condition,
            '6': view.show_renewal_survey_form_condition,
        }

    def show_new_project_forms_condition(self):
        """Only show the forms needed for a new Project if the pooling
        preference is to create one."""
        step_name = 'pooling_preference'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        form_class = ProjectRenewalPoolingPreferenceForm
        return (cleaned_data.get('preference', None) ==
                form_class.POOLED_TO_UNPOOLED_NEW)

    def show_project_selection_form_condition(self):
        """Only show the form for selecting a Project if the pooling
        preference is to start pooling, to pool with a different
        Project, or to select a different Project owned by the PI."""
        step_name = 'pooling_preference'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        form_class = ProjectRenewalPoolingPreferenceForm
        preferences = (
            form_class.UNPOOLED_TO_POOLED,
            form_class.POOLED_TO_POOLED_DIFFERENT,
            form_class.POOLED_TO_UNPOOLED_OLD,
        )
        return cleaned_data.get('preference', None) in preferences

    def show_renewal_survey_form_condition(self):
        """Only show the renewal survey form for a particular period.

        TODO: This period has been hard-coded for the short-term. A
         longer-term solution without hard-coding must be applied prior
         to the start of the period following it.
        """
        step_name = 'allocation_period'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        allocation_period = cleaned_data.get('allocation_period', None)
        expected_allocation_period = AllocationPeriod.objects.get(
            name='Allowance Year 2024 - 2025')
        return allocation_period == expected_allocation_period

    def __get_survey_data(self, form_data):
        """Return provided survey data."""
        step_number = self.step_numbers_by_form_name['new_project_survey']
        return form_data[step_number]

    def __handle_create_new_project(self, form_data):
        """Create a new project and an allocation to the primary compute
        resource. This method should only be invoked if a new Project"""
        step_number = self.step_numbers_by_form_name['new_project_details']
        data = form_data[step_number]

        # Create the new Project.
        status = ProjectStatusChoice.objects.get(name='New')
        try:
            project = Project.objects.create(
                name=data['name'],
                status=status,
                title=data['title'],
                description=data['description'])
        except IntegrityError as e:
            logger.error(
                f'Project {data["name"]} unexpectedly already exists.')
            raise e

        # Create an allocation to the primary compute resource.
        status = AllocationStatusChoice.objects.get(name='New')
        allocation = Allocation.objects.create(project=project, status=status)
        resource = get_primary_compute_resource()
        allocation.resources.add(resource)
        allocation.save()

        return project

    def __handle_create_new_project_request(self, pi, project, survey_data):
        """Create a new SavioProjectAllocationRequest. This method
        should only be invoked if a new Project is requested."""
        # TODO: allocation_type will eventually be removed from the model.
        request_kwargs = dict()
        request_kwargs['requester'] = self.request.user
        request_kwargs['allocation_type'] = \
            self.interface.name_short_from_name(self.computing_allowance.name)
        request_kwargs['computing_allowance'] = self.computing_allowance
        request_kwargs['pi'] = pi
        request_kwargs['project'] = project
        request_kwargs['pool'] = False
        request_kwargs['survey_answers'] = survey_data
        request_kwargs['status'] = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
        return SavioProjectAllocationRequest.objects.create(**request_kwargs)

    def __infer_pi_current_project(self, pi_user, computing_allowance):
        """Retrieve the PI's current Project with the given
        allowance."""
        # TODO: Set this dynamically when supporting other types.
        allocation_period = get_current_allowance_year_period()
        try:
            # TODO: When supporting renewals of allowances that PIs may have
            # TODO: multiple of, relax the uniqueness constraint.
            return get_pi_active_unique_project(
                pi_user, computing_allowance, allocation_period)
        except Project.DoesNotExist:
            # If the PI has no active Project with the allowance, fall back on
            # one shared by the requester and the PI.
            project_name_prefix = self.interface.code_from_name(
                computing_allowance.get_name())
            requester_projects = set(list(
                ProjectUser.objects.filter(
                    project__name__startswith=project_name_prefix,
                    user=self.request.user,
                    role__name__in=[
                        'Manager', 'Principal Investigator']
                ).values_list('project', flat=True)))
            pi_projects = set(list(
                ProjectUser.objects.filter(
                    project__name__startswith=project_name_prefix,
                    user=pi_user,
                    role__name='Principal Investigator'
                ).values_list('project', flat=True)))
            intersection = set.intersection(
                requester_projects, pi_projects)
            project_pk = sorted(list(intersection))[0]
            return Project.objects.get(pk=project_pk)

    def __set_data_from_previous_steps(self, step, dictionary):
        """Update the given dictionary with data from previous steps."""
        dictionary['computing_allowance'] = self.computing_allowance
        computing_allowance_wrapper = ComputingAllowance(
            self.computing_allowance)
        dictionary['allowance_is_one_per_pi'] = \
            computing_allowance_wrapper.is_one_per_pi()

        allocation_period_form_step = self.step_numbers_by_form_name[
            'allocation_period']
        if step > allocation_period_form_step:
            data = self.get_cleaned_data_for_step(
                str(allocation_period_form_step))
            if data:
                dictionary.update(data)
                dictionary['allocation_amount'] = \
                    self._get_service_units_to_allocate(
                        data['allocation_period'])

        pi_selection_form_step = self.step_numbers_by_form_name['pi_selection']
        if step > pi_selection_form_step:
            data = self.get_cleaned_data_for_step(str(pi_selection_form_step))
            if data:
                dictionary.update(data)
                pi_user = data['PI'].user
                current_project = self.__infer_pi_current_project(
                    pi_user, computing_allowance_wrapper)
                dictionary['current_project'] = current_project

        pooling_preference_form_step = self.step_numbers_by_form_name[
            'pooling_preference']
        if step > pooling_preference_form_step:
            data = self.get_cleaned_data_for_step(
                str(pooling_preference_form_step))
            if data:
                dictionary.update(data)

                preference = data['preference']
                form_class = ProjectRenewalPoolingPreferenceForm
                dictionary['breadcrumb_pooling_preference'] = \
                    form_class.SHORT_DESCRIPTIONS.get(preference, 'Unknown')

                if (preference == form_class.UNPOOLED_TO_UNPOOLED or
                        preference == form_class.POOLED_TO_POOLED_SAME):
                    dictionary['requested_project'] = \
                        dictionary['current_project']

        project_selection_form_step = self.step_numbers_by_form_name[
            'project_selection']
        if step > project_selection_form_step:
            data = self.get_cleaned_data_for_step(
                str(project_selection_form_step))
            if data:
                dictionary.update(data)
                dictionary['requested_project'] = data['project']

        new_project_details_form_step = self.step_numbers_by_form_name[
            'new_project_details']
        if step > new_project_details_form_step:
            data = self.get_cleaned_data_for_step(
                str(new_project_details_form_step))
            if data:
                dictionary.update(data)
                dictionary['requested_project'] = data['name']

        google_renewal_survey_form_step = self.step_numbers_by_form_name[
            'google_renewal_survey']
        if step == google_renewal_survey_form_step:
            survey_data = get_renewal_survey(dictionary['allocation_period'].name)
            if survey_data != None:
                dictionary['form_id'] = survey_data['form_id']


class AllocationRenewalRequestUnderProjectView(LoginRequiredMixin,
                                               UserPassesTestMixin,
                                               AllocationRenewalMixin,
                                               SessionWizardView):

    FORMS = [
        ('allocation_period', SavioProjectAllocationPeriodForm),
        ('pi_selection', ProjectRenewalPISelectionForm),
        # ('renewal_survey', ProjectRenewalSurveyForm),
        ('google_renewal_survey', ProjectRenewalGoogleSurveyForm),
        ('review_and_submit', ProjectRenewalReviewAndSubmitForm),
    ]

    TEMPLATES = {
        'allocation_period': 'project/project_renewal/allocation_period.html',
        'pi_selection': 'project/project_renewal/pi_selection.html',
        'google_renewal_survey': 
            'project/project_renewal/project_google_renewal_survey.html',
        'review_and_submit': 'project/project_renewal/review_and_submit.html',
    }

    form_list = [
        SavioProjectAllocationPeriodForm,
        ProjectRenewalPISelectionForm,
        ProjectRenewalGoogleSurveyForm,
        ProjectRenewalReviewAndSubmitForm,
    ]

    project_obj = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define a lookup table from form name to step number.
        self.step_numbers_by_form_name = {
            name: i for i, (name, _) in enumerate(self.FORMS)}

    @staticmethod
    def condition_dict():
        view = AllocationRenewalRequestUnderProjectView
        return {
            '2': view.show_renewal_survey_form_condition,
        }

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.project_obj = get_object_or_404(Project, pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def done(self, form_list, **kwargs):
        """Perform processing and store information in a request
        object."""
        redirect_url = reverse(
            'project-detail', kwargs={'pk': self.project_obj.pk})
        try:
            tmp = {}
            self.__set_data_from_previous_steps(len(self.FORMS), tmp)
            pi = tmp['PI'].user
            allocation_period = tmp['allocation_period']

            # If the PI already has a non-denied request for the period, raise
            # an exception. Such PIs are not selectable in the 'pi_selection'
            # step, but a request could have been created between selection and
            # final submission.
            if has_non_denied_renewal_request(pi, allocation_period):
                raise Exception(
                    f'PI {pi.username} already has a non-denied '
                    f'AllocationRenewalRequest for AllocationPeriod '
                    f'{allocation_period.name}.')

            # request = self.create_allocation_renewal_request(
            #     self.request.user, pi, self.computing_allowance,
            #     allocation_period, self.project_obj, self.project_obj, 
            #     tmp['renewal_survey_answers'])
            request = self.create_allocation_renewal_request(
                self.request.user, pi, self.computing_allowance,
                allocation_period, self.project_obj, self.project_obj)

            self.send_emails(request)
        except Exception as e:
            logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            messages.success(self.request, self.success_message)

        return HttpResponseRedirect(redirect_url)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        current_step = int(self.steps.current)
        self.__set_data_from_previous_steps(current_step, context)
        return context

    def get_form_kwargs(self, step=None):
        kwargs = {}
        step = int(step)
        if step == self.step_numbers_by_form_name['allocation_period']:
            kwargs['computing_allowance'] = self.computing_allowance
        elif step == self.step_numbers_by_form_name['pi_selection']:
            kwargs['computing_allowance'] = self.computing_allowance
            tmp = {}
            self.__set_data_from_previous_steps(step, tmp)
            kwargs['allocation_period_pk'] = getattr(
                tmp.get('allocation_period', None), 'pk', None)
            kwargs['project_pks'] = [self.project_obj.pk]
        elif step == self.step_numbers_by_form_name['google_renewal_survey']:
            kwargs['user'] = self.request.user
            kwargs['project_name'] = self.project_obj.name
            tmp = {}
            self.__set_data_from_previous_steps(len(self.FORMS), tmp)
            kwargs['pi'] = tmp['PI'].user
            kwargs['allocation_period'] = tmp['allocation_period'].name
        return kwargs

    def get_template_names(self):
        return [self.TEMPLATES[self.FORMS[int(self.steps.current)][0]]]

    def show_renewal_survey_form_condition(self):
        """Only show the renewal survey form for a particular period.

        TODO: This period has been hard-coded for the short-term. A
         longer-term solution without hard-coding must be applied prior
         to the start of the period following it.
        """
        step_name = 'allocation_period'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        allocation_period = cleaned_data.get('allocation_period', None)
        expected_allocation_period = AllocationPeriod.objects.get(
            name='Allowance Year 2024 - 2025')
        return allocation_period == expected_allocation_period

    def test_func(self):
        """Allow superusers and users who are active Managers or
        Principal Investigators on the Project and who have signed the
        access agreement to access the view."""
        user = self.request.user
        if user.is_superuser:
            return True
        signed_date = (
            self.request.user.userprofile.access_agreement_signed_date)
        if signed_date is None:
            message = (
                'You must sign the User Access Agreement before you can '
                'request to renew a PI\'s allocation.')
            messages.error(self.request, message)
            return False
        if is_user_manager_or_pi_of_project(user, self.project_obj):
            return True
        message = (
            'You must be an active Manager or Principal Investigator of the '
            'Project.')
        messages.error(self.request, message)

    def __set_data_from_previous_steps(self, step, dictionary):
        """Update the given dictionary with data from previous steps."""
        allocation_period_form_step = self.step_numbers_by_form_name[
            'allocation_period']
        if step > allocation_period_form_step:
            data = self.get_cleaned_data_for_step(
                str(allocation_period_form_step))
            if data:
                dictionary.update(data)
                dictionary['allocation_amount'] = \
                    self._get_service_units_to_allocate(
                        data['allocation_period'])

        pi_selection_form_step = self.step_numbers_by_form_name['pi_selection']
        if step > pi_selection_form_step:
            data = self.get_cleaned_data_for_step(str(pi_selection_form_step))
            if data:
                dictionary.update(data)
                dictionary['current_project'] = self.project_obj
                dictionary['requested_project'] = self.project_obj
                form_class = ProjectRenewalPoolingPreferenceForm
                if not self.project_obj.is_pooled():
                    pooling_preference = form_class.UNPOOLED_TO_UNPOOLED
                else:
                    pooling_preference = form_class.POOLED_TO_POOLED_SAME
                form_class = ProjectRenewalPoolingPreferenceForm
                dictionary['breadcrumb_pooling_preference'] = \
                    form_class.SHORT_DESCRIPTIONS.get(
                        pooling_preference, 'Unknown')
        
        google_renewal_survey_form_step = self.step_numbers_by_form_name[
            'google_renewal_survey']
        if step == google_renewal_survey_form_step:
            survey_data = get_renewal_survey(dictionary['allocation_period'].name)
            if survey_data != None:
                dictionary['form_id'] = survey_data['form_id']
                
