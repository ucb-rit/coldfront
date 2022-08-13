from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

from django.contrib.auth.models import User
from django.urls import reverse

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.allocation.models import (ClusterAccountDeactivationRequestStatusChoice,
                                              ClusterAccountDeactivationRequestReasonChoice,
                                              ClusterAccountDeactivationRequest)
from coldfront.core.allocation.utils import get_reason_legend_dict
from coldfront.core.project.models import Project, ProjectStatusChoice, \
    ProjectUserRoleChoice, ProjectUserStatusChoice, ProjectUser
from coldfront.core.resource.models import ResourceType, Resource
from coldfront.core.user.utils import get_compute_resources_for_user
from coldfront.core.utils.common import utc_now_offset_aware, \
    import_from_settings, utc_datetime_to_display_time_zone_date
from coldfront.core.utils.tests.test_base import TestBase


class TestAccountDeactivationRequestBase(TestBase):
    """A base testing class for account deactivation requests."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        for i in range(5):
            user = User.objects.create(username=f'user{i}')
            setattr(self, f'user{i}', user)

        active_project_status = \
            ProjectStatusChoice.objects.get(name='Active')
        active_project_user_status = \
            ProjectUserStatusChoice.objects.get(name='Active')
        user_role = ProjectUserRoleChoice.objects.get(name='User')
        allocation_amount = Decimal('1000.0')

        cluster_type = ResourceType.objects.get(name='Cluster')
        self.compute1 = Resource.objects.create(name='TEST1 Compute',
                                                resource_type=cluster_type)
        self.compute2 = Resource.objects.create(name='TEST2 Compute',
                                                resource_type=cluster_type)

        for i in range(2):
            project = Project.objects.create(
                name=f'project{i}', status=active_project_status)
            setattr(self, project.name, project)
            allocation_objects = create_project_allocation(
                project, allocation_amount)
            allocation_objects.allocation.resources.add(self.compute1,
                                                        self.compute2)
            allocation_objects.allocation.save()

            for j in range(5):
                user = getattr(self, f'user{j}')
                ProjectUser.objects.create(
                    project=project,
                    user=user,
                    role=user_role,
                    status=active_project_user_status)

        no_valid_account = \
            ClusterAccountDeactivationRequestReasonChoice.objects.get(
                name='NO_VALID_USER_ACCOUNT_FEE_BILLING_ID')
        no_valid_recharge = \
            ClusterAccountDeactivationRequestReasonChoice.objects.get(
                name='NO_VALID_RECHARGE_USAGE_FEE_BILLING_ID')

        self.expiration_offset = \
            import_from_settings('ACCOUNT_DEACTIVATION_AUTO_QUEUE_DAYS')

        self.request_dict = {
            'request0': {'user': self.user0,
                         'status':
                             ClusterAccountDeactivationRequestStatusChoice.objects.get(
                                 name='Queued'),
                         'reason': no_valid_account,
                         'expiration': self._get_offset_time(),
                         'recharge_project_pk': ''},
            'request1': {'user': self.user1,
                         'status':
                             ClusterAccountDeactivationRequestStatusChoice.objects.get(
                                 name='Ready'),
                         'reason': no_valid_recharge,
                         'expiration': self._get_offset_time(),
                         'recharge_project_pk': self.project1.pk},
            'request2': {'user': self.user2,
                         'status':
                             ClusterAccountDeactivationRequestStatusChoice.objects.get(
                                 name='Processing'),
                         'reason': no_valid_recharge,
                         'expiration': self._get_offset_time(),
                         'recharge_project_pk': self.project0.pk},
            'request3': {'user': self.user3,
                         'status':
                             ClusterAccountDeactivationRequestStatusChoice.objects.get(
                                 name='Complete'),
                         'reason': no_valid_account,
                         'expiration': self._get_offset_time(),
                         'recharge_project_pk': ''},
            'request4': {'user': self.user4,
                         'status':
                             ClusterAccountDeactivationRequestStatusChoice.objects.get(
                                 name='Cancelled'),
                         'reason': no_valid_account,
                         'expiration': self._get_offset_time(),
                         'recharge_project_pk': ''},
        }

        for name, kwargs in self.request_dict.items():
            recharge_project_pk = kwargs.pop('recharge_project_pk')
            request = ClusterAccountDeactivationRequest.objects.create(**kwargs)
            request.state['recharge_project_pk'] = recharge_project_pk
            request.save()
            kwargs['recharge_project_pk'] = recharge_project_pk
            setattr(self, name, request)

        self.staff = User.objects.create(username='staff', is_staff=True)

        self.superuser = User.objects.create(username='superuser',
                                             is_superuser=True)

        self.password = 'password'
        for user in User.objects.all():
            self.sign_user_access_agreement(user)
            user.set_password(self.password)
            user.save()

    def _get_offset_time(self):
        return utc_now_offset_aware() + timedelta(days=self.expiration_offset)


class TestAccountDeactivationRequestListView(
    TestAccountDeactivationRequestBase):
    """A testing class for AccountDeactivationRequestListView."""

    def setUp(self):
        super().setUp()
        self.url = 'account-deactivation-request-list'

    def _assert_recharge_visible(self, recharge_pk, html):
        if recharge_pk:
            recharge_name = Project.objects.get(pk=recharge_pk).name
        else:
            recharge_name = 'N/A'
        self.assertIn(recharge_name, html)

    def _assert_compute_visible(self, user, html):
        compute_resources = get_compute_resources_for_user(user)
        compute_resources = ', '.join([resource.name.replace('Compute', '').strip()
                                       for resource in compute_resources])
        self.assertIn(compute_resources, html)

    def _assert_actions_visible(self, superuser, status, html):
        visible = status in ['Queued', 'Ready'] and superuser
        button = '<a href="/user/account-deactivation-request-cancel/'
        if visible:
            self.assertIn(button, html)
        else:
            self.assertNotIn(button, html)

    def _assert_correct_status_badge(self, status, html):
        if status == 'Complete':
            status_badge = 'success'
        elif status == 'Cancelled':
            status_badge = 'danger'
        else:
            status_badge = 'warning'
        status_badge_html = f'<span class="badge badge-{status_badge}">' \
                            f'{status}</span>'
        self.assertIn(status_badge_html, html)

    def _assert_correct_user(self, username, html):
        link = f'<a href="/user/user-profile/{username}">{username}</a>'
        self.assertIn(link, html)

    def _assert_expiration(self, kwargs, html):
        kwargs_copy = kwargs.copy()
        kwargs_copy.pop('recharge_project_pk')
        if kwargs_copy['status'].name == 'Queued':
            self.assertIn('Expiration', html)
            request = \
                ClusterAccountDeactivationRequest.objects.get(**kwargs_copy)
            expected = \
                utc_datetime_to_display_time_zone_date(request.expiration)
            self.assertIn(expected.strftime('%b. %d, %Y'), html)
        else:
            self.assertNotIn('Expiration', html)

    def _assert_correct_reason(self, reason, html):
        legend_dict = get_reason_legend_dict()
        if reason.name == 'NO_VALID_USER_ACCOUNT_FEE_BILLING_ID':
            badge = f'<span class="badge badge-primary">' \
                    f'{legend_dict[reason]}</span>\n'
            self.assertIn(badge, html)
        if reason.name == 'NO_VALID_RECHARGE_USAGE_FEE_BILLING_ID':
            badge = f'<span class="badge badge-info">' \
                    f'{legend_dict[reason]}</span>\n'
            self.assertIn(badge, html)

    def _assert_content_shown(self, user, request_kwargs):
        url = f'{reverse(self.url)}?status={request_kwargs["status"].name}'

        self.client.login(username=user.username, password=self.password)
        response = self.client.get(url)
        html = response.content.decode('utf-8')

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self._assert_correct_reason(request_kwargs['reason'], html)
        self._assert_correct_user(request_kwargs['user'].username, html)
        self._assert_correct_status_badge(request_kwargs['status'].name, html)
        self._assert_actions_visible(user.is_superuser,
                                     request_kwargs['status'].name, html)
        self._assert_expiration(request_kwargs, html)
        self._assert_compute_visible(request_kwargs['user'], html)
        self._assert_recharge_visible(request_kwargs['recharge_project_pk'],
                                      html)

    def test_access(self):
        url = reverse(self.url)
        self.assert_has_access(url, self.superuser, True)
        self.assert_has_access(url, self.staff, True)
        self.assert_has_access(url, self.user0, False)

    def test_content(self):
        for _, kwargs in self.request_dict.items():
            self._assert_content_shown(self.superuser, kwargs)
            self._assert_content_shown(self.staff, kwargs)


class TestAccountDeactivationRequestCancelView(
    TestAccountDeactivationRequestBase):
    """A testing class for AccountDeactivationRequestCancelView."""

    def setUp(self):
        super().setUp()
        self.url = 'account-deactivation-request-cancel'

    def test_access(self):
        url = reverse(self.url, kwargs={'pk': self.request0.pk})
        self.assert_has_access(url, self.superuser, True)
        self.assert_has_access(url, self.staff, False)
        self.assert_has_access(url, self.user0, False)

    def test_status_redirect(self):
        """Assert that a request with a bad status redirects correctly."""
        self.client.login(username=self.superuser, password=self.password)

        for request in [self.request0, self.request1]:
            url = reverse(self.url, kwargs={'pk': request.pk})
            response = self.client.get(url)
            self.assertEqual(response.status_code, HTTPStatus.OK)

        for request in [self.request2, self.request3, self.request4]:
            url = reverse(self.url, kwargs={'pk': request.pk})
            response = self.client.get(url)
            self.assertEqual(response.status_code, HTTPStatus.FOUND)
            self.assertRedirects(response,
                                 reverse('account-deactivation-request-list'))

    def test_post_updates_request(self):
        """Test that a post request correctly updates the request."""
        self.client.login(username=self.superuser, password=self.password)

        self.assertEqual(self.request0.status.name, 'Queued')
        self.assertEqual(self.request0.state['cancellation_justification'], '')

        url = reverse(self.url, kwargs={'pk': self.request0.pk})
        data = {'justification': 'This is a test cancellation justification.'}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response,
                             reverse('account-deactivation-request-list'))

        self.request0.refresh_from_db()
        self.assertEqual(self.request0.status.name, 'Cancelled')
        self.assertEqual(self.request0.state['cancellation_justification'],
                         data.get('justification'))
