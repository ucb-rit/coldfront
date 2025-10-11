from gc import is_finalized
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView

from coldfront.core.utils.common import utc_now_offset_aware


class FakeStorageRequestDataMixin:
    """Mixin to provide fake storage request data for testing purposes."""
    _fake_data = {
        1: {
            'id': 1,
            'pk': 1,
            'status': {
                'name': 'Under Review',
            },
            'project': {
                'pk': 1,
                'name': 'fc_testproject',
            },
            'request_time': utc_now_offset_aware(),
            'requester': {
                'first_name': 'First',
                'last_name': 'Last',
                'email': 'firstlast@berkeley.edu',
            },
            'pi': {
                'first_name': 'First',
                'last_name': 'Last',
                'email': 'firstlast@berkeley.edu',
            },
            'amount': '1 TB',
            'state': {
                'eligibility': {
                    'status': 'Pending',
                    'timestamp': '',
                },
                'intake_consistency': {
                    'status': 'Pending',
                    'timestamp': '',
                    'final_amount': '',
                },
                'setup': {
                    'status': 'Pending',
                    'timestamp': '',
                },
                'other': {
                    'justification': '',
                    'timestamp': '',
                },
            }
        },
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

        eligibility = storage_request['state']['eligibility']
        checklist.append([
            'Confirm that the PI is eligible for free faculty storage.',
            eligibility['status'],
            eligibility['timestamp'],
            True,
            '#'
        ])
        is_eligible = eligibility['status'] == 'Approved'

        intake_consistency = storage_request['state']['intake_consistency']
        checklist.append([
            ('Confirm that the PI has completed the external intake form and '
             'that the storage amount requested here matches the amount '
             'specified there.'),
            intake_consistency['status'],
            intake_consistency['timestamp'],
            True,
            '#'
        ])
        is_instake_consistent = intake_consistency['status'] == 'Approved'

        setup = storage_request['state']['setup']
        checklist.append([
            'Perform storage setup on the cluster.',
            self._get_setup_status(),
            setup['timestamp'],
            is_eligible and is_instake_consistent,
            '#'
        ])

        return checklist

    def _get_setup_status(self):
        """Return one of the following statuses for the 'setup' step of
        the request: 'N/A', 'Pending', 'Complete'."""
        pk = self.kwargs.get('pk')
        storage_request = self.get_fake_storage_request(pk)

        state = storage_request['state']

        if (state['eligibility']['status'] == 'Denied' or
                state['intake_consistency']['status'] == 'Denied'):
            return 'N/A'
        return state['setup']['status']


__all__ = [
    'StorageRequestDetailView',
]
