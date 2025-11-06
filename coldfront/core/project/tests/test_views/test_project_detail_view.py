from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase

from copy import deepcopy
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
import unittest

from flags.state import enable_flag
from http import HTTPStatus


# Helper to check if faculty storage allocations plugin is installed
FSA_PLUGIN_INSTALLED = 'coldfront.plugins.faculty_storage_allocations' in settings.INSTALLED_APPS


class TestProjectDetailView(TestBase):
    """A class for testing ProjectDetailView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    @staticmethod
    def project_detail_url(pk):
        """Return the URL to the detail view for the Project with the
        given primary key."""
        return reverse('project-detail', kwargs={'pk': pk})

    def test_permissions_get(self):
        """Test that the correct users have permissions to perform GET
        requests."""
        project = self.create_active_project_with_pi('ac_project', self.user)
        create_project_allocation(project, Decimal('0.00'))

        url = self.project_detail_url(project.pk)

        # Unauthenticated user.
        self.client.logout()
        response = self.client.get(url)
        self.assert_redirects_to_login(response, next_url=url)

        # Project member user.
        self.client.login(username=self.user.username, password=self.password)
        project_user = ProjectUser.objects.get(project=project, user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        project_user.delete()

        # Non-(project member) user.
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # Non-(project member) staff.
        self.user.is_staff = True
        self.user.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.user.is_staff = False
        self.user.save()

        # Non-(project member) superuser.
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.user.is_superuser = False
        self.user.save()

    def test_purchase_sus_button_invisible_for_ineligible_projects(self):
        """Test that the 'Purchase Service Units' button only appears
        for Projects that are eligible to do so."""
        computing_allowance_interface = ComputingAllowanceInterface()
        expected_num_eligible, actual_num_eligible = 1, 0
        ineligible_found = False
        for allowance in computing_allowance_interface.allowances():
            project_name_prefix = computing_allowance_interface.code_from_name(
                allowance.name)
            wrapper = ComputingAllowance(allowance)
            project = self.create_active_project_with_pi(
                f'{project_name_prefix}project', self.user)
            url = self.project_detail_url(project.pk)
            response = self.client.get(url)
            button_text = 'Purchase Service Units'
            if wrapper.is_recharge():
                self.assertContains(response, button_text)
                actual_num_eligible += 1
            else:
                self.assertNotContains(response, button_text)
                ineligible_found = True
        self.assertEqual(expected_num_eligible, actual_num_eligible)
        self.assertTrue(ineligible_found)

    def test_purchase_sus_button_invisible_for_user_roles(self):
        """Test that the 'Purchase Service Units' button only appears
        for superusers, PIs, and Managers."""
        project = self.create_active_project_with_pi('ac_project', self.user)
        create_project_allocation(project, Decimal('0.00'))

        url = self.project_detail_url(project.pk)
        button_text = 'Purchase Service Units'

        project_user = ProjectUser.objects.get(project=project, user=self.user)
        self.assertEqual(project_user.role.name, 'Principal Investigator')
        response = self.client.get(url)
        self.assertContains(response, button_text)

        project_user.role = ProjectUserRoleChoice.objects.get(name='Manager')
        project_user.save()
        response = self.client.get(url)
        self.assertContains(response, button_text)

        project_user.role = ProjectUserRoleChoice.objects.get(name='User')
        project_user.save()
        response = self.client.get(url)
        self.assertNotContains(response, button_text)

        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(url)
        self.assertContains(response, button_text)

    def test_renew_allowance_button_conditionally_enabled(self):
        """Test that the 'Renew Allowance' button is only enabled
        under certain conditions."""
        computing_allowance_interface = ComputingAllowanceInterface()
        computing_allowance = self.get_predominant_computing_allowance()
        project_name_prefix = computing_allowance_interface.code_from_name(
            computing_allowance.name)

        project = self.create_active_project_with_pi(
            f'{project_name_prefix}project', self.user)
        create_project_allocation(project, Decimal('0.00'))

        project_detail_url = self.project_detail_url(project.pk)
        # The existence of the renewal URL on the page indicates that the
        # button is enabled.
        renewal_url = reverse('project-renew', kwargs={'pk': project.pk})

        # Create a second PI on the project.
        pi_2 = User.objects.create(
            email='pi_2@email.com',
            first_name='PI',
            last_name='2',
            username='pi_2')
        ProjectUser.objects.create(
            project=project,
            role=ProjectUserRoleChoice.objects.get(
                name='Principal Investigator'),
            status=ProjectUserStatusChoice.objects.get(name='Active'),
            user=pi_2)

        # Renewals for the next allocation period cannot be requested.
        flag_name = 'ALLOCATION_RENEWAL_FOR_NEXT_PERIOD_REQUESTABLE'
        flags_copy = deepcopy(settings.FLAGS)
        flags_copy.pop(flag_name)
        with override_settings(FLAGS=flags_copy):
            # 0/2 PIs have non-denied renewal requests under the current
            # period.
            allocation_period = get_current_allowance_year_period()
            self.assertFalse(
                AllocationRenewalRequest.objects.filter(
                    allocation_period=allocation_period,
                    pi__in=[self.user, pi_2]).exists())
            response = self.client.get(project_detail_url)
            self.assertContains(response, renewal_url)

            # 1/2 PIs have non-denied renewal requests under the current
            # period.
            under_review_request_status = \
                AllocationRenewalRequestStatusChoice.objects.get(
                    name='Under Review')
            AllocationRenewalRequest.objects.create(
                requester=self.user,
                pi=self.user,
                allocation_period=allocation_period,
                status=under_review_request_status,
                pre_project=project,
                post_project=project,
                request_time=utc_now_offset_aware())
            response = self.client.get(project_detail_url)
            self.assertContains(response, renewal_url)

            denied_request_status = \
                AllocationRenewalRequestStatusChoice.objects.get(name='Denied')
            request_2 = AllocationRenewalRequest.objects.create(
                requester=self.user,
                pi=pi_2,
                allocation_period=allocation_period,
                status=denied_request_status,
                pre_project=project,
                post_project=project,
                request_time=utc_now_offset_aware())
            response = self.client.get(project_detail_url)
            self.assertContains(response, renewal_url)

            # 2/2 PIs have non-denied renewal requests under the current
            # period.
            approved_request_status = \
                AllocationRenewalRequestStatusChoice.objects.get(
                    name='Approved')
            request_2.status = approved_request_status
            request_2.save()
            response = self.client.get(project_detail_url)
            self.assertNotContains(response, renewal_url)

        # Renewals for the next allocation period can be requested.
        enable_flag(flag_name)
        response = self.client.get(project_detail_url)
        self.assertContains(response, renewal_url)

    def test_renew_allowance_button_conditionally_visible(self):
        """Test that the 'Renew Allowance' button is only visible to
        certain users for certain allocation types."""
        project = self.create_active_project_with_pi('project', self.user)
        create_project_allocation(project, Decimal('0.00'))

        url = self.project_detail_url(project.pk)
        button_text = 'Renew Allowance'

        project_user = ProjectUser.objects.get(project=project, user=self.user)

        all_roles = ProjectUserRoleChoice.objects.distinct()
        eligible_role_names = {'Manager', 'Principal Investigator'}

        computing_allowance_interface = ComputingAllowanceInterface()
        all_allowances = computing_allowance_interface.allowances()
        eligible_allowance_names, ineligible_allowance_names = set(), set()
        for allowance in all_allowances:
            wrapper = ComputingAllowance(allowance)
            if wrapper.is_renewal_supported():
                eligible_allowance_names.add(allowance.name)
            else:
                ineligible_allowance_names.add(allowance.name)
        self.assertGreater(len(eligible_allowance_names), 0)
        self.assertGreater(len(ineligible_allowance_names), 0)

        project_name_prefixes_by_allowance_name = {
            allowance.name: \
                computing_allowance_interface.code_from_name(allowance.name)
            for allowance in all_allowances}

        expected_num_successes = (
             len(eligible_role_names) * len(eligible_allowance_names))
        actual_num_successes = 0
        expected_num_failures = (
            all_roles.count() * len(all_allowances) - expected_num_successes)
        actual_num_failures = 0

        # Non-superuser, project member.
        self.assertFalse(self.user.is_superuser)
        for role in all_roles:
            project_user.role = role
            project_user.save()
            for allowance in all_allowances:
                project_name_prefix = project_name_prefixes_by_allowance_name[
                    allowance.name]
                project.name = f'{project_name_prefix}project'
                project.save()
                response = self.client.get(url)
                if (role.name in eligible_role_names and
                        allowance.name in eligible_allowance_names):
                    self.assertContains(response, button_text)
                    actual_num_successes = actual_num_successes + 1
                else:
                    self.assertNotContains(response, button_text)
                    actual_num_failures = actual_num_failures + 1
        self.assertEqual(expected_num_successes, actual_num_successes)
        self.assertEqual(expected_num_failures, actual_num_failures)
        project_user.delete()

        # Superuser, non-(project member).
        self.user.is_superuser = True
        self.user.save()
        for allowance in all_allowances:
            project_name_prefix = project_name_prefixes_by_allowance_name[
                allowance.name]
            project.name = f'{project_name_prefix}project'
            project.save()
            response = self.client.get(url)
            if allowance.name in eligible_allowance_names:
                self.assertContains(response, button_text)
            else:
                self.assertNotContains(response, button_text)
        self.user.is_superuser = False
        self.user.save()

        # Staff, non-(project member).
        self.user.is_staff = True
        self.user.save()
        for allowance in all_allowances:
            project_name_prefix = project_name_prefixes_by_allowance_name[
                allowance.name]
            project.name = f'{project_name_prefix}project'
            project.save()
            response = self.client.get(url)
            self.assertNotContains(response, button_text)
        self.user.is_staff = False
        self.user.save()

    @unittest.skipIf(not FSA_PLUGIN_INSTALLED, 'Faculty Storage Allocations plugin not installed')
    @override_settings(FLAGS={'FACULTY_STORAGE_ALLOCATIONS_ENABLED': [{'condition': 'boolean', 'value': True}]})
    def test_request_storage_link_invisible_for_ineligible_projects(self):
        """Test that the 'Request Faculty Storage Allocation' link only
        appears for Projects that are eligible to do so (FCA projects)."""
        from unittest.mock import patch

        computing_allowance_interface = ComputingAllowanceInterface()
        expected_num_eligible, actual_num_eligible = 1, 0
        ineligible_found = False

        # Mock has_eligible_pi_for_fsa_request to always return True
        with patch(
                'coldfront.plugins.faculty_storage_allocations.utils.has_eligible_pi_for_fsa_request',
                return_value=True):

            for allowance in computing_allowance_interface.allowances():
                project_name_prefix = \
                    computing_allowance_interface.code_from_name(allowance.name)
                wrapper = ComputingAllowance(allowance)
                project = self.create_active_project_with_pi(
                    f'{project_name_prefix}project', self.user)
                create_project_allocation(project, Decimal('0.00'))

                url = self.project_detail_url(project.pk)
                response = self.client.get(url)

                link_text = 'Request Faculty Storage Allocation'

                # Only FCA projects should see the link
                if allowance.name == 'Faculty Computing Allowance':
                    self.assertContains(response, link_text)
                    actual_num_eligible += 1
                else:
                    self.assertNotContains(response, link_text)
                    ineligible_found = True

            self.assertEqual(expected_num_eligible, actual_num_eligible)
            self.assertTrue(ineligible_found)

    @unittest.skipIf(not FSA_PLUGIN_INSTALLED, 'Faculty Storage Allocations plugin not installed')
    @override_settings(FLAGS={'FACULTY_STORAGE_ALLOCATIONS_ENABLED': [{'condition': 'boolean', 'value': True}]})
    def test_request_storage_link_invisible_for_user_roles(self):
        """Test that the 'Request Faculty Storage Allocation' link only
        appears for superusers, PIs, and Managers."""
        from unittest.mock import patch

        project = self.create_active_project_with_pi('fc_project', self.user)
        create_project_allocation(project, Decimal('0.00'))

        url = self.project_detail_url(project.pk)
        link_text = 'Request Faculty Storage Allocation'

        # Mock has_eligible_pi_for_fsa_request to always return True
        with patch(
                'coldfront.plugins.faculty_storage_allocations.utils.has_eligible_pi_for_fsa_request',
                return_value=True):

            project_user = ProjectUser.objects.get(
                project=project, user=self.user)
            self.assertEqual(project_user.role.name, 'Principal Investigator')
            response = self.client.get(url)
            self.assertContains(response, link_text)

            project_user.role = ProjectUserRoleChoice.objects.get(name='Manager')
            project_user.save()
            response = self.client.get(url)
            self.assertContains(response, link_text)

            project_user.role = ProjectUserRoleChoice.objects.get(name='User')
            project_user.save()
            response = self.client.get(url)
            self.assertNotContains(response, link_text)

            # Superuser can see it even with 'User' role
            self.user.is_superuser = True
            self.user.save()
            response = self.client.get(url)
            self.assertContains(response, link_text)

    @unittest.skipIf(not FSA_PLUGIN_INSTALLED, 'Faculty Storage Allocations plugin not installed')
    @override_settings(FLAGS={'FACULTY_STORAGE_ALLOCATIONS_ENABLED': [{'condition': 'boolean', 'value': False}]})
    def test_request_storage_link_invisible_when_flag_disabled(self):
        """Test that the 'Request Faculty Storage Allocation' link is
        not visible when the FACULTY_STORAGE_ALLOCATIONS_ENABLED flag is disabled."""
        # Create an FCA project (eligible)
        project = self.create_active_project_with_pi('fc_project', self.user)
        create_project_allocation(project, Decimal('0.00'))

        url = self.project_detail_url(project.pk)
        link_text = 'Request Faculty Storage Allocation'

        # PI should not see the link when flag is disabled
        project_user = ProjectUser.objects.get(project=project, user=self.user)
        self.assertEqual(project_user.role.name, 'Principal Investigator')
        response = self.client.get(url)
        self.assertNotContains(response, link_text)

        # Even superuser should not see it when flag is disabled
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(url)
        self.assertNotContains(response, link_text)

    @unittest.skipIf(not FSA_PLUGIN_INSTALLED, 'Faculty Storage Allocations plugin not installed')
    @override_settings(
        FLAGS={'FACULTY_STORAGE_ALLOCATIONS_ENABLED': [{'condition': 'boolean', 'value': True}]},
        FACULTY_STORAGE_ALLOCATIONS_ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED=False
    )
    def test_request_storage_link_visible_when_pi_eligible_whitelist_disabled(self):
        """Test that the 'Request Faculty Storage Allocation' link is
        visible when PI is eligible and whitelist is disabled."""
        from unittest.mock import patch

        # Create an FCA project (eligible)
        project = self.create_active_project_with_pi('fc_project', self.user)
        create_project_allocation(project, Decimal('0.00'))

        url = self.project_detail_url(project.pk)
        link_text = 'Request Faculty Storage Allocation'

        # Mock the settings module that the eligibility service imports
        with patch('coldfront.plugins.faculty_storage_allocations.conf.settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED', False):

            # PI should see the link (whitelist disabled, no existing requests)
            response = self.client.get(url)
            self.assertContains(response, link_text)

    @unittest.skipIf(not FSA_PLUGIN_INSTALLED, 'Faculty Storage Allocations plugin not installed')
    @override_settings(
        FLAGS={'FACULTY_STORAGE_ALLOCATIONS_ENABLED': [{'condition': 'boolean', 'value': True}]},
        FACULTY_STORAGE_ALLOCATIONS_ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED=True,
        FACULTY_STORAGE_ALLOCATIONS_ELIGIBLE_PI_EMAIL_WHITELIST=[]
    )
    def test_request_storage_link_invisible_when_pi_not_on_whitelist(self):
        """Test that the 'Request Faculty Storage Allocation' link is
        not visible when PI is not on the whitelist."""
        from unittest.mock import patch, PropertyMock
        from allauth.account.models import EmailAddress

        # Create an FCA project (eligible)
        project = self.create_active_project_with_pi('fc_project', self.user)
        create_project_allocation(project, Decimal('0.00'))

        # Create email for the PI
        EmailAddress.objects.create(
            user=self.user,
            email='pi@example.com',
            verified=True,
            primary=True
        )

        url = self.project_detail_url(project.pk)
        link_text = 'Request Faculty Storage Allocation'

        # Mock the settings module that the eligibility service imports
        with patch('coldfront.plugins.faculty_storage_allocations.conf.settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED', True), \
             patch('coldfront.plugins.faculty_storage_allocations.conf.settings.ELIGIBLE_PI_EMAIL_WHITELIST', ['other@berkeley.edu']):

            # PI should NOT see the link (not on whitelist)
            response = self.client.get(url)
            self.assertNotContains(response, link_text)

    @unittest.skipIf(not FSA_PLUGIN_INSTALLED, 'Faculty Storage Allocations plugin not installed')
    @override_settings(
        FLAGS={'FACULTY_STORAGE_ALLOCATIONS_ENABLED': [{'condition': 'boolean', 'value': True}]},
        FACULTY_STORAGE_ALLOCATIONS_ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED=True,
        FACULTY_STORAGE_ALLOCATIONS_ELIGIBLE_PI_EMAIL_WHITELIST=['pi@example.com']
    )
    def test_request_storage_link_visible_when_pi_on_whitelist(self):
        """Test that the 'Request Faculty Storage Allocation' link is
        visible when PI is on the whitelist."""
        from unittest.mock import patch
        from allauth.account.models import EmailAddress

        # Create an FCA project (eligible)
        project = self.create_active_project_with_pi('fc_project', self.user)
        create_project_allocation(project, Decimal('0.00'))

        # Create email for the PI that's on the whitelist
        EmailAddress.objects.create(
            user=self.user,
            email='pi@example.com',
            verified=True,
            primary=True
        )

        url = self.project_detail_url(project.pk)
        link_text = 'Request Faculty Storage Allocation'

        # Mock the settings module that the eligibility service imports
        with patch('coldfront.plugins.faculty_storage_allocations.conf.settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED', True), \
             patch('coldfront.plugins.faculty_storage_allocations.conf.settings.ELIGIBLE_PI_EMAIL_WHITELIST', ['pi@example.com']):

            # PI should see the link (on whitelist, no existing requests)
            response = self.client.get(url)
            self.assertContains(response, link_text)

    @unittest.skipIf(not FSA_PLUGIN_INSTALLED, 'Faculty Storage Allocations plugin not installed')
    @override_settings(
        FLAGS={'FACULTY_STORAGE_ALLOCATIONS_ENABLED': [{'condition': 'boolean', 'value': True}]},
        FACULTY_STORAGE_ALLOCATIONS_ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED=False
    )
    def test_request_storage_link_invisible_when_pi_has_existing_request(self):
        """Test that the 'Request Faculty Storage Allocation' link is
        not visible when PI has an existing non-denied FSA request."""
        from unittest.mock import patch
        from coldfront.plugins.faculty_storage_allocations.models import (
            FacultyStorageAllocationRequest,
            FacultyStorageAllocationRequestStatusChoice,
            faculty_storage_allocation_request_state_schema,
        )

        # Create an FCA project (eligible)
        project = self.create_active_project_with_pi('fc_project', self.user)
        create_project_allocation(project, Decimal('0.00'))

        # Create an existing FSA request for this PI
        status, _ = FacultyStorageAllocationRequestStatusChoice.objects.get_or_create(
            name='Under Review'
        )
        FacultyStorageAllocationRequest.objects.create(
            status=status,
            project=project,
            requester=self.user,
            pi=self.user,
            requested_amount_gb=1000,
            state=faculty_storage_allocation_request_state_schema(),
        )

        url = self.project_detail_url(project.pk)
        link_text = 'Request Faculty Storage Allocation'

        # Mock the settings module that the eligibility service imports
        with patch('coldfront.plugins.faculty_storage_allocations.conf.settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED', False):

            # PI should NOT see the link (has existing request)
            response = self.client.get(url)
            self.assertNotContains(response, link_text)

    @unittest.skipIf(not FSA_PLUGIN_INSTALLED, 'Faculty Storage Allocations plugin not installed')
    @override_settings(
        FLAGS={'FACULTY_STORAGE_ALLOCATIONS_ENABLED': [{'condition': 'boolean', 'value': True}]},
        FACULTY_STORAGE_ALLOCATIONS_ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED=False
    )
    def test_request_storage_link_visible_when_different_pi_is_eligible(self):
        """Test that the 'Request Faculty Storage Allocation' link is
        visible when at least one PI on the project is eligible."""
        from unittest.mock import patch
        from coldfront.plugins.faculty_storage_allocations.models import (
            FacultyStorageAllocationRequest,
            FacultyStorageAllocationRequestStatusChoice,
            faculty_storage_allocation_request_state_schema,
        )

        # Create an FCA project with the main PI
        project = self.create_active_project_with_pi('fc_project', self.user)
        create_project_allocation(project, Decimal('0.00'))

        # Create a second PI who has an existing request (not eligible)
        pi_2 = User.objects.create(
            email='pi_2@example.com',
            first_name='PI',
            last_name='Two',
            username='pi_2'
        )
        ProjectUser.objects.create(
            project=project,
            role=ProjectUserRoleChoice.objects.get(name='Principal Investigator'),
            status=ProjectUserStatusChoice.objects.get(name='Active'),
            user=pi_2
        )

        # Create existing FSA request for pi_2 (making them ineligible)
        status, _ = FacultyStorageAllocationRequestStatusChoice.objects.get_or_create(
            name='Under Review'
        )
        FacultyStorageAllocationRequest.objects.create(
            status=status,
            project=project,
            requester=pi_2,
            pi=pi_2,
            requested_amount_gb=1000,
            state=faculty_storage_allocation_request_state_schema(),
        )

        url = self.project_detail_url(project.pk)
        link_text = 'Request Faculty Storage Allocation'

        # Mock the settings module that the eligibility service imports
        with patch('coldfront.plugins.faculty_storage_allocations.conf.settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED', False):

            # Link should STILL be visible because self.user (first PI) is eligible
            response = self.client.get(url)
            self.assertContains(response, link_text)

    # TODO
