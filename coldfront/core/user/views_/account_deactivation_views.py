from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import FormView

from coldfront.core.allocation.models import ClusterAccountDeactivationRequest, \
    ClusterAccountDeactivationRequestStatusChoice
from coldfront.core.user.forms_.account_deactivation_forms import \
    AccountDeactivationRequestSearchForm, \
    AccountDeactivationCancelForm
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.views import ListViewClass


class AccountDeactivationRequestListView(LoginRequiredMixin,
                                         UserPassesTestMixin,
                                         ListViewClass):
    model = ClusterAccountDeactivationRequest
    template_name = 'account_deactivation/request_list.html'
    context_object_name = 'account_deactivation_requests'
    paginate_by = 25

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.view_clusteraccountdeactivationrequest'):
            return True

    def get_queryset(self):
        order_by = self.get_order_by()

        request_search_form = AccountDeactivationRequestSearchForm(
            self.request.GET)
        if request_search_form.is_valid():
            data = request_search_form.cleaned_data
            queryset = ClusterAccountDeactivationRequest.objects.all()

            if data.get('username'):
                queryset = queryset.filter(
                    user__username__icontains=data.get('username'))

            if data.get('first_name'):
                queryset = queryset.filter(
                    user__first_name__icontains=data.get('first_name'))

            if data.get('last_name'):
                queryset = queryset.filter(
                    user__last_name__icontains=data.get('last_name'))

            if data.get('status'):
                self.status = data.get('status')
                queryset = queryset.filter(status__name=self.status)
            else:
                queryset = queryset.filter(status__name='Ready')

            if data.get('reason'):
                queryset = queryset.filter(
                    reason__name=data.get('reason'))

        else:
            queryset = ClusterAccountDeactivationRequest.objects.filter(
                status__name='Ready')
            self.status = 'Ready'

        return queryset.order_by(order_by)

    def get_context_data(self, **kwargs):
        kwargs.update({'search_form': AccountDeactivationRequestSearchForm})
        context = super().get_context_data(**kwargs)

        context['status'] = self.status

        context['actions_visible'] = self.request.user.is_superuser and \
                                     context['status'] in ['Queued',
                                                           'Ready']

        return context


class AccountDeactivationRequestCancelView(LoginRequiredMixin,
                                           UserPassesTestMixin,
                                           FormView):
    form_class = AccountDeactivationCancelForm
    template_name = 'account_deactivation/cancel_request.html'
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.request_obj = ClusterAccountDeactivationRequest.objects.get(pk=pk)

        if self.request_obj.status.name not in ['Queued', 'Ready']:
            message = (
                f'You cannot perform this action on a request with status '
                f'{self.request_obj.status.name}.')
            messages.error(self.request, message)
            return HttpResponseRedirect(reverse('account-deactivation-request-list'))

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        justification = form_data['justification']

        self.request_obj.status = \
            ClusterAccountDeactivationRequestStatusChoice.objects.get(
                name='Cancelled')
        self.request_obj.state['other']['justification'] = \
            justification
        self.request_obj.state['other']['timestamp'] = \
            utc_now_offset_aware().isoformat()
        self.request_obj.save()

        message = (
            f'Cancelled ClusterAccountDeactivationRequest {self.request_obj.pk}'
            f' with the following justification: \"{justification}\".')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request_obj'] = self.request_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial['justification'] = self.request_obj.state['other']['justification']

        return initial

    def get_success_url(self):
        return reverse(
            'account-deactivation-request-list')
