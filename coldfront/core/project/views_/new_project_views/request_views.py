from allauth.account.models import EmailAddress

from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.billing.forms import BillingIDValidationForm
from coldfront.core.billing.utils.queries import get_or_create_billing_activity_from_full_id

from coldfront.core.project.forms_.new_project_forms.request_forms import ComputingAllowanceForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectAllocationPeriodForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectDetailsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectExistingPIForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectICAExtraFieldsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectNewPIForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectPoolAllocationsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectPooledProjectSelectionForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectRechargeExtraFieldsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectSurveyForm
from coldfront.core.project.forms_.new_project_forms.request_forms import VectorProjectDetailsForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.models import savio_project_request_ica_extra_fields_schema
from coldfront.core.project.models import savio_project_request_ica_state_schema
from coldfront.core.project.models import savio_project_request_recharge_extra_fields_schema
from coldfront.core.project.models import savio_project_request_recharge_state_schema
from coldfront.core.project.models import VectorProjectAllocationRequest
from coldfront.core.project.utils_.new_project_utils import send_new_project_request_admin_notification_email
from coldfront.core.project.utils_.new_project_utils import send_new_project_request_pi_notification_email
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils import get_primary_compute_resource
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.user.models import UserProfile
from coldfront.core.user.utils import access_agreement_signed
from coldfront.core.utils.common import session_wizard_all_form_data
from coldfront.core.utils.common import utc_now_offset_aware

from collections import OrderedDict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from django_q.tasks import async_task
from flags.state import flag_enabled
from formtools.wizard.views import SessionWizardView

import logging
import os


class ProjectRequestView(LoginRequiredMixin, UserPassesTestMixin,
                         TemplateView):
    template_name = 'project/project_request/project_request.html'

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        if access_agreement_signed(self.request.user):
            return True
        message = (
            'You must sign the User Access Agreement before you can create a '
            'new project.')
        messages.error(self.request, message)

    def get(self, request, *args, **kwargs):
        context = dict()
        return render(request, self.template_name, context)


# =============================================================================
# BRC: SAVIO
# =============================================================================

class NewProjectRequestLandingView(LoginRequiredMixin, UserPassesTestMixin,
                                   TemplateView):
    template_name = (
        'project/project_request/savio/request/project_request_landing.html')

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        if access_agreement_signed(self.request.user):
            return True
        message = (
            'You must sign the User Access Agreement before you can create a '
            'new project.')
        messages.error(self.request, message)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        allowances = []
        yearly_allowance_names = []
        interface = ComputingAllowanceInterface()
        for allowance in sorted(interface.allowances(), key=lambda a: a.pk):
            wrapper = ComputingAllowance(allowance)
            allowance_name = wrapper.get_name()
            entry = {
                'name_long': interface.name_long_from_name(allowance_name),
                'is_poolable': wrapper.is_poolable(),
                'requires_mou': wrapper.requires_memorandum_of_understanding(),
            }
            allowances.append(entry)
            if wrapper.is_yearly():
                name_short = interface.name_short_from_name(allowance_name)
                yearly_allowance_names.append(f'{name_short}s')

        context['allowances'] = allowances
        context['yearly_allowance_names'] = ', '.join(yearly_allowance_names)

        return context


