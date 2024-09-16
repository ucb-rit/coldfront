from django.core import mail
from django.contrib.auth.models import User
from django_q.models import Schedule

from coldfront.config import settings
from coldfront.core.project.models import ProjectUser, ProjectUserRoleChoice, ProjectUserStatusChoice
from coldfront.core.project.utils_.renewal_utils import send_new_allocation_period_renewal_notification_email
from coldfront.core.project.utils_.renewal_utils import batch_send_new_allocation_period_renewal_notification_email
from coldfront.core.project.utils_.renewal_utils import send_all_new_allocation_period_renewal_notification_emails
from coldfront.core.utils.tests.test_base import TestBase


class TestAllowanceRenewalEmail(TestBase):
    """ A class for testing renewal email functions in 
     `coldfront.core.project.utils_.renewal_utils` """
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)

        self.manager = User.objects.create(
            email='manager@email.com',
            first_name='Manager',
            last_name='manager',
            username='manager_user')

        manager_role = ProjectUserRoleChoice.objects.get(
            name='Manager')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')

        self.project1 = self.create_active_project_with_pi('fc_one', self.user)

        ProjectUser.objects.create(
            project=self.project1,
            role=manager_role,
            status=active_project_user_status,
            user=self.manager)
        
        project2 = self.create_active_project_with_pi('fc_two', self.user)
        self.projects = [self.project1, project2]
    
    def test_send_tailored_email(self):
        """ This tests that the 
        `send_new_allocation_period_renewal_notification_email` function sends a 
        valid renewal email to PIs/Managers of a project. """
        self.assertEqual(len(mail.outbox), 0)

        send_new_allocation_period_renewal_notification_email(self.project1)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertIn('PI Computing Allowance Renewal on', email.subject)
        self.assertEqual(email.to, [self.user.email, self.manager.email])
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def test_send_batch_renewal_emails(self):
        """ This tests that the 
        `batch_send_new_allocation_period_renewal_notification_email` function 
        sends unique renewal emails to the PIs/Managers of each project passed 
        to it. """
        self.assertEqual(len(mail.outbox), 0)

        batch_send_new_allocation_period_renewal_notification_email(self.projects)

        self.assertEqual(len(mail.outbox), 2)

        email1 = mail.outbox[0]

        self.assertIn('PI Computing Allowance Renewal on', email1.subject)
        self.assertEqual(email1.to, [self.user.email, self.manager.email])
        self.assertEqual(settings.EMAIL_SENDER, email1.from_email)

        email2 = mail.outbox[1]

        self.assertIn('PI Computing Allowance Renewal on', email2.subject)
        self.assertEqual(email2.to, [self.user.email])
        self.assertEqual(settings.EMAIL_SENDER, email2.from_email)

    def test_send_mass_renewal_emails(self):
        """ This tests that the 
        `send_all_new_allocation_period_renewal_notification_emails` function 
        schedules the correct number of calls to 
        `batch_send_new_allocation_period_renewal_notification_email`. """

        func = 'coldfront.core.project.tasks.batch_send_new_allocation_period_renewal_notification_email'
        self.assertEqual(len(mail.outbox), 0)
        scheduled_tasks = Schedule.objects.filter(func=func)
        
        self.assertEqual(len(scheduled_tasks), 0)

        # TODO: Get this value from settings when it's moved to settings
        NUM_BATCHES = 2

        send_all_new_allocation_period_renewal_notification_emails()
        scheduled_tasks = Schedule.objects.filter(func=func)
        self.assertEqual(len(scheduled_tasks), NUM_BATCHES)
    