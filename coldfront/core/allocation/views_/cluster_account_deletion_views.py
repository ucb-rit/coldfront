from itertools import chain

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import ListView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.allocation.forms_.cluster_acc_deletion_forms import \
    ClusterAccountDeletionSelfRequestForm
from coldfront.core.allocation.models import (Allocation,
                                              AllocationAttributeType,
                                              AllocationUserStatusChoice)
from coldfront.core.allocation.utils_.cluster_account_deletion_utils import \
    ClusterAccDeletionRequestRunner

from coldfront.core.project.forms_.removal_forms import \
    (ProjectRemovalRequestSearchForm,
     ProjectRemovalRequestUpdateStatusForm,
     ProjectRemovalRequestCompletionForm)
from coldfront.core.project.models import (Project,
                                           ProjectUserStatusChoice,
                                           ProjectUserRemovalRequest,
                                           ProjectUserRemovalRequestStatusChoice)
from coldfront.core.project.utils_.removal_utils import ProjectRemovalRequestRunner
from coldfront.core.utils.common import (import_from_settings,
                                         utc_now_offset_aware)
from coldfront.core.utils.mail import send_email_template

import logging

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)


class ClusterAccountDeletionSelfView(LoginRequiredMixin,
                                     UserPassesTestMixin,
                                     FormView):

    logger = logging.getLogger(__name__)
    form_class = ClusterAccountDeletionSelfRequestForm
    template_name = \
        'cluster_account_deletion/cluster_account_deletion_self.html'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        # TODO: who can request account deletion? Should we block PIs from deleting accounts?
        if self.request.user.userprofile.is_pi:
            return False

    def dispatch(self, request, *args, **kwargs):

        self.user_obj = get_object_or_404(
            User, pk=self.kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            request_runner = ClusterAccDeletionRequestRunner(self.request.user, 'User')
            runner_result = request_runner.run()
            success_messages, error_messages = request_runner.get_messages()

            if runner_result:
                request_runner.send_emails()
                for message in success_messages:
                    messages.success(self.request, message)
            else:
                for message in error_messages:
                    messages.error(self.request, message)
        except Exception as e:
            self.logger.exception(e)
            error_message = \
                'Unexpected error. Please contact an administrator.'
            messages.error(self.request, error_message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_obj'] = self.user_obj
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user_obj'] = self.user_obj

        return kwargs

    def get_success_url(self):
        return reverse('home')