class SavioProjectRequestWizard(LoginRequiredMixin, UserPassesTestMixin,
                                SessionWizardView):

    # Note that this list may not contain all forms included in the view. Avoid
    # referencing this list directly.
    form_list = [
        ComputingAllowanceForm,
        SavioProjectAllocationPeriodForm,
        SavioProjectExistingPIForm,
        SavioProjectNewPIForm,
        SavioProjectICAExtraFieldsForm,
        SavioProjectRechargeExtraFieldsForm,
        SavioProjectPoolAllocationsForm,
        SavioProjectPooledProjectSelectionForm,
        SavioProjectDetailsForm,
        BillingIDValidationForm,
        SavioProjectSurveyForm,
    ]

    logger = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        # When instantiated with .as_view(), the class variable form_list is
        # processed. However, the check for whether department functionality is
        # enabled cannot be done at the class level, so the check, and the
        # update to the list of forms to include the department selection form,
        # is done here.
        if self.__departments_enabled():
            kwargs['form_list'] = self.__include_department_form(
                kwargs['form_list'])

        super().__init__(*args, **kwargs)

        # A list of tuples (form name, form class) in order of appearance.
        self.__forms = self.__wizard_form_names_and_classes()
        # A dict mapping form name to the corresponding template.
        self.__templates = self.__wizard_templates()

        # Define a lookup table from form name to step number.
        self.step_numbers_by_form_name = {
            name: i for i, (name, _) in enumerate(self.__forms)}

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        signed_date = (
            self.request.user.userprofile.access_agreement_signed_date)
        if signed_date is not None:
            return True
        message = (
            'You must sign the User Access Agreement before you can create a '
            'new project.')
        messages.error(self.request, message)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        current_step = int(self.steps.current)
        self.__set_data_from_previous_steps(current_step, context)
        return context

    def get_form_kwargs(self, step=None):
        # For each step, a list of kwargs required by the corresponding form.
        required_keys_by_step_name = {
            'allocation_period': ['computing_allowance'],
            'existing_pi': ['computing_allowance', 'allocation_period'],
            'pooled_project_selection': ['computing_allowance'],
            'details': ['computing_allowance'],
            'survey': ['computing_allowance'],
        }
        # For each step number, the corresponding step name.
        step_names_by_step_number = {
            self.step_numbers_by_form_name[name]: name
            for name in required_keys_by_step_name
        }

        step_number = int(step)
        if step_number not in step_names_by_step_number:
            return {}

        data = {}
        self.__set_data_from_previous_steps(step_number, data)

        kwargs = {}
        step_name = step_names_by_step_number[step_number]
        for key in required_keys_by_step_name[step_name]:
            kwargs[key] = data.get(key, None)
        return kwargs

    def get_template_names(self):
        return [self.__templates[self.__forms[int(self.steps.current)][0]]]

    def done(self, form_list, **kwargs):
        """Perform processing and store information in a request
        object."""
        redirect_url = '/'
        try:
            form_data = session_wizard_all_form_data(
                form_list, kwargs['form_dict'], len(self.__forms))
            request_kwargs = {
                'requester': self.request.user,
            }
            computing_allowance = self.__get_computing_allowance(form_data)
            computing_allowance_wrapper = ComputingAllowance(
                computing_allowance)

            with transaction.atomic():
                allocation_period = self.__get_allocation_period(form_data)
                pi = self.__handle_pi_data(form_data)

                if self.__departments_enabled():
                    self.__handle_pi_departments(form_data, pi)

                if computing_allowance_wrapper.is_instructional():
                    self.__handle_ica_allowance(
                        form_data, computing_allowance_wrapper, request_kwargs)
                elif computing_allowance_wrapper.is_recharge():
                    self.__handle_recharge_allowance(
                        form_data, computing_allowance_wrapper, request_kwargs)

                pooling_requested = self.__get_pooling_requested(form_data)
                if pooling_requested:
                    project = self.__handle_pool_with_existing_project(
                        form_data)
                else:
                    project = self.__handle_create_new_project(form_data)
                    if self.__billing_id_required():
                        self.__handle_billing_id(form_data, request_kwargs)

                survey_data = self.__get_survey_data(form_data)

                # Store transformed form data in a request.
                # TODO: allocation_type will eventually be removed from the
                # TODO: model.
                computing_allowance_interface = ComputingAllowanceInterface()
                request_kwargs['allocation_type'] = \
                    computing_allowance_interface.name_short_from_name(
                        computing_allowance_wrapper.get_name())
                request_kwargs['computing_allowance'] = computing_allowance
                request_kwargs['allocation_period'] = allocation_period
                request_kwargs['pi'] = pi
                request_kwargs['project'] = project
                request_kwargs['pool'] = pooling_requested
                request_kwargs['survey_answers'] = survey_data
                request_kwargs['status'] = \
                    ProjectAllocationRequestStatusChoice.objects.get(
                        name='Under Review')
                request_kwargs['request_time'] = utc_now_offset_aware()
                request = SavioProjectAllocationRequest.objects.create(
                    **request_kwargs)

            try:
                if self.__departments_enabled():
                    # Enqueue a task to update the PI's authoritative
                    # departments. This is purposefully placed outside the
                    # transaction to prevent it from closing during processing
                    # (when processing is synchronous).
                    func = (
                        'coldfront.plugins.departments.tasks.'
                        'fetch_and_set_user_authoritative_departments')
                    async_task(
                        func, pi.pk, sync=settings.Q_CLUSTER.get('sync', False))
            except Exception as e:
                self.logger.exception(e)

            # Send a notification email to admins.
            try:
                send_new_project_request_admin_notification_email(request)
            except Exception as e:
                self.logger.error(
                    'Failed to send notification email. Details:\n')
                self.logger.exception(e)
            # Send a notification email to the PI if the requester differs.
            if request.requester != request.pi:
                try:
                    send_new_project_request_pi_notification_email(request)
                except Exception as e:
                    self.logger.error(
                        'Failed to send notification email. Details:\n')
                    self.logger.exception(e)
        except Exception as e:
            self.logger.exception(e)
            message = 'Unexpected failure. Please contact an administrator.'
            messages.error(self.request, message)
        else:
            message = (
                'Thank you for your submission. It will be reviewed and '
                'processed by administrators.')
            messages.success(self.request, message)

        return HttpResponseRedirect(redirect_url)

    @staticmethod
    def condition_dict():
        """Return a mapping from a string index `i` into FORMS
        (zero-indexed) to a function determining whether FORMS[int(i)]
        should be included."""
        view = SavioProjectRequestWizard

        _condition_dict = {}
        # The computing allowance form (at index 0) is always included.
        _condition_dict['1'] = view.show_allocation_period_form_condition
        # The existing PI selection form (at index 2) is always included.
        _condition_dict['3'] = view.show_new_pi_form_condition

        # The index of the next form to be added.
        next_index = 4

        if view.__departments_enabled():
            _condition_dict[str(next_index)] = \
                view.show_pi_department_form_condition
            next_index += 1

        remaining_form_conditions = (
            view.show_ica_extra_fields_form_condition,
            view.show_recharge_extra_fields_form_condition,
            view.show_pool_allocations_form_condition,
            view.show_pooled_project_selection_form_condition,
            view.show_details_form_condition,
            view.show_billing_id_form_condition,
        )

        for condition in remaining_form_conditions:
            _condition_dict[str(next_index)] = condition
            next_index += 1

        return _condition_dict

    def show_allocation_period_form_condition(self):
        """Only show the form for selecting an AllocationPeriod for
        periodic allowances."""
        step_name = 'computing_allowance'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        computing_allowance = cleaned_data.get('computing_allowance', None)
        if not computing_allowance:
            return False
        return ComputingAllowance(computing_allowance).is_periodic()

    def show_billing_id_form_condition(self):
        """Only show the form for providing a billing ID when it is
        required, and when pooling is not requested."""
        if not self.__billing_id_required():
            return False
        step_name = 'pool_allocations'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        return not cleaned_data.get('pool', False)

    def show_details_form_condition(self):
        step_name = 'pool_allocations'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        return not cleaned_data.get('pool', False)

    def show_ica_extra_fields_form_condition(self):
        step_name = 'computing_allowance'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        computing_allowance = cleaned_data.get('computing_allowance', None)
        if not computing_allowance:
            return False
        computing_allowance = ComputingAllowance(computing_allowance)
        return (
            computing_allowance.is_instructional() and
            computing_allowance.requires_extra_information())

    def show_new_pi_form_condition(self):
        """Only show the form for providing details about a new PI if
        the user did not select an existing PI."""
        step_name = 'existing_pi'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        return cleaned_data.get('PI', None) is None

    def show_pi_department_form_condition(self):
        """Only show the form for providing department(s) for the PI
        when the following are true:
            - Department information is required.
            - The PI does not already have any departments set.
        """
        if not self.__departments_enabled():
            return False

        from coldfront.plugins.departments.utils.queries import get_departments_for_user

        existing_pi_step = str(self.step_numbers_by_form_name['existing_pi'])
        existing_pi_cleaned_data = self.get_cleaned_data_for_step(
            existing_pi_step) or {}
        if existing_pi_cleaned_data:
            pi = existing_pi_cleaned_data['PI']
            authoritative_departments, non_authoritative_departments = \
                get_departments_for_user(pi)
            if authoritative_departments or non_authoritative_departments:
                return False

        return True

    def show_pool_allocations_form_condition(self):
        step_name = 'computing_allowance'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        computing_allowance = cleaned_data.get('computing_allowance', None)
        if not computing_allowance:
            return False
        return ComputingAllowance(computing_allowance).is_poolable()

    def show_pooled_project_selection_form_condition(self):
        step_name = 'pool_allocations'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        return cleaned_data.get('pool', False)

    def show_recharge_extra_fields_form_condition(self):
        step_name = 'computing_allowance'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        computing_allowance = cleaned_data.get('computing_allowance', None)
        if not computing_allowance:
            return False
        computing_allowance = ComputingAllowance(computing_allowance)
        return (
            computing_allowance.is_recharge() and
            computing_allowance.requires_extra_information())

    @staticmethod
    def __billing_id_required():
        """Return whether a billing ID should be requested from the
        user. The form for requesting it will be included based on
        additional factors."""
        return flag_enabled('LRC_ONLY')

    @staticmethod
    def __departments_enabled():
        """Return whether department functionality is enabled."""
        # Because this is called from urls.py (via condition_dict) at import
        # time, the database table for flag state may not exist yet. Catch the
        # exception raised to allow the import to succeed.
        try:
            return flag_enabled('USER_DEPARTMENTS_ENABLED')
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(e)
            return False

    def __get_allocation_period(self, form_data):
        """Return the AllocationPeriod the user selected."""
        step_number = self.step_numbers_by_form_name['allocation_period']
        data = form_data[step_number]
        return data.get('allocation_period', None)

    def __get_computing_allowance(self, form_data):
        """Return the computing allowance (Resource) the user
        selected."""
        step_number = self.step_numbers_by_form_name['computing_allowance']
        data = form_data[step_number]
        return data['computing_allowance']

    def __get_pooling_requested(self, form_data):
        """Return whether pooling was requested."""
        step_number = self.step_numbers_by_form_name['pool_allocations']
        data = form_data[step_number]
        return data.get('pool', False)

    def __get_survey_data(self, form_data):
        """Return provided survey data."""
        step_number = self.step_numbers_by_form_name['survey']
        return form_data[step_number]

    def __handle_billing_id(self, form_data, request_kwargs):
        """Store the User-provided billing ID in the given dictionary to
        be used during request creation."""
        step_number = self.step_numbers_by_form_name['billing_id']
        data = form_data[step_number]
        billing_id = data['billing_id']
        request_kwargs['billing_activity'] = \
            get_or_create_billing_activity_from_full_id(billing_id)

    def __handle_ica_allowance(self, form_data, computing_allowance_wrapper,
                               request_kwargs):
        """Perform ICA-specific handling.

        In particular, set fields in the given dictionary to be used
        during request creation. Set the extra_fields field from the
        given form data and set the state field to include an additional
        step."""
        if computing_allowance_wrapper.requires_extra_information():
            step_number = self.step_numbers_by_form_name['ica_extra_fields']
            data = form_data[step_number]
            extra_fields = savio_project_request_ica_extra_fields_schema()
            for field in extra_fields:
                extra_fields[field] = data[field]
            request_kwargs['extra_fields'] = extra_fields
        request_kwargs['state'] = savio_project_request_ica_state_schema()

    def __handle_pi_data(self, form_data):
        """Return the requested PI. If the PI did not exist, create a
        new User and UserProfile."""
        # If an existing PI was selected, return the existing User object.
        step_number = self.step_numbers_by_form_name['existing_pi']
        data = form_data[step_number]
        if data['PI']:
            pi = data['PI']
            pi_profile = pi.userprofile
        else:
            # Create a new User object intended to be a new PI.
            step_number = self.step_numbers_by_form_name['new_pi']
            data = form_data[step_number]

            try:
                email = data['email']
                pi = User.objects.create(
                    username=email,
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    email=email,
                    is_active=True)
            except IntegrityError as e:
                self.logger.error(f'User {email} unexpectedly exists.')
                raise e

            # Set user's middle name in the UserProfile; generate a PI request.
            try:
                pi_profile = pi.userprofile
            except UserProfile.DoesNotExist as e:
                self.logger.error(
                    f'User {email} unexpectedly has no UserProfile.')
                raise e
            pi_profile.middle_name = data['middle_name']
            pi_profile.upgrade_request = utc_now_offset_aware()
            pi_profile.save()

            # Create an unverified, primary EmailAddress for the new User object.
            try:
                EmailAddress.objects.create(
                    user=pi,
                    email=email,
                    verified=False,
                    primary=True)
            except IntegrityError as e:
                self.logger.error(
                    f'EmailAddress {email} unexpectedly already exists.')
                raise e

        return pi

    def __handle_pi_departments(self, form_data, pi):
        """Update the PI's non-authoritative departments to the
        specified ones, if the requester was prompted to provide them.
        Do not update the PI's authoritative departments."""
        step_number = self.step_numbers_by_form_name['pi_department']
        data = form_data[step_number]
        non_authoritative_departments = data.get('departments', None)

        if non_authoritative_departments is None:
            # The requester was not prompted to provide departments.
            return

        from coldfront.plugins.departments.utils.queries import UserDepartmentUpdater

        user_department_updater = UserDepartmentUpdater(
            pi, non_authoritative_departments)
        user_department_updater.run(authoritative=False, non_authoritative=True)

    def __handle_recharge_allowance(self, form_data,
                                    computing_allowance_wrapper,
                                    request_kwargs):
        """Perform Recharge-specific handling.

        In particular, set fields in the given dictionary to be used
        during request creation. If required, set the extra_fields field
        from the given form data. In general, set the state field to
        include an additional step."""
        if computing_allowance_wrapper.requires_extra_information():
            step_number = self.step_numbers_by_form_name[
                'recharge_extra_fields']
            data = form_data[step_number]
            extra_fields = savio_project_request_recharge_extra_fields_schema()
            for field in extra_fields:
                extra_fields[field] = data[field]
            request_kwargs['extra_fields'] = extra_fields
        request_kwargs['state'] = savio_project_request_recharge_state_schema()

    def __handle_create_new_project(self, form_data):
        """Create a new project and an allocation to the primary Compute
        resource."""
        step_number = self.step_numbers_by_form_name['details']
        data = form_data[step_number]

        # Create the new Project.
        status = ProjectStatusChoice.objects.get(name='New')
        try:
            project = Project.objects.create(
                name=data['name'],
                status=status,
                title=data['title'],
                description=data['description'])
                #field_of_science=data['field_of_science'])
        except IntegrityError as e:
            self.logger.error(
                f'Project {data["name"]} unexpectedly already exists.')
            raise e

        # Create an allocation to the primary compute resource.
        status = AllocationStatusChoice.objects.get(name='New')
        allocation = Allocation.objects.create(project=project, status=status)
        resource = get_primary_compute_resource()
        allocation.resources.add(resource)
        allocation.save()

        return project

    def __handle_pool_with_existing_project(self, form_data):
        """Return the requested project to pool with."""
        step_number = \
            self.step_numbers_by_form_name['pooled_project_selection']
        data = form_data[step_number]
        project = data['project']

        # Validate that the project has exactly one allocation to the "Savio
        # Compute" resource.
        resource = get_primary_compute_resource()
        allocations = Allocation.objects.filter(
            project=project, resources__pk__exact=resource.pk)
        try:
            assert allocations.count() == 1
        except AssertionError as e:
            number = 'no' if allocations.count() == 0 else 'more than one'
            self.logger.error(
                f'Project {project.name} unexpectedly has {number} Allocation '
                f'to Resource {resource.name}')
            raise e

        return project

    def __include_department_form(self, form_list):
        """Given an OrderedDict defined in WizardView's get_initkwargs
        method that maps a step name (str) to a form class, return a new
        OrderedDict with the department selection form included.

        This should be done at instantiation, as opposed to at the class
        level, because the departments plugin app may not be installed,
        so imports of it may fail.

        This method should only be called if the app is installed.
        """
        from coldfront.plugins.departments.forms import \
            NonAuthoritativeDepartmentSelectionForm

        updated_form_list = OrderedDict()
        index = 0
        for _, form_class in form_list.items():
            updated_form_list[str(index)] = form_class
            index += 1
            if form_class == SavioProjectNewPIForm:
                updated_form_list[str(index)] = \
                    NonAuthoritativeDepartmentSelectionForm
                index += 1
        return updated_form_list

    def __set_data_from_previous_steps(self, step, dictionary):
        """Update the given dictionary with data from previous steps."""
        computing_allowance_form_step = \
            self.step_numbers_by_form_name['computing_allowance']
        if step > computing_allowance_form_step:
            computing_allowance_form_data = self.get_cleaned_data_for_step(
                str(computing_allowance_form_step))
            if computing_allowance_form_data:
                dictionary.update(computing_allowance_form_data)
                computing_allowance_wrapper = ComputingAllowance(
                    computing_allowance_form_data['computing_allowance'])
                dictionary['allowance_is_one_per_pi'] = \
                    computing_allowance_wrapper.is_one_per_pi()

        allocation_period_form_step = \
            self.step_numbers_by_form_name['allocation_period']
        if step > allocation_period_form_step:
            allocation_period_form_data = self.get_cleaned_data_for_step(
                str(allocation_period_form_step))
            if allocation_period_form_data:
                dictionary.update(allocation_period_form_data)

        existing_pi_step = self.step_numbers_by_form_name['existing_pi']
        new_pi_step = self.step_numbers_by_form_name['new_pi']
        if step > new_pi_step:
            existing_pi_form_data = self.get_cleaned_data_for_step(
                str(existing_pi_step))
            if existing_pi_form_data['PI'] is not None:
                pi = existing_pi_form_data['PI']
                dictionary.update({
                    'breadcrumb_pi': (
                        f'Existing PI: {pi.first_name} {pi.last_name} '
                        f'({pi.email})'),
                })
            else:
                new_pi_form_data = self.get_cleaned_data_for_step(
                    str(new_pi_step))
                first_name = new_pi_form_data['first_name']
                last_name = new_pi_form_data['last_name']
                email = new_pi_form_data['email']
                dictionary.update({
                    'breadcrumb_pi': (
                        f'New PI: {first_name} {last_name} ({email})')
                })

        pool_allocations_step = \
            self.step_numbers_by_form_name['pool_allocations']
        if step > pool_allocations_step:
            computing_allowance = ComputingAllowance(
                dictionary['computing_allowance'])
            if computing_allowance.is_poolable():
                pool_allocations_form_data = self.get_cleaned_data_for_step(
                    str(pool_allocations_step))
                pooling_requested = pool_allocations_form_data['pool']
            else:
                pooling_requested = False
            dictionary.update({'breadcrumb_pooling': pooling_requested})

        pooled_project_selection_step = \
            self.step_numbers_by_form_name['pooled_project_selection']
        details_step = self.step_numbers_by_form_name['details']
        if step > details_step:
            if pooling_requested:
                pooled_project_selection_form_data = \
                    self.get_cleaned_data_for_step(
                        str(pooled_project_selection_step))
                project = pooled_project_selection_form_data['project']
                dictionary.update({
                    'breadcrumb_project': f'Project: {project.name}'
                })
            else:
                details_form_data = self.get_cleaned_data_for_step(
                    str(details_step))
                name = details_form_data['name']
                dictionary.update({'breadcrumb_project': f'Project: {name}'})

    def __wizard_form_names_and_classes(self):
        """Return a list of tuples (form name, form class) in order of
        appearance."""
        names_and_classes = []

        names_and_classes.append(
            ('computing_allowance', ComputingAllowanceForm))
        names_and_classes.append(
            ('allocation_period', SavioProjectAllocationPeriodForm))
        names_and_classes.append(
            ('existing_pi', SavioProjectExistingPIForm))
        names_and_classes.append(
            ('new_pi', SavioProjectNewPIForm))

        if self.__departments_enabled():
            from coldfront.plugins.departments.forms import \
                NonAuthoritativeDepartmentSelectionForm
            names_and_classes.append(
                ('pi_department', NonAuthoritativeDepartmentSelectionForm))

        names_and_classes.append(
            ('ica_extra_fields', SavioProjectICAExtraFieldsForm))
        names_and_classes.append(
            ('recharge_extra_fields', SavioProjectRechargeExtraFieldsForm))
        names_and_classes.append(
            ('pool_allocations', SavioProjectPoolAllocationsForm))
        names_and_classes.append(
            ('pooled_project_selection',
             SavioProjectPooledProjectSelectionForm))
        names_and_classes.append(('details', SavioProjectDetailsForm))
        names_and_classes.append(('billing_id', BillingIDValidationForm))
        names_and_classes.append(('survey', SavioProjectSurveyForm))

        return names_and_classes

    def __wizard_templates(self):
        """Return a dict mapping form name to the corresponding
        template."""
        templates = {}

        templates['computing_allowance'] = (
            'project/project_request/savio/request/project_computing_allowance.html')
        templates['allocation_period'] = (
            'project/project_request/savio/request/project_allocation_period.html')
        templates['existing_pi'] = (
            'project/project_request/savio/request/project_existing_pi.html')
        templates['new_pi'] = (
            'project/project_request/savio/request/project_new_pi.html')

        if self.__departments_enabled():
            templates['pi_department'] = (
                'project/project_request/savio/request/project_pi_department.html')

        templates['ica_extra_fields'] = (
            'project/project_request/savio/request/project_ica_extra_fields.html')
        templates['recharge_extra_fields'] = (
            'project/project_request/savio/request/project_recharge_extra_fields.html')
        templates['pool_allocations'] = (
            'project/project_request/savio/request/project_pool_allocations.html')
        templates['pooled_project_selection'] = (
            'project/project_request/savio/request/'
            'project_pooled_project_selection.html')
        templates['details'] = (
            'project/project_request/savio/request/project_details.html')
        templates['billing_id'] = (
            'project/project_request/savio/request/project_billing_id.html')
        templates['survey'] = (
            'project/project_request/savio/request/project_survey.html')

        return templates


