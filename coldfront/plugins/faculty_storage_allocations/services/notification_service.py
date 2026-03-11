from urllib.parse import urljoin

from django.conf import settings as django_settings
from django.urls import reverse

from coldfront.core.utils.email.email_strategy import validate_email_strategy_or_get_default
from coldfront.core.utils.mail import send_email_template

from coldfront.plugins.faculty_storage_allocations.conf import settings


class FSARequestNotificationService:
    """Handle all email notifications for FSA requests."""

    @staticmethod
    def send_request_created_email_to_admins(request, email_strategy=None):
        """Notify admins when a new request is created."""
        email_strategy = validate_email_strategy_or_get_default(email_strategy)

        subject = (
            f'New Faculty Storage Allocation Request - {request.project.name}')
        template_name = 'faculty_storage_allocations/email/request_created.txt'
        context = {
            'project': request.project,
            'requester': request.requester,
            'pi': request.pi,
            'amount_tb': request.requested_amount_gb // 1000,
            'review_url': urljoin(
                django_settings.CENTER_BASE_URL,
                reverse('faculty-storage-allocation-request-detail', kwargs={'pk': request.pk})
            ),
        }
        sender = django_settings.EMAIL_SENDER
        receiver_list = _get_admin_notification_recipients('request_created')

        email_args = (subject, template_name, context, sender, receiver_list)
        email_strategy.process_email(send_email_template, *email_args)

    @staticmethod
    def send_request_approved_email_to_admins(request, email_strategy=None):
        """Notify admins when a request is approved."""
        email_strategy = validate_email_strategy_or_get_default(email_strategy)

        subject = (
            f'Faculty Storage Allocation Request Approved - '
            f'{request.project.name}')
        template_name = 'faculty_storage_allocations/email/request_approved.txt'
        context = {
            'project': request.project,
            'amount_tb': request.approved_amount_gb // 1000,
            'review_url': urljoin(
                django_settings.CENTER_BASE_URL,
                reverse('faculty-storage-allocation-request-detail', kwargs={'pk': request.pk})
            ),
        }
        sender = django_settings.EMAIL_SENDER
        receiver_list = _get_admin_notification_recipients('request_approved')

        email_args = (subject, template_name, context, sender, receiver_list)
        email_strategy.process_email(send_email_template, *email_args)

    @staticmethod
    def send_completion_email_to_users(request, email_strategy=None):
        """Notify the PI and requester when the request is completed."""
        email_strategy = validate_email_strategy_or_get_default(email_strategy)

        subject = (
            f'Faculty Storage Allocation Request Complete - '
            f'{request.project.name}')
        template_name = 'faculty_storage_allocations/email/request_completed.txt'
        context = {
            'center_name': django_settings.CENTER_NAME,
            'project': request.project,
            'amount_tb': request.approved_amount_gb // 1000,
            'project_url': urljoin(
                django_settings.CENTER_BASE_URL,
                reverse('project-detail', kwargs={'pk': request.project.pk})
            ),
            'support_email': django_settings.CENTER_HELP_EMAIL,
            'signature': django_settings.EMAIL_SIGNATURE,
        }
        sender = django_settings.EMAIL_SENDER
        receiver_list = list(set([request.requester.email, request.pi.email]))

        email_args = (subject, template_name, context, sender, receiver_list)
        email_strategy.process_email(send_email_template, *email_args)

    @staticmethod
    def send_denial_email_to_users(request, email_strategy=None):
        """Notify the PI and requester when their request is denied."""
        email_strategy = validate_email_strategy_or_get_default(email_strategy)

        reason = request.denial_reason()

        subject = (
            f'Faculty Storage Allocation Request Denied - '
            f'{request.project.name}')
        template_name = 'faculty_storage_allocations/email/request_denied.txt'
        context = {
            'center_name': django_settings.CENTER_NAME,
            'project': request.project,
            'amount_tb': request.requested_amount_gb // 1000,
            'reason_category': reason.category,
            'reason_justification': reason.justification,
            'support_email': django_settings.CENTER_HELP_EMAIL,
            'signature': django_settings.EMAIL_SIGNATURE,
        }
        sender = django_settings.EMAIL_SENDER
        receiver_list = list(set([request.requester.email, request.pi.email]))

        email_args = (subject, template_name, context, sender, receiver_list)
        email_strategy.process_email(send_email_template, *email_args)


def _get_admin_notification_recipients(event_type):
    """Return the list of administrator email addresses to notify
    for the given event type. Return the empty list if the event is
    not "registered"."""
    return settings.EMAIL_ADMIN_NOTIFICATION_RECIPIENTS.get(event_type, [])
