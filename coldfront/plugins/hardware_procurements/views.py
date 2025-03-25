from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.paginator import EmptyPage
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator
from django.http import Http404
from django.urls import reverse
from django.views.generic import TemplateView

from coldfront.plugins.hardware_procurements.forms import HardwareProcurementSearchForm
from coldfront.plugins.hardware_procurements.utils import UserInfoDict
from coldfront.plugins.hardware_procurements.utils.data_sources import fetch_hardware_procurements


class HardwareProcurementDetailView(LoginRequiredMixin, UserPassesTestMixin,
                                    TemplateView):
    """TODO"""

    template_name = 'hardware_procurements/hardware_procurement_detail.html'

    def __init__(self, *args, **kwargs):
         super().__init__(*args, **kwargs)
         self._procurement = None

    def dispatch(self, request, *args, **kwargs):
        procurement_id = self.kwargs.get('procurement_id')
        try:
            self._procurement = self._fetch_procurement(procurement_id)
        except Exception as e:
            raise Http404('Invalid procurement.')

        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['procurement'] = self._procurement
        return context

    def _fetch_procurement(self, procurement_id):
        """TODO"""
        # TODO: Write a helper method that gets the object based on ID.
        # TODO: Caching...
        for procurement in fetch_hardware_procurements():
            # print(procurement)
            if procurement['id'] == procurement_id:
                return procurement
        raise ValueError(f'Could not fetch procurement {procurement_id}.')


class HardwareProcurementListView(LoginRequiredMixin, UserPassesTestMixin,
                                  TemplateView):
    """TODO"""

    template_name = 'hardware_procurements/hardware_procurement_list.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._procurements = []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        self._procurements = self._get_procurements()

        search_form = HardwareProcurementSearchForm(self.request.GET)
        if search_form.is_valid():
            context['search_form'] = search_form
        else:
            context['search_form'] = HardwareProcurementSearchForm()

        page = self.request.GET.get('page', 1)
        paginator = Paginator(self._procurements, 30)
        try:
            procurements = paginator.page(page)
        except PageNotAnInteger:
            procurements = paginator.page(1)
        except EmptyPage:
            procurements = paginator.page(paginator.num_pages)
        context['procurements']  = procurements

        list_url = reverse('hardware-procurement-list')

        # TODO: Avoid hard-coding statuses.
        for status in ('completed', 'inactive', 'pending'):
            context[f'{status}_url'] = (
                f'{list_url}?{urlencode({"status": status})}')

        # Include information about the PI.
        context['display_user_info'] = True

        return context

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.is_staff

    def _get_procurements(self):
        """TODO"""
        user = self.request.user
        user_can_see_all_procurements = user.is_superuser or user.is_staff

        fetch_hardware_procurements_kwargs = {}
        if not user_can_see_all_procurements:
            fetch_hardware_procurements_kwargs['user_data'] = \
                UserInfoDict.from_user(user)
        hardware_procurements = fetch_hardware_procurements(
            **fetch_hardware_procurements_kwargs)

        # TODO: (MUST) Move filtering to the utility method.
        pi_filter = None
        hardware_type_filter = None
        status_filter = 'pending'

        # TODO: Avoid hard-coding statuses.
        # TODO: These misspellings should be corrected in the source.
        status_mapping = {
            'completed': {'Complete', 'Completed', 'Compelete', 'Compeleted',},
            'inactive': {'Inactive',},
            'pending': {'Active',},
        }

        search_form = HardwareProcurementSearchForm(self.request.GET)
        if search_form.is_valid():
            data = search_form.cleaned_data
            if data.get('pi', None):
                pi_filter = data['pi']
            if data.get('hardware_type', None):
                hardware_type_filter = data['hardware_type']
            if data.get('status', None):
                status_filter = data['status']

        filtered_hardware_procurements = []
        for hardware_procurement in hardware_procurements:

            if pi_filter is not None:
                pi_email = hardware_procurement.get('pi_email', None)
                if pi_email != pi_filter.email:
                    continue

            if hardware_type_filter is not None:
                hardware_type = hardware_procurement.get('hardware_type', None)
                if hardware_type != hardware_type_filter:
                    continue

            if status_filter is not None:
                procurement_status = hardware_procurement.get('status', None)
                if procurement_status not in status_mapping[status_filter]:
                    continue

            filtered_hardware_procurements.append(hardware_procurement)

        return filtered_hardware_procurements
