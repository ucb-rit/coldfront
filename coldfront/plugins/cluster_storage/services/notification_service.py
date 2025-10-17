import logging

from django.conf import settings

from coldfront.core.utils.email.email_strategy import validate_email_strategy_or_get_default
from coldfront.core.utils.mail import send_email_template


logger = logging.getLogger(__name__)


class StorageRequestNotificationService:
    """Handle all email notifications for storage requests."""

    @staticmethod
    def send_request_created_email(request, email_strategy=None):
        """Notify admins when a new request is created."""
        logger.info(f'Sending creation notification for request {request.id}')

        email_strategy = validate_email_strategy_or_get_default(email_strategy)

        context = {
            'request': request,
            'project': request.project,
            'requester': request.requester,
            'amount_gb': request.requested_amount_gb,
            'signature': settings.EMAIL_SIGNATURE,
        }

        email_strategy.process_email(
            send_email_template,
            subject=f'New Storage Request - {request.project.name}',
            template_name='cluster_storage/email/request_created.txt',
            context=context,
            sender=settings.EMAIL_SENDER,
            receiver_list=settings.EMAIL_ADMIN_LIST,
        )

    @staticmethod
    def send_completion_email(request, email_strategy=None):
        """Notify requester when storage is ready."""
        logger.info(f'Sending completion notification for request {request.id}')

        email_strategy = validate_email_strategy_or_get_default(email_strategy)

        context = {
            'request': request,
            'project': request.project,
            'requester': request.requester,
            'amount_gb': request.requested_amount_gb,
            'signature': settings.EMAIL_SIGNATURE,
        }

        email_strategy.process_email(
            send_email_template,
            subject=f'Storage Ready - {request.project.name}',
            template_name='cluster_storage/email/request_completed.txt',
            context=context,
            sender=settings.EMAIL_SENDER,
            receiver_list=[request.requester.email],
        )

    @staticmethod
    def send_denial_email(request, justification, email_strategy=None):
        """Notify requester when their request is denied."""
        logger.info(f'Sending denial notification for request {request.id}')

        email_strategy = validate_email_strategy_or_get_default(email_strategy)

        context = {
            'request': request,
            'project': request.project,
            'requester': request.requester,
            'amount_gb': request.requested_amount_gb,
            'justification': justification,
            'signature': settings.EMAIL_SIGNATURE,
        }

        email_strategy.process_email(
            send_email_template,
            subject=f'Storage Request Denied - {request.project.name}',
            template_name='cluster_storage/email/request_denied.txt',
            context=context,
            sender=settings.EMAIL_SENDER,
            receiver_list=[request.requester.email],
        )
