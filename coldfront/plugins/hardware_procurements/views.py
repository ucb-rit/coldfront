from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
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
    """A view for displaying the details of a particular
    HardwareProcurement."""

    template_name = 'hardware_procurements/hardware_procurement_detail.html'

    def __init__(self, *args, **kwargs):
         super().__init__(*args, **kwargs)
         self._procurement = None
         self._user_data = None

    def dispatch(self, request, *args, **kwargs):
        self._user_data = UserInfoDict.from_user(self.request.user)

        procurement_id = self.kwargs.get('procurement_id')
        try:
            self._procurement = self._fetch_procurement(procurement_id)
        except Exception as e:
            raise Http404('Invalid procurement.')

        if not self._check_permissions(self._procurement):
            raise PermissionDenied(
                'You do not have permission to access this procurement.')

        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        """Permissions are handled by _check_permissions after the
        HardwareProcurement object has been fetched."""
        return True

    def _check_permissions(self, hardware_procurement):
        """Return whether the requesting user has access to the given
        HardwareProcurement."""
        user = self.request.user
        # TODO: This is duplicated in this module.
        user_can_see_all_procurements = user.is_superuser or user.is_staff
        if user_can_see_all_procurements:
            return True
        if hardware_procurement.is_user_associated(self._user_data):
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['procurement'] = self._procurement
        return context

    def _fetch_procurement(self, procurement_id):
        """Return a HardwareProcurement object matching the given ID, if
        one exists. Otherwise, raise a ValueError.

        Limit the scope of the search if the requesting user does not
        have permission to view all procurements.
        """
        user = self.request.user

        fetch_hardware_procurements_kwargs = {}
        # TODO: This is duplicated in this module.
        user_can_see_all_procurements = user.is_superuser or user.is_staff
        if not user_can_see_all_procurements:
            fetch_hardware_procurements_kwargs['user_data'] = self._user_data

        for hardware_procurement in fetch_hardware_procurements(
                **fetch_hardware_procurements_kwargs):
            _procurement_id = hardware_procurement.get_id()
            if _procurement_id == procurement_id:
                return hardware_procurement

        raise ValueError(f'Could not fetch procurement {procurement_id}.')


class HardwareProcurementListView(LoginRequiredMixin, UserPassesTestMixin,
                                  TemplateView):
    """A view for displaying multiple HardwareProcurements."""

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
        for status in ('completed', 'inactive', 'pending', 'retired'):
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
        # TODO: This is duplicated in this module.
        user_can_see_all_procurements = user.is_superuser or user.is_staff

        # TODO: Move filtering (beyond status) to the utility method?
        pi_filter = None
        hardware_type_filter = None
        status_filter = 'pending'

        search_form = HardwareProcurementSearchForm(self.request.GET)
        if search_form.is_valid():
            data = search_form.cleaned_data
            if data.get('pi', None):
                pi_filter = data['pi']
            if data.get('hardware_type', None):
                hardware_type_filter = data['hardware_type']
            if data.get('status', None):
                status_filter = data['status']

        fetch_hardware_procurements_kwargs = {
            'status': status_filter.capitalize(),
        }
        if not user_can_see_all_procurements:
            fetch_hardware_procurements_kwargs['user_data'] = \
                UserInfoDict.from_user(user)
        hardware_procurements = fetch_hardware_procurements(
            **fetch_hardware_procurements_kwargs)

        filtered_hardware_procurements = []
        for hardware_procurement in hardware_procurements:

            procurement_data = hardware_procurement.get_data()
            procurement_data['id'] = hardware_procurement.get_id()

            if pi_filter is not None:
                pi_email = procurement_data.get('pi_email', None)
                if pi_email != pi_filter.email:
                    continue

            if hardware_type_filter is not None:
                hardware_type = procurement_data.get('hardware_type', None)
                if hardware_type != hardware_type_filter:
                    continue

            filtered_hardware_procurements.append(procurement_data)

        return filtered_hardware_procurements
