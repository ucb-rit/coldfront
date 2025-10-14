from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.project.models import Project
from coldfront.core.utils.common import utc_now_offset_aware

from coldfront.plugins.cluster_storage.forms import StorageRequestEditForm
from coldfront.plugins.cluster_storage.forms import StorageRequestForm
from coldfront.plugins.cluster_storage.forms import StorageRequestReviewSetupForm
from coldfront.plugins.cluster_storage.forms import StorageRequestReviewStatusForm
from coldfront.plugins.cluster_storage.forms import StorageRequestSearchForm


class FakeStorageRequest:
    """Temporary class to stand in for a model."""
    def __init__(self, id, pk, status, project, request_time, requester, pi, amount, state):
        self.id = id
        self.pk = pk
        self.status = status
        self.project = project
        self.request_time = request_time
        self.requester = requester
        self.pi = pi
        self.amount = amount
        self.state = state


class FakeStorageRequestDataMixin:
    """Mixin to provide fake storage request data for testing purposes."""
    _fake_data = {
        1: FakeStorageRequest(
            id=1,
            pk=1,
            status={'name': 'Under Review'},
            project=Project(name='fc_testproject'),
            request_time=utc_now_offset_aware(),
            requester=User(
                first_name='First',
                last_name='Last',
                email='firstlast@berkeley.edu'),
            pi=User(
                first_name='First',
                last_name='Last',
                email='firstlast@berkeley.edu'),
            amount='1 TB',
            state={
                'eligibility': {
                    'status': 'Pending',
                    'justification': '',
                    'timestamp': '',
                },
                'intake_consistency': {
                    'status': 'Pending',
                    'justification': '',
                    'timestamp': '',
                    'final_amount': '',
                },
                'setup': {
                    'status': 'Pending',
                    'timestamp': '',
                    'directory_name': '',
                },
                'other': {
                    'justification': '',
                    'timestamp': '',
                },
            }
        ),
    }

    def get_fake_storage_request(self, pk):
        """Retrieve fake storage request data by primary key."""
        return self._fake_data.get(pk)


class StorageRequestDetailView(LoginRequiredMixin, UserPassesTestMixin,
                               FakeStorageRequestDataMixin, TemplateView):
    template_name = 'cluster_storage/approval/storage_request_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')  # Get the PK from the URL
        storage_request = self.get_fake_storage_request(pk)

        if not storage_request:
            context['storage_request'] = {'error': 'Storage request not found.'}
        else:
            context['storage_request'] = storage_request

        context['allow_editing'] = True
        context['is_allowed_to_manage_request'] = True  # TODO
        context['latest_update_timestamp'] = utc_now_offset_aware()
        context['checklist'] = self._get_checklist()
        return context

    def test_func(self):
        # TODO: Implement proper permission checks
        return True

    def _get_checklist(self):
        """Return a nested list, where each row contains the details of
        one item on the checklist.

        Each row is of the form: [task text, status name, latest update
        timestamp, is "Manage" button available, URL of "Manage" button].
        """
        pk = self.kwargs.get('pk')
        storage_request = self.get_fake_storage_request(pk)

        checklist = []

        eligibility = storage_request.state['eligibility']
        checklist.append([
            'Confirm that the PI is eligible for free faculty storage.',
            eligibility['status'],
            eligibility['timestamp'],
            True,
            reverse('storage-request-review-eligibility', kwargs={'pk': pk}),
        ])
        is_eligible = eligibility['status'] == 'Approved'

        intake_consistency = storage_request.state['intake_consistency']
        checklist.append([
            ('Confirm that the PI has completed the external intake form and '
             'that the storage amount requested here matches the amount '
             'specified there.'),
            intake_consistency['status'],
            intake_consistency['timestamp'],
            True,
            reverse(
                'storage-request-review-intake-consistency', kwargs={'pk': pk}),
        ])
        is_instake_consistent = intake_consistency['status'] == 'Approved'

        setup = storage_request.state['setup']
        checklist.append([
            'Perform storage setup on the cluster.',
            self._get_setup_status(),
            setup['timestamp'],
            True, # is_eligible and is_instake_consistent,  # TODO
            reverse('storage-request-review-setup', kwargs={'pk': pk})
        ])

        return checklist

    def _get_setup_status(self):
        """Return one of the following statuses for the 'setup' step of
        the request: 'N/A', 'Pending', 'Complete'."""
        pk = self.kwargs.get('pk')
        storage_request = self.get_fake_storage_request(pk)

        state = storage_request.state

        if (state['eligibility']['status'] == 'Denied' or
                state['intake_consistency']['status'] == 'Denied'):
            return 'N/A'
        return state['setup']['status']


class StorageRequestListView(LoginRequiredMixin, UserPassesTestMixin,
                             FakeStorageRequestDataMixin, TemplateView):
    template_name = 'cluster_storage/approval/storage_request_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self._storage_requests = [
            self.get_fake_storage_request(1),
        ]

        search_form = StorageRequestSearchForm(self.request.GET)
        if search_form.is_valid():
            context['search_form'] = search_form
            data = search_form.cleaned_data
            filter_parameters = urlencode(
                {key: value for key, value in data.items() if value})
        else:
            context['search_form'] = StorageRequestForm()
            filter_parameters = ''

        # Pagination expects the following context variable.
        context['filter_parameters_with_order_by'] = filter_parameters

        page = self.request.GET.get('page', 1)
        paginator = Paginator(self._storage_requests, 30)
        try:
            storage_requests = paginator.page(page)
        except PageNotAnInteger:
            storage_requests = paginator.page(1)
        except EmptyPage:
            storage_requests = paginator.page(paginator.num_pages)
        context['storage_requests']  = storage_requests

        list_url = reverse('storage-request-list')

        for status in StorageRequestSearchForm.STATUS_CHOICES:
            if status[0]:  # Ignore the blank choice.
                context[f'{status}_url'] = (
                    f'{list_url}?{urlencode({"status": status[1]})}')

        # Include information about the PI.
        context['display_user_info'] = True

        return context

    def test_func(self):
        # TODO
        return True