# =============================================================================
# BRC: VECTOR
# =============================================================================

class VectorProjectRequestView(LoginRequiredMixin, UserPassesTestMixin,
                               FormView):
    form_class = VectorProjectDetailsForm
    template_name = (
        'project/project_request/vector/request/project_details.html')

    logger = logging.getLogger(__name__)

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perms('project.view_vectorprojectallocationrequest'):
            return True

        signed_date = (
            self.request.user.userprofile.access_agreement_signed_date)
        if signed_date is not None:
            return True
        message = (
            'You must sign the User Access Agreement before you can create a '
            'new project.')
        messages.error(self.request, message)

    def form_valid(self, form):
        try:
            project = self.__handle_create_new_project(form.cleaned_data)
            # Store form data in a request.

            pi = User.objects.get(username=settings.VECTOR_PI_USERNAME)
            status = ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
            request = VectorProjectAllocationRequest.objects.create(
                requester=self.request.user,
                pi=pi,
                project=project,
                status=status)

            # Send a notification email to admins.
            try:
                send_new_project_request_admin_notification_email(request)
            except Exception as e:
                self.logger.error(
                    'Failed to send notification email. Details:\n')
                self.logger.exception(e)
        except Exception as e:
            self.logger.exception(e)
            message = 'Unexpected failure. Please contact an administrator.'
            messages.error(self.request, message)
        else:
            message = (
                'Thank you for your submission. It will be reviewed and '
                'processed by administrators.')
            messages.success(self.request, message)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('home')

    def __handle_create_new_project(self, data):
        """Create a new project and an allocation to the Vector Compute
        resource."""
        status = ProjectStatusChoice.objects.get(name='New')
        try:
            project = Project.objects.create(
                name=data['name'],
                status=status,
                title=data['title'],
                description=data['description'])
        except IntegrityError as e:
            self.logger.error(
                f'Project {data["name"]} unexpectedly already exists.')
            raise e

        # Create an allocation to the "Vector Compute" resource.
        status = AllocationStatusChoice.objects.get(name='New')
        allocation = Allocation.objects.create(project=project, status=status)
        resource = Resource.objects.get(name='Vector Compute')
        allocation.resources.add(resource)
        allocation.save()

        return project
