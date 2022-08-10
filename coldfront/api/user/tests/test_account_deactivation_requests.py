from datetime import timedelta

from django.contrib.auth.models import User

from coldfront.api.user.tests.test_user_base import TestUserBase
from coldfront.api.user.tests.utils import \
    assert_account_deactivation_request_serialization
from coldfront.core.allocation.models import \
    ClusterAccountDeactivationRequestStatusChoice, \
    ClusterAccountDeactivationRequest, \
    ClusterAccountDeactivationRequestReasonChoice

from http import HTTPStatus

from coldfront.core.utils.common import utc_now_offset_aware, \
    import_from_settings

"""A test suite for the /account_deactivation_requests/ endpoints, divided
by method."""

SERIALIZER_FIELDS = ('id', 'user', 'status', 'reason', 'justification')

BASE_URL = '/api/account_deactivation_requests/'


class TestClusterAccountDeactivationRequestsBase(TestUserBase):
    """A base class for tests of the /account_deactivation_requests/
    endpoints."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create 4 ClusterAccountDeactivationRequests with statuses Ready
        # and Processing and reasons NO_VALID_USER_ACCOUNT_FEE_BILLING_ID and
        # NO_VALID_RECHARGE_USAGE_FEE_BILLING_ID
        ready_status = \
            ClusterAccountDeactivationRequestStatusChoice.objects.get(
                name='Ready')
        processing_status = \
            ClusterAccountDeactivationRequestStatusChoice.objects.get(
                name='Processing')
        no_valid_account = \
            ClusterAccountDeactivationRequestReasonChoice.objects.get(
                name='NO_VALID_USER_ACCOUNT_FEE_BILLING_ID')
        no_valid_recharge = \
            ClusterAccountDeactivationRequestReasonChoice.objects.get(
                name='NO_VALID_RECHARGE_USAGE_FEE_BILLING_ID')

        self.request_dict = {
            'request0': {'user': self.user0,
                         'status': ready_status,
                         'reason': [no_valid_account]},
            'request1': {'user': self.user1,
                         'status': processing_status,
                         'reason': [no_valid_recharge]},
            'request2': {'user': self.user2,
                         'status': ready_status,
                         'reason': [no_valid_recharge, no_valid_account]},
            'request3': {'user': self.user3,
                         'status': processing_status,
                         'reason': [no_valid_account, no_valid_recharge]},
        }

        for name, kwargs in self.request_dict.items():
            reasons = kwargs.pop('reason')
            request = ClusterAccountDeactivationRequest.objects.create(**kwargs)
            request.reason.add(*reasons)
            request.save()
            kwargs['reason'] = reasons
            setattr(self, name, request)

        # Run the client as the superuser.
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.superuser_token.key}')

        self.expiration_offset = \
            import_from_settings('ACCOUNT_DEACTIVATION_QUEUE_DAYS')


class TestListClusterAccountDeactivationRequests(
    TestClusterAccountDeactivationRequestsBase):
    """A class for testing GET /account_deactivation_requests/."""

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = BASE_URL
        method = 'GET'
        self.assert_authorization_token_required(url, method)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = BASE_URL
        method = 'GET'
        users = [
            (self.user0, False),
            (self.staff_user, True),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)

    def test_result_order(self):
        """Test that the results are sorted by ID in ascending order."""
        url = BASE_URL
        self.assert_result_order(url, 'id', ascending=True)

    def test_no_filters(self):
        """Test that all results are returned when no query filters are
        provided."""
        url = BASE_URL
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(json['count'],
                         ClusterAccountDeactivationRequest.objects.count())
        self.assertIsNone(json['next'])
        self.assertIsNone(json['previous'])
        for result in json['results']:
            account_deactivation_request = \
                ClusterAccountDeactivationRequest.objects.get(pk=result['id'])
            assert_account_deactivation_request_serialization(
                account_deactivation_request,
                result,
                SERIALIZER_FIELDS)

    def test_status_filter(self):
        """Test that querying by status filters results properly."""
        url = BASE_URL
        self.assertEqual(ClusterAccountDeactivationRequest.objects.count(), 4)
        for status in ('Ready', 'Processing'):
            query_parameters = {
                'status': status,
            }
            response = self.client.get(url, query_parameters)
            json = response.json()
            self.assertEqual(json['count'], 2)
            for result in json['results']:
                self.assertEqual(result['status'], status)

    def test_reason_filter(self):
        """Test that querying by reason filters results properly."""
        url = BASE_URL
        self.assertEqual(ClusterAccountDeactivationRequest.objects.count(), 4)
        for reason in ('NO_VALID_USER_ACCOUNT_FEE_BILLING_ID',
                       'NO_VALID_RECHARGE_USAGE_FEE_BILLING_ID'):
            query_parameters = {
                'reason': reason,
            }
            response = self.client.get(url, query_parameters)
            json = response.json()
            self.assertEqual(json['count'], 3)
            for result in json['results']:
                reasons = result['reason'].split(',')
                self.assertIn(reason, reasons)


class TestRetrieveClusterAccountDeactivationRequests(
    TestClusterAccountDeactivationRequestsBase):
    """A class for testing GET /account_deactivation_requests/
    {account_deactivation_request_id}/."""

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.pk_url(BASE_URL, '1')
        method = 'GET'
        self.assert_authorization_token_required(url, method)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.pk_url(BASE_URL, '1')
        method = 'GET'
        users = [
            (self.user0, False),
            (self.staff_user, True),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)

    def test_response_format(self):
        """Test that the response is in the expected format."""
        url = self.pk_url(BASE_URL, self.request0.pk)
        self.assert_retrieve_result_format(url, SERIALIZER_FIELDS)

    def test_valid_pk(self):
        """Test that the response for a valid primary key contains the
        correct values."""
        url = self.pk_url(BASE_URL, self.request0.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        assert_account_deactivation_request_serialization(
            self.request0, json, SERIALIZER_FIELDS)

    def test_invalid_pk(self):
        """Test that the response for a nonexistent or unassociated
        primary key raises an error."""
        pk = self.generate_invalid_pk(ClusterAccountDeactivationRequest)
        url = self.pk_url(BASE_URL, pk)
        self.assert_retrieve_invalid_response_format(url)


class TestUpdatePatchClusterAccountDeactivationRequests(
    TestClusterAccountDeactivationRequestsBase):
    """A class for testing PATCH /account_deactivation_requests/
    {account_deactivation_request_id}/."""

    def _refresh_objects(self):
        """Refresh relevant objects from db."""
        for request_name in self.request_dict.keys():
            request = getattr(self, request_name)
            request.refresh_from_db()

    def _assert_reason_equal(self, request, actual):
        reasons = request.reason.all().values_list('name', flat=True)
        for reason in actual:
            self.assertIn(reason.name, reasons)

    def _assert_pre_state(self):
        """Assert that the relevant objects have the expected state."""
        self._refresh_objects()
        for name, kwargs in self.request_dict.items():
            request = getattr(self, name)
            self.assertEqual(request.status, kwargs['status'])
            self.assertEqual(request.user, kwargs['user'])
            self._assert_reason_equal(request, kwargs['reason'])

    def _assert_post_state(self, request_name, status, justification=None):
        """Assert that the relevant objects have the expected state."""
        self._refresh_objects()
        for name, kwargs in self.request_dict.items():
            request = getattr(self, name)

            # User and Reason should not change.
            self.assertEqual(request.user, kwargs['user'])
            self._assert_reason_equal(request, kwargs['reason'])

            # Status and justification should only change for the
            # specified request.
            if name == request_name:
                self.assertEqual(request.status.name, status)
                if justification:
                    self.assertEqual(request.state['justification'],
                                     justification)
            else:
                self.assertEqual(request.status, kwargs['status'])

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.pk_url(BASE_URL, '1')
        method = 'PATCH'
        self.assert_authorization_token_required(url, method)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.pk_url(BASE_URL, '1')
        method = 'PATCH'
        users = [
            (self.user0, False),
            (self.staff_user, False),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)

    def test_read_only_fields_ignored(self):
        """Test that requests that attempt to update read-only fields do
        not update those fields."""
        self._assert_pre_state()

        url = self.pk_url(BASE_URL, self.request0.pk)
        data = {
            'id': self.request0.pk + 1,
            'status': 'Processing',
            'reason': 'NO_VALID_RECHARGE_USAGE_FEE_BILLING_ID',
            'user': 'user2',
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()

        self._assert_post_state('request0', data.get('status'))

        assert_account_deactivation_request_serialization(
            self.request0, json, SERIALIZER_FIELDS)

    def test_valid_data_processing(self):
        """Test that updating an object with valid PATCH data
        succeeds when the new status is Processing."""
        self._assert_pre_state()

        url = self.pk_url(BASE_URL, self.request0.pk)
        data = {
            'status': 'Processing',
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()

        self._assert_post_state('request0', data.get('status'))
        assert_account_deactivation_request_serialization(
            self.request0, json, SERIALIZER_FIELDS)

    def test_valid_data_cancelled(self):
        """Test that updating an object with valid PATCH data
        succeeds when the new status is Processing."""
        self._assert_pre_state()

        url = self.pk_url(BASE_URL, self.request0.pk)
        data = {
            'status': 'Cancelled',
            'justification': 'This is a test justification.'
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()

        self._assert_post_state('request0',
                                data.get('status'),
                                data.get('justification'))

        assert_account_deactivation_request_serialization(
            self.request0, json, SERIALIZER_FIELDS)

    def test_invalid_data(self):
        """Test that updating an object with invalid PATCH data
        fails."""
        self._assert_pre_state()

        url = self.pk_url(BASE_URL, self.request0.pk)
        data = {
            'status': 'Invalid',
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()

        self.assertIn('status', json)
        self.assertEqual(
            json['status'], ['Object with name=Invalid does not exist.'])

        self._assert_pre_state()


class TestDestroyClusterAccountDeactivations(
    TestClusterAccountDeactivationRequestsBase):
    """A class for testing DELETE /account_deactivation_requests/
    {account_deactivation_request_id}/."""

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.pk_url(BASE_URL, '1')
        method = 'DELETE'
        self.assert_authorization_token_required(url, method)

    def test_method_not_allowed(self):
        """Test that this method is not allowed."""
        url = self.pk_url(BASE_URL, '1')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.pk_url(BASE_URL, '1')
        method = 'DELETE'
        users = [
            (self.user0, False),
            (self.staff_user, False),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)


class TestUpdatePutClusterAccountDeactivations(
    TestClusterAccountDeactivationRequestsBase):
    """A class for testing PUT /account_deactivation_requests/
    {account_deactivation_request_id}/."""

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.pk_url(BASE_URL, '1')
        method = 'PUT'
        self.assert_authorization_token_required(url, method)

    def test_method_not_allowed(self):
        """Test that this method is not allowed."""
        url = self.pk_url(BASE_URL, '1')
        response = self.client.put(url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.pk_url(BASE_URL, '1')
        method = 'PUT'
        users = [
            (self.user0, False),
            (self.staff_user, False),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)


class TestCreateClusterAccountDeactivations(
    TestClusterAccountDeactivationRequestsBase):
    """A class for testing POST /account_deactivation_requests/."""

    def _assert_pre_state(self, user, status, reason):
        reasons = reason.split(',')
        query = ClusterAccountDeactivationRequest.objects.filter(
            user__username=user,
            status__name=status,
            reason__name__in=reasons
        )
        self.assertFalse(query.exists())

    def _assert_post_state(self, user, status, reason, pre_time, post_time):
        query = ClusterAccountDeactivationRequest.objects.filter(
            user__username=user,
            status__name=status,
        )
        self.assertEqual(query.count(), 1)
        self.assertTrue(pre_time <= query.first().expiration <= post_time)

        reasons = reason.split(',')
        for reason in query.first().reason.all():
            self.assertIn(reason.name, reasons)

    def _get_request(self, user, status, reason):
        reasons = reason.split(',')
        query = ClusterAccountDeactivationRequest.objects.filter(
            user__username=user,
            status__name=status,
            reason__name__in=reasons
        )

        self.assertEqual(query.count(), 1)

        return query.first()

    def _get_offset_time(self):
        return utc_now_offset_aware() + timedelta(days=self.expiration_offset)

    def setUp(self):
        super().setUp()
        # Create a new user.
        self.user5 = User.objects.create(username='user5')

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = BASE_URL
        method = 'POST'
        self.assert_authorization_token_required(url, method)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = BASE_URL
        method = 'POST'
        users = [
            (self.user0, False),
            (self.staff_user, False),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)

    def test_valid_data_queued(self):
        """Test that creating an object with valid POST data
        succeeds when the new status is Queued."""
        pre_time = self._get_offset_time()
        url = BASE_URL
        data = {
            'user': 'user5',
            'status': 'Queued',
            'reason': 'NO_VALID_USER_ACCOUNT_FEE_BILLING_ID'
        }
        self._assert_pre_state(**data)
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        json = response.json()

        post_time = self._get_offset_time()
        self._assert_post_state(**data, pre_time=pre_time, post_time=post_time)
        assert_account_deactivation_request_serialization(
            self._get_request(**data), json, SERIALIZER_FIELDS)

    def test_invalid__user_data(self):
        """Test that creating an object with invalid POST data
        does not succeed."""
        url = BASE_URL
        data = {
            'user': 'Invalid',
            'status': 'Queued',
            'reason': 'NO_VALID_USER_ACCOUNT_FEE_BILLING_ID'
        }
        self._assert_pre_state(**data)
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()

        self.assertEqual(json['user'],
                         ['Object with username=Invalid does not exist.'])
        self._assert_pre_state(**data)

    def test_invalid_data_reason(self):
        """Test that creating an object with invalid POST data
        does not succeed."""
        url = BASE_URL
        data = {
            'user': 'user5',
            'status': 'Queued',
            'reason': 'Invalid'
        }
        self._assert_pre_state(**data)
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()

        self.assertEqual(json['non_field_errors'],
                         ['Invalid reason "Invalid" given.'])
        self._assert_pre_state(**data)

    def test_invalid_data_status(self):
        """Test that creating an object with invalid POST data
        does not succeed."""
        url = BASE_URL
        data = {
            'user': 'user5',
            'status': 'Processing',
            'reason': 'NO_VALID_USER_ACCOUNT_FEE_BILLING_ID'
        }
        self._assert_pre_state(**data)
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()

        self.assertEqual(json['error'],
                         'POST requests only allow requests to be '
                         'created with a "Queued" status.')
        self._assert_pre_state(**data)

    def test_request_exists(self):
        """Test that creating an object with valid POST data
        does not succeed if the object already exists."""
        pre_time = self._get_offset_time()
        url = BASE_URL
        data = {
            'user': 'user5',
            'status': 'Queued',
            'reason': 'NO_VALID_USER_ACCOUNT_FEE_BILLING_ID'
        }
        self._assert_pre_state(**data)
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        post_time = self._get_offset_time()
        self._assert_post_state(**data, pre_time=pre_time, post_time=post_time)

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()

        self.assertEqual(json['error'],
                         'ClusterAccountDeactivationRequest with '
                         'given args already exists.')
        self._assert_post_state(**data, pre_time=pre_time, post_time=post_time)
