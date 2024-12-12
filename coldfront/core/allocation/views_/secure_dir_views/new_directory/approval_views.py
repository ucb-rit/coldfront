import iso8601
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic.base import TemplateView
from django.views.generic.base import View

from coldfront.core.allocation.forms_.secure_dir_forms import SecureDirRDMConsultationReviewForm
from coldfront.core.allocation.forms_.secure_dir_forms import SecureDirRequestEditDepartmentForm
from coldfront.core.allocation.forms_.secure_dir_forms import SecureDirSetupForm
from coldfront.core.allocation.models import SecureDirRequest
from coldfront.core.allocation.models import SecureDirRequestStatusChoice
from coldfront.core.allocation.utils_.secure_dir_utils.new_directory import get_secure_dir_allocations
from coldfront.core.allocation.utils_.secure_dir_utils.new_directory import secure_dir_request_state_status
from coldfront.core.allocation.utils_.secure_dir_utils.new_directory import SecureDirRequestApprovalRunner
from coldfront.core.allocation.utils_.secure_dir_utils.new_directory import SecureDirRequestDenialRunner
from coldfront.core.allocation.utils_.secure_dir_utils.new_directory import set_sec_dir_context

from coldfront.core.project.forms import ReviewStatusForm, ReviewDenyForm

from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.views.mou_views import MOURequestNotifyPIViewMixIn


logger = logging.getLogger(__name__)


