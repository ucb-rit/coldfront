import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView

from formtools.wizard.views import SessionWizardView

from coldfront.core.allocation.forms_.secure_dir_forms import SecureDirDataDescriptionForm
from coldfront.core.allocation.forms_.secure_dir_forms import SecureDirDirectoryNamesForm
from coldfront.core.allocation.forms_.secure_dir_forms import SecureDirPISelectionForm
from coldfront.core.allocation.forms_.secure_dir_forms import SecureDirRDMConsultationForm
from coldfront.core.allocation.utils_.secure_dir_utils.new_directory import get_default_secure_dir_paths
from coldfront.core.allocation.utils_.secure_dir_utils.new_directory import is_project_eligible_for_secure_dirs
from coldfront.core.allocation.utils_.secure_dir_utils.new_directory import SECURE_DIRECTORY_NAME_PREFIX
from coldfront.core.allocation.utils_.secure_dir_utils.new_directory import SecureDirRequestRunner

from coldfront.core.project.models import Project
from coldfront.core.project.utils_.permissions_utils import is_user_manager_or_pi_of_project

from coldfront.core.user.utils import access_agreement_signed

from coldfront.core.utils.common import session_wizard_all_form_data
from coldfront.core.utils.common import utc_now_offset_aware


logger = logging.getLogger(__name__)


class NewSecureDirRequestViewAccessibilityMixin(UserPassesTestMixin):
    """A mixin for determining whether views related to requesting new
    secure directories are accessible.

    Inheriting views must take a Project primary key via a "pk" URL
    argument."""

    def test_func(self):
        """Allow access to:
            - Superusers
            - Active PIs and Managers of the project who have signed the
              access agreement

        Disallow access if the project is ineligible to request
        secure directories.
        """
        project_obj = get_object_or_404(Project, pk=self.kwargs['pk'])
        user = self.request.user
        is_user_authorized = (
            user.is_superuser or
            is_user_manager_or_pi_of_project(user, project_obj))

        if not is_user_authorized:
            return False

        if not is_project_eligible_for_secure_dirs(project_obj):
            message = (
                f'Project {project_obj.name} is ineligible for secure '
                f'directories.')
            messages.error(self.request, message)
            return False

        if user.is_superuser:
            return True

        if not access_agreement_signed(user):
            message = (
                'Please sign the User Access Agreement before requesting a new '
                'secure directory.')
            messages.error(message)
            return False

        return True