class StorageRequestEditView(LoginRequiredMixin, UserPassesTestMixin,
                             FakeStorageRequestDataMixin, FormView):
    form_class = StorageRequestEditForm
    template_name = 'cluster_storage/approval/storage_request_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')  # Get the PK from the URL
        storage_request = self.get_fake_storage_request(pk)

        if not storage_request:
            context['storage_request'] = {'error': 'Storage request not found.'}
        else:
            context['storage_request'] = storage_request

        context['is_allowed_to_manage_request'] = True  # TODO
        context['explanatory_paragraph'] = (
            'If necessary, update the amount of storage requested by the user.')
        context['page_title'] = 'Update Storage Amount'
        return context

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get('pk')  # Get the PK from the URL
        storage_request = self.get_fake_storage_request(pk)
        if storage_request:
            initial['storage_amount'] = storage_request.amount.split()[0]
        return initial

    # TODO: form_valid, other functions, etc.

    def get_success_url(self):
        pk = self.kwargs.get('pk')
        return reverse('storage-request-detail', kwargs={'pk': pk})

    def test_func(self):
        # TODO: Allow some other staff in a particular group.
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False


class StorageRequestReviewEligibilityView(LoginRequiredMixin,
                                          UserPassesTestMixin,
                                          FakeStorageRequestDataMixin,
                                          FormView):
    form_class = StorageRequestReviewStatusForm
    template_name = 'cluster_storage/approval/storage_request_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')  # Get the PK from the URL
        storage_request = self.get_fake_storage_request(pk)

        if not storage_request:
            context['storage_request'] = {'error': 'Storage request not found.'}
        else:
            context['storage_request'] = storage_request

        context['is_allowed_to_manage_request'] = True  # TODO
        context['explanatory_paragraph'] = (
            'Please determine whether the request\'s PI is eligible for free '
            'faculty storage. <b>As part of this, confirm that the PI does not '
            'already have existing free faculty storage.</b>If the PI is '
            'ineligible, the request will be denied immediately, and a '
            'notification email will be sent to the requester and PI.')
        context['page_title'] = 'Review Eligibility'
        return context

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get('pk')  # Get the PK from the URL
        storage_request = self.get_fake_storage_request(pk)
        eligibility = storage_request.state['eligibility']
        initial['status'] = eligibility['status']
        initial['justification'] = eligibility['justification']
        return initial

    # TODO: form_valid, other functions, etc.

    def get_success_url(self):
        pk = self.kwargs.get('pk')
        return reverse('storage-request-detail', kwargs={'pk': pk})

    def test_func(self):
        # TODO: Allow some other staff in a particular group.
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False


class StorageRequestReviewIntakeConsistencyView(LoginRequiredMixin,
                                                UserPassesTestMixin,
                                                FakeStorageRequestDataMixin,
                                                FormView):
    form_class = StorageRequestReviewStatusForm
    template_name = 'cluster_storage/approval/storage_request_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')  # Get the PK from the URL
        storage_request = self.get_fake_storage_request(pk)

        if not storage_request:
            context['storage_request'] = {'error': 'Storage request not found.'}
        else:
            context['storage_request'] = storage_request

        context['is_allowed_to_manage_request'] = True  # TODO
        context['explanatory_paragraph'] = (
            'Please confirm that the PI has completed the external intake form '
            'and that the storage amount requested matches the amount '
            'specified in the intake form.'
        )
        context['page_title'] = 'Review Intake Consistency'
        return context

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get('pk')  # Get the PK from the URL
        storage_request = self.get_fake_storage_request(pk)
        intake_consistency = storage_request.state['intake_consistency']
        initial['status'] = intake_consistency['status']
        initial['justification'] = intake_consistency['justification']
        return initial

    # TODO: form_valid, other functions, etc.

    def get_success_url(self):
        pk = self.kwargs.get('pk')
        return reverse('storage-request-detail', kwargs={'pk': pk})

    def test_func(self):
        # TODO: Allow some other staff in a particular group.
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False


class StorageRequestReviewSetupView(LoginRequiredMixin,
                                    UserPassesTestMixin,
                                    FakeStorageRequestDataMixin,
                                    FormView):
    form_class = StorageRequestReviewSetupForm
    template_name = 'cluster_storage/approval/storage_request_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')  # Get the PK from the URL
        storage_request = self.get_fake_storage_request(pk)

        if not storage_request:
            context['storage_request'] = {'error': 'Storage request not found.'}
        else:
            context['storage_request'] = storage_request

        context['is_allowed_to_manage_request'] = True  # TODO
        context['explanatory_paragraph'] = (
            'Please perform directory setup on the cluster.')
        context['page_title'] = 'Setup'
        return context

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get('pk')  # Get the PK from the URL
        storage_request = self.get_fake_storage_request(pk)
        setup = storage_request.state['setup']
        initial['status'] = setup['status']
        initial['directory_name'] = setup['directory_name']
        return initial

    # TODO: form_valid, other functions, etc.

    def get_success_url(self):
        pk = self.kwargs.get('pk')
        return reverse('storage-request-detail', kwargs={'pk': pk})

    def test_func(self):
        # TODO: Allow some other staff in a particular group.
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False


__all__ = [
    'StorageRequestDetailView',
    'StorageRequestEditView',
    'StorageRequestListView',
    'StorageRequestReviewEligibilityView',
    'StorageRequestReviewIntakeConsistencyView',
    'StorageRequestReviewSetupView',
]