class SecureDirRequestListView(LoginRequiredMixin,
                               UserPassesTestMixin,
                               TemplateView):

    template_name = 'secure_dir/secure_dir_request/secure_dir_request_list.html'
    # Show completed requests if True; else, show pending requests.
    completed = False

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.view_securedirrequest'):
            return True

        message = (
            'You do not have permission to view the previous page.')
        messages.error(self.request, message)

    def get_queryset(self):
        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            else:
                direction = '-'
            order_by = direction + order_by
        else:
            order_by = '-modified'

        return SecureDirRequest.objects.order_by(order_by)

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests."""
        context = super().get_context_data(**kwargs)
        kwargs = {}

        request_list = self.get_queryset()

        if self.completed:
            status__name__in = [
                'Approved - Complete', 'Denied']
        else:
            status__name__in = ['Under Review', 'Approved - Processing']

        kwargs['status__name__in'] = status__name__in
        context['secure_dir_request_list'] = request_list.filter(**kwargs)

        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        return context


class SecureDirRequestMixin(object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_obj = None

    def redirect_if_disallowed_status(self, http_request,
                                      disallowed_status_names=(
                                              'Approved - Complete',
                                              'Denied')):
        """Return a redirect response to the detail view for this
        project request if its status has one of the given disallowed
        names, after sending a message to the user. Otherwise, return
        None."""
        if not isinstance(self.request_obj, SecureDirRequest):
            raise TypeError(
                f'Request object has unexpected type '
                f'{type(self.request_obj)}.')
        status_name = self.request_obj.status.name
        if status_name in disallowed_status_names:
            message = (
                f'You cannot perform this action on a request with status '
                f'{status_name}.')
            messages.error(http_request, message)
            return HttpResponseRedirect(
                self.request_detail_url(self.request_obj.pk))
        return None

    @staticmethod
    def request_detail_url(pk):
        """Return the URL to the detail view for the request with the
        given primary key."""
        return reverse('secure-dir-request-detail', kwargs={'pk': pk})

    def set_request_obj(self, pk):
        """Set this instance's request_obj to be the SecureDirRequest with
        the given primary key."""
        self.request_obj = get_object_or_404(SecureDirRequest, pk=pk)


class SecureDirRequestDetailView(LoginRequiredMixin,
                                 UserPassesTestMixin,
                                 SecureDirRequestMixin,
                                 DetailView):
    model = SecureDirRequest
    template_name = \
        'secure_dir/secure_dir_request/secure_dir_request_detail.html'
    context_object_name = 'secure_dir_request'

    logger = logging.getLogger(__name__)

    error_message = 'Unexpected failure. Please contact an administrator.'

    redirect = reverse_lazy('secure-dir-pending-request-list')

    def test_func(self):
        """Allow access to:
            - Superusers
            - Users with access to view SecureDirRequests
            - Active PIs of the project
            - The user who made the request
        """
        user = self.request.user

        if user.is_superuser:
            return True

        if user.has_perm('allocation.view_securedirrequest'):
            return True

        pis = self.request_obj.project.projectuser_set.filter(
            role__name='Principal Investigator',
            status__name='Active').values_list('user__pk', flat=True)
        if user.pk in pis:
            return True

        if user == self.request_obj.requester:
            return True

        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            latest_update_timestamp = \
                self.request_obj.latest_update_timestamp()
            if not latest_update_timestamp:
                latest_update_timestamp = 'No updates yet.'
            else:
                # TODO: Upgrade to Python 3.7+ to use this.
                # latest_update_timestamp = datetime.datetime.fromisoformat(
                #     latest_update_timestamp)
                latest_update_timestamp = iso8601.parse_date(
                    latest_update_timestamp)
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
            latest_update_timestamp = 'Failed to determine timestamp.'
        context['latest_update_timestamp'] = latest_update_timestamp

        if self.request_obj.status.name == 'Denied':
            try:
                denial_reason = self.request_obj.denial_reason()
                category = denial_reason.category
                justification = denial_reason.justification
                timestamp = denial_reason.timestamp
            except Exception as e:
                self.logger.exception(e)
                messages.error(self.request, self.error_message)
                category = 'Unknown Category'
                justification = (
                    'Failed to determine denial reason. Please contact an '
                    'administrator.')
                timestamp = 'Unknown Timestamp'
            context['denial_reason'] = {
                'category': category,
                'justification': justification,
                'timestamp': timestamp,
            }
            context['support_email'] = settings.CENTER_HELP_EMAIL

        context['checklist'] = self.get_checklist()
        context['setup_status'] = self.get_setup_status()
        context['is_checklist_complete'] = self.is_checklist_complete()

        context['is_allowed_to_manage_request'] = \
            self.request.user.is_superuser

        context['secure_dir_request'] = self.request_obj

        context['can_download_mou'] = self.request_obj \
                                    .state['notified']['status'] == 'Complete'
        context['can_upload_mou'] = \
            self.request_obj.status.name == 'Under Review'
        context['mou_uploaded'] = bool(self.request_obj.mou_file)

        context['unsigned_download_url'] = reverse('secure-dir-request-download-unsigned-mou',
                                                    kwargs={'pk': self.request_obj.pk,
                                                            'request_type': 'secure-dir'})
        context['signed_download_url'] = reverse('secure-dir-request-download-mou',
                                                    kwargs={'pk': self.request_obj.pk,
                                                            'request_type': 'secure-dir'})
        context['signed_upload_url'] = reverse('secure-dir-request-upload-mou',
                                                    kwargs={'pk': self.request_obj.pk,
                                                            'request_type': 'secure-dir'})
        context['mou_type'] = 'Researcher Use Agreement'

        set_sec_dir_context(context, self.request_obj)

        return context

    def get_checklist(self):
        """Return a nested list, where each row contains the details of
        one item on the checklist.
        Each row is of the form: [task text, status name, latest update
        timestamp, is "Manage" button available, URL of "Manage"
        button.]"""
        pk = self.request_obj.pk
        state = self.request_obj.state
        checklist = []

        rdm = state['rdm_consultation']
        checklist.append([
            'Confirm that the PI has consulted with RDM.',
            rdm['status'],
            rdm['timestamp'],
            True,
            reverse(
                'secure-dir-request-review-rdm-consultation', kwargs={'pk': pk})
        ])
        rdm_consulted = rdm['status'] == 'Approved'
        
        notified = state['notified']
        task_text = (
            'Confirm or edit allowance details, and '
            'enable/notify the PI to sign the Researcher Use Agreement.')
        checklist.append([
            task_text,
            notified['status'],
            notified['timestamp'],
            True,
            reverse('secure-dir-request-notify-pi',
                    kwargs={'pk': pk})
        ])
        is_notified = notified['status'] == 'Complete'

        mou = state['mou']
        checklist.append([
            'Confirm that the PI has signed the Researcher Use Agreement.',
            mou['status'],
            mou['timestamp'],
            is_notified,
            reverse(
                'secure-dir-request-review-mou', kwargs={'pk': pk})
        ])
        mou_signed = mou['status'] == 'Approved'

        setup = state['setup']
        checklist.append([
            'Perform secure directory setup on the cluster.',
            self.get_setup_status(),
            setup['timestamp'],
            rdm_consulted and is_notified and mou_signed,
            reverse('secure-dir-request-review-setup', kwargs={'pk': pk})
        ])

        return checklist

    def post(self, request, *args, **kwargs):
        """Approve the request."""
        if not self.request.user.is_superuser:
            message = 'You do not have permission to access this page.'
            messages.error(request, message)
            pk = self.request_obj.pk

            return HttpResponseRedirect(
                reverse('secure-dir-request-detail', kwargs={'pk': pk}))

        if not self.is_checklist_complete():
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            pk = self.request_obj.pk
            return HttpResponseRedirect(
                reverse('secure-dir-request-detail', kwargs={'pk': pk}))

        # Check that the project does not have any Secure Directories yet.
        sec_dir_allocations = get_secure_dir_allocations()
        if sec_dir_allocations.filter(project=self.request_obj.project).exists():
            message = f'The project {self.request_obj.project.name} already ' \
                      f'has a secure directory associated with it.'
            messages.error(self.request, message)
            pk = self.request_obj.pk
            return HttpResponseRedirect(
                reverse('secure-dir-request-detail', kwargs={'pk': pk}))

        # Approve the request.
        runner = SecureDirRequestApprovalRunner(self.request_obj)
        runner.run()

        success_messages, error_messages = runner.get_messages()
        for message in success_messages:
            messages.success(self.request, message)
        for message in error_messages:
            messages.error(self.request, message)

        return HttpResponseRedirect(self.redirect)

    def get_setup_status(self):
        """Return one of the following statuses for the 'setup' step of
        the request: 'N/A', 'Pending', 'Completed'."""
        state = self.request_obj.state
        if (state['rdm_consultation']['status'] == 'Denied' or
                state['mou']['status'] == 'Denied'):
            return 'N/A'
        return state['setup']['status']

    def is_checklist_complete(self):
        status_choice = secure_dir_request_state_status(self.request_obj)
        return (status_choice.name == 'Approved - Processing' and
                self.request_obj.state['setup']['status'] == 'Completed')


class SecureDirRequestReviewRDMConsultView(LoginRequiredMixin,
                                           UserPassesTestMixin,
                                           SecureDirRequestMixin,
                                           FormView):
    form_class = SecureDirRDMConsultationReviewForm
    template_name = (
        'secure_dir/secure_dir_request/secure_dir_consult_rdm.html')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk=pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        rdm_update = form_data['rdm_update']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['rdm_consultation'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = \
            secure_dir_request_state_status(self.request_obj)
        self.request_obj.rdm_consultation = rdm_update
        self.request_obj.save()

        if status == 'Denied':
            runner = SecureDirRequestDenialRunner(self.request_obj)
            runner.run()

        message = (
            f'RDM consultation status for {self.request_obj.project.name}\'s '
            f'secure directory request has been set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        set_sec_dir_context(context, self.request_obj)
        return context

    def get_initial(self):
        initial = super().get_initial()
        rdm_consultation = self.request_obj.state['rdm_consultation']
        initial['status'] = rdm_consultation['status']
        initial['justification'] = rdm_consultation['justification']
        initial['rdm_update'] = self.request_obj.rdm_consultation

        return initial

    def get_success_url(self):
        return reverse(
            'secure-dir-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SecureDirRequestReviewMOUView(LoginRequiredMixin,
                                    UserPassesTestMixin,
                                    SecureDirRequestMixin,
                                    FormView):
    form_class = ReviewStatusForm
    template_name = (
        'secure_dir/secure_dir_request/secure_dir_mou.html')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk=pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['mou'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = \
            secure_dir_request_state_status(self.request_obj)
        self.request_obj.save()

        if status == 'Denied':
            runner = SecureDirRequestDenialRunner(self.request_obj)
            runner.run()

        message = (
            f'MOU status for the secure directory request of project '
            f'{self.request_obj.project.pk} has been set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        set_sec_dir_context(context, self.request_obj)
        return context

    def get_initial(self):
        initial = super().get_initial()
        mou = self.request_obj.state['mou']
        initial['status'] = mou['status']
        initial['justification'] = mou['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'secure-dir-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SecureDirRequestReviewSetupView(LoginRequiredMixin,
                                      UserPassesTestMixin,
                                      SecureDirRequestMixin,
                                      FormView):
    form_class = SecureDirSetupForm
    template_name = (
        'secure_dir/secure_dir_request/secure_dir_setup.html')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk=pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['dir_name'] = self.request_obj.directory_name
        kwargs['request_pk'] = self.request_obj.pk
        return kwargs

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        directory_name = form_data['directory_name']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['setup'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = \
            secure_dir_request_state_status(self.request_obj)
        if directory_name:
            self.request_obj.directory_name = directory_name
        self.request_obj.save()

        if status == 'Denied':
            runner = SecureDirRequestDenialRunner(self.request_obj)
            runner.run()

        message = (
            f'Setup status for {self.request_obj.project.name}\'s '
            f'secure directory request has been set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        set_sec_dir_context(context, self.request_obj)
        return context

    def get_initial(self):
        initial = super().get_initial()
        setup = self.request_obj.state['setup']
        initial['status'] = setup['status']
        initial['justification'] = setup['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'secure-dir-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SecureDirRequestReviewDenyView(LoginRequiredMixin, UserPassesTestMixin,
                                     SecureDirRequestMixin, FormView):
    form_class = ReviewDenyForm
    template_name = (
        'secure_dir/secure_dir_request/secure_dir_review_deny.html')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data

        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['other'] = {
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.save()

        # Deny the request.
        runner = SecureDirRequestDenialRunner(self.request_obj)
        runner.run()

        success_messages, error_messages = runner.get_messages()
        for message in success_messages:
            messages.success(self.request, message)
        for message in error_messages:
            messages.error(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        set_sec_dir_context(context, self.request_obj)
        return context

    def get_initial(self):
        initial = super().get_initial()
        other = self.request_obj.state['other']
        initial['justification'] = other['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'secure-dir-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SecureDirRequestUndenyRequestView(LoginRequiredMixin,
                                        UserPassesTestMixin,
                                        SecureDirRequestMixin,
                                        View):

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = (
            'You do not have permission to undeny a secure directory request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk)

        disallowed_status_names = list(
            SecureDirRequestStatusChoice.objects.filter(
                ~Q(name='Denied')).values_list('name', flat=True))
        redirect = self.redirect_if_disallowed_status(
            request, disallowed_status_names=disallowed_status_names)
        if redirect is not None:
            return redirect

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        state = self.request_obj.state

        rdm_consultation = state['rdm_consultation']
        if rdm_consultation['status'] == 'Denied':
            rdm_consultation['status'] = 'Pending'
            rdm_consultation['timestamp'] = ''
            rdm_consultation['justification'] = ''

        mou = state['mou']
        if mou['status'] == 'Denied':
            mou['status'] = 'Pending'
            mou['timestamp'] = ''
            mou['justification'] = ''

        setup = state['setup']
        if setup['status'] != 'Pending':
            setup['status'] = 'Pending'
            setup['timestamp'] = ''
            setup['justification'] = ''

        other = state['other']
        if other['timestamp']:
            other['justification'] = ''
            other['timestamp'] = ''

        self.request_obj.status = \
            secure_dir_request_state_status(self.request_obj)
        self.request_obj.save()

        message = (
            f'Secure directory request for {self.request_obj.project.name} has '
            f'been un-denied and will need to be reviewed again.')
        messages.success(request, message)

        return HttpResponseRedirect(
            reverse(
                'secure-dir-request-detail',
                kwargs={'pk': kwargs.get('pk')}))


class SecureDirRequestEditDepartmentView(LoginRequiredMixin,
                                         UserPassesTestMixin,
                                         SecureDirRequestMixin,
                                         FormView):
    template_name = 'secure_dir/secure_dir_request/secure_dir_request_edit_department.html'
    form_class = SecureDirRequestEditDepartmentForm

    logger = logging.getLogger(__name__)

    error_message = 'Unexpected failure. Please contact an administrator.'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'].initial['department'] = self.request_obj.department
        context['secure_dir_request'] = self.request_obj
        context['notify_pi'] = False
        return context

    def form_valid(self, form):
        """Save the form."""
        self.request_obj.department = form.cleaned_data.get('department')
        self.request_obj.save()
        message = 'The request has been updated.'
        messages.success(self.request, message)
        return HttpResponseRedirect(reverse('secure-dir-request-detail',
                                            kwargs={'pk':self.request_obj.pk}))

    def form_invalid(self, form):
        """Handle invalid forms."""
        message = 'Please correct the errors below.'
        messages.error(self.request, message)
        return self.render_to_response(
            self.get_context_data(form=form))


class SecureDirRequestNotifyPIView(MOURequestNotifyPIViewMixIn,
                                   SecureDirRequestEditDepartmentView):
    def email_pi(self):
        super()._email_pi('Secure Directory Request Ready To Be Signed',
                         self.request_obj.pi.get_full_name(),
                         reverse('secure-dir-request-detail',
                                 kwargs={'pk': self.request_obj.pk}),
                         'Researcher Use Agreement',
                         f'{self.request_obj.project.name} secure directory request',
                         self.request_obj.pi.email)