class SecureDirRequestLandingView(LoginRequiredMixin,
                                  NewSecureDirRequestViewAccessibilityMixin,
                                  TemplateView):
    """A view for the secure directory request landing page."""

    template_name = \
        'secure_dir/secure_dir_request/secure_dir_request_landing.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._project_obj = None

    def dispatch(self, request, *args, **kwargs):
        self._project_obj = get_object_or_404(Project, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self._project_obj
        return context


class SecureDirRequestWizard(LoginRequiredMixin,
                             NewSecureDirRequestViewAccessibilityMixin,
                             SessionWizardView):

    FORMS = [
        ('pi_selection', SecureDirPISelectionForm),
        ('data_description', SecureDirDataDescriptionForm),
        ('rdm_consultation', SecureDirRDMConsultationForm),
        ('directory_name', SecureDirDirectoryNamesForm)
    ]

    TEMPLATES = {
        'pi_selection': 'secure_dir/secure_dir_request/pi_selection.html',
        'data_description':
            'secure_dir/secure_dir_request/data_description.html',
        'rdm_consultation':
            'secure_dir/secure_dir_request/rdm_consultation.html',
        'directory_name': 'secure_dir/secure_dir_request/directory_name.html'
    }

    form_list = [
        SecureDirPISelectionForm,
        SecureDirDataDescriptionForm,
        SecureDirRDMConsultationForm,
        SecureDirDirectoryNamesForm
    ]

    logger = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define a lookup table from form name to step number.
        self.step_numbers_by_form_name = {
            name: i for i, (name, _) in enumerate(self.FORMS)}
        self._project = None

    def dispatch(self, request, *args, **kwargs):
        self._project = get_object_or_404(Project, pk=kwargs.get('pk', None))
        # The inherited NewSecureDirRequestViewAccessibilityMixin ensures that
        # any Project with an existing secure directory or a request to create
        # one is denied access to this page.
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        current_step = int(self.steps.current)
        self._set_data_from_previous_steps(current_step, context)

        groups_path, scratch_path = get_default_secure_dir_paths()
        context['groups_path'] = groups_path
        context['scratch_path'] = scratch_path
        context['directory_name_prefix'] = SECURE_DIRECTORY_NAME_PREFIX

        return context

    def get_form_kwargs(self, step=None):
        kwargs = {}
        step = int(step)
        if step == self.step_numbers_by_form_name['pi_selection']:
            kwargs['project_pk'] = self._project.pk
        return kwargs

    def get_template_names(self):
        return [self.TEMPLATES[self.FORMS[int(self.steps.current)][0]]]

    def done(self, form_list, **kwargs):
        """Run the runner for handling a new request."""
        try:
            form_data = session_wizard_all_form_data(
                form_list, kwargs['form_dict'], len(self.form_list))
            request_kwargs = self._get_secure_dir_request_kwargs(form_data)
            secure_dir_request_runner = SecureDirRequestRunner(request_kwargs)
            secure_dir_request_runner.run()
        except Exception as e:
            self.logger.exception(e)
            message = 'Unexpected failure. Please contact an administrator.'
            messages.error(self.request, message)
        else:
            message = (
                'Thank you for your submission. It will be reviewed and '
                'processed by administrators.')
            messages.success(self.request, message)
        redirect_url = '/'
        return HttpResponseRedirect(redirect_url)

    @staticmethod
    def condition_dict():
        """Return a mapping from a string index `i` into FORMS
        (zero-indexed) to a function determining whether FORMS[int(i)]
        should be included."""
        view = SecureDirRequestWizard
        return {
            '2': view.show_rdm_consultation_form_condition,
        }

    def show_rdm_consultation_form_condition(self):
        step_name = 'data_description'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        return cleaned_data.get('rdm_consultation', False)

    def _get_secure_dir_request_kwargs(self, form_data):
        """Return keyword arguments needed to create a SecureDirRequest
        from the HttpRequest and provided form data.

        Note that the status need not be given because it is set by the
        runner.
        """
        return {
            'requester': self.request.user,
            'pi': self._get_pi_user(form_data),
            'department': self._get_department(form_data),
            'data_description': self._get_data_description(form_data),
            'rdm_consultation': self._get_rdm_consultation(form_data),
            'project': self._project,
            'directory_name': self._get_directory_name(form_data),
            'request_time': utc_now_offset_aware(),
        }

    def _get_department(self, form_data):
        """Return the department that the user submitted."""
        step_number = self.step_numbers_by_form_name['data_description']
        data = form_data[step_number]
        return data.get('department')

    def _get_data_description(self, form_data):
        """Return the data description the user submitted."""
        step_number = self.step_numbers_by_form_name['data_description']
        data = form_data[step_number]
        return data.get('data_description')

    def _get_rdm_consultation(self, form_data):
        """Return the consultants the user spoke to."""
        step_number = self.step_numbers_by_form_name['rdm_consultation']
        data = form_data[step_number]
        return data.get('rdm_consultants', None)

    def _get_directory_name(self, form_data):
        """Return the name of the directory."""
        step_number = self.step_numbers_by_form_name['directory_name']
        data = form_data[step_number]
        return data.get('directory_name', None)

    def _get_pi_user(self, form_data):
        """Return the selected PI User object."""
        step_number = self.step_numbers_by_form_name['pi_selection']
        data = form_data[step_number]
        pi_project_user = data['pi']
        return pi_project_user.user

    def _set_data_from_previous_steps(self, step, dictionary):
        """Update the given dictionary with data from previous steps."""
        dictionary['breadcrumb_project'] = f'Project: {self._project.name}'

        pi_selection_step = self.step_numbers_by_form_name['pi_selection']
        if step > pi_selection_step:
            pi_selection_form_data = self.get_cleaned_data_for_step(
                str(pi_selection_step))
            dictionary['breadcrumb_pi'] = (
                f'PI: {pi_selection_form_data["pi"].user.username}')

        rdm_consultation_step = self.step_numbers_by_form_name[
            'rdm_consultation']
        if step > rdm_consultation_step:
            rdm_consultation_form_data = self.get_cleaned_data_for_step(
                str(rdm_consultation_step))
            has_consulted_rdm = (
                'Yes' if rdm_consultation_form_data else 'No')
            dictionary['breadcrumb_rdm_consultation'] = (
                f'Consulted RDM: {has_consulted_rdm}')
