from io import StringIO

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command

from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.tests.test_base import TestBase


class TestSUBase(TestBase):
    """Base class for testing the management commands that alter project SUs"""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create a PI.
        self.pi = User.objects.create(
            username='pi0', email='pi0@nonexistent.com')
        user_profile = UserProfile.objects.get(user=self.pi)
        user_profile.is_pi = True
        user_profile.save()

        # Create two Users.
        for i in range(2):
            user = User.objects.create(
                username=f'user{i}', email=f'user{i}@nonexistent.com')
            user_profile = UserProfile.objects.get(user=user)
            user_profile.cluster_uid = f'{i}'
            user_profile.save()
            setattr(self, f'user{i}', user)
            setattr(self, f'user_profile{i}', user_profile)

        # Clear the mail outbox.
        mail.outbox = []

    @staticmethod
    def call_command(*args):
        """
        Call the command with the given arguments, returning the messages
        written to stdout and stderr.
        """
        out, err = StringIO(), StringIO()
        kwargs = {'stdout': out, 'stderr': err}
        call_command(*args, **kwargs)
        return out.getvalue(), err.getvalue()

    @staticmethod
    def get_accounting_allocation_objects(project, user=None):
        """Call get_accounting_allocation_objects, without the check
        that the Allocation must be Active. Return its output."""
        return get_accounting_allocation_objects(
            project, user=user, enforce_allocation_active=False)

    def record_historical_objects_len(self, project):
        """
        Records the lengths of all relevant historical objects to a dict
        """
        length_dict = {}
        allocation_objects = self.get_accounting_allocation_objects(project)
        historical_allocation_attribute = \
            allocation_objects.allocation_attribute.history.all()

        length_dict['historical_allocation_attribute'] = \
            len(historical_allocation_attribute)

        for project_user in project.projectuser_set.all():
            if project_user.role.name != 'User':
                continue

            allocation_user_obj = self.get_accounting_allocation_objects(
                project, user=project_user.user)

            historical_allocation_user_attribute = \
                allocation_user_obj.allocation_user_attribute.history.all()

            key = 'historical_allocation_user_attribute_' + project_user.user.username
            length_dict[key] = len(historical_allocation_user_attribute)

        return length_dict

    def allocation_values_test(self, project, value, user_value):
        """
        Tests that the allocation user values are correct
        """
        allocation_objects = self.get_accounting_allocation_objects(project)
        self.assertEqual(allocation_objects.allocation_attribute.value, value)

        for project_user in project.projectuser_set.all():
            if project_user.role.name != 'User':
                continue
            allocation_objects = self.get_accounting_allocation_objects(
                project, user=project_user.user)

            self.assertEqual(allocation_objects.allocation_user_attribute.value,
                             user_value)

    def transactions_created(self, project, pre_time, post_time, amount):
        """
        Tests that transactions were created for the zeroing of SUs
        """
        proj_transaction = ProjectTransaction.objects.get(project=project,
                                                          allocation=amount)

        self.assertTrue(pre_time <= proj_transaction.date_time <= post_time)

        for project_user in project.projectuser_set.all():
            if project_user.role.name != 'User':
                continue

            proj_user_transaction = ProjectUserTransaction.objects.get(
                project_user=project_user,
                allocation=amount)

            self.assertTrue(pre_time <= proj_user_transaction.date_time <= post_time)

    def historical_objects_created(self, pre_length_dict, post_length_dict):
        """
        Test that historical objects were created
        """
        for k, v in pre_length_dict.items():
            self.assertEqual(v + 1, post_length_dict[k])

    def historical_objects_updated(self, project, reason):
        """
        Tests that the relevant historical objects have the correct reason
        """
        allocation_objects = self.get_accounting_allocation_objects(project)

        alloc_attr_hist_reason = \
            allocation_objects.allocation_attribute.history. \
                latest('id').history_change_reason
        self.assertEqual(alloc_attr_hist_reason, reason)

        for project_user in project.projectuser_set.all():
            if project_user.role.name != 'User':
                continue

            allocation_user_obj = self.get_accounting_allocation_objects(
                project, user=project_user.user)

            alloc_attr_hist_reason = \
                allocation_user_obj.allocation_user_attribute.history.latest(
                    'id').history_change_reason
            self.assertEqual(alloc_attr_hist_reason, reason)
