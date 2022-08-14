from django.db.models.signals import post_save

from coldfront.core.allocation.models import AllocationRenewalRequest, \
    AccountDeletionRequest, AccountDeletionRequestStatusChoice
from coldfront.core.allocation.utils_.account_deletion_utils import \
    AccountDeletionRequestRunner
from coldfront.core.project.models import SavioProjectAllocationRequest, \
    ProjectUserRemovalRequest, ProjectUser, ProjectUserJoinRequest
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalDenialRunner
from django.dispatch import receiver
from django.dispatch import Signal
import logging

from coldfront.core.utils.common import utc_now_offset_aware

logger = logging.getLogger(__name__)


# A signal to send when a SavioProjectAllocationRequest is denied.
new_project_request_denied = Signal()


@receiver(new_project_request_denied)
def deny_associated_allocation_renewal_request(sender, **kwargs):
    """When a SavioProjectAllocationRequest is denied, if it is
    referenced by an AllocationRenewalRequest, also deny that
    request.

    Parameters:
        - sender: None
        - **kwargs
            - request_id (int): The ID of the denied request
    """
    request_id = kwargs['request_id']
    try:
        new_project_request_obj = SavioProjectAllocationRequest.objects.get(
            id=request_id)
    except SavioProjectAllocationRequest.DoesNotExist:
        message = f'Invalid SavioProjectAllocationRequest ID {request_id}.'
        logger.error(message)
        return

    try:
        renewal_request_obj = AllocationRenewalRequest.objects.get(
            new_project_request=new_project_request_obj)
    except AllocationRenewalRequest.DoesNotExist:
        return
    except AllocationRenewalRequest.MultipleObjectsReturned:
        message = (
            f'Unexpectedly found multiple AllocationRenewalRequests that '
            f'reference SavioProjectAllocationRequest {request_id}.')
        logger.error(message)
        return

    # Set the reason for the renewal request to be that of the new project
    # request.
    reason = new_project_request_obj.denial_reason()
    renewal_request_obj.state['other'] = {
        'justification': reason.justification,
        'timestamp': reason.timestamp,
    }
    renewal_request_obj.save()

    try:
        runner = AllocationRenewalDenialRunner(renewal_request_obj)
        runner.run()
    except Exception as e:
        message = (
            f'Encountered unexpected exception when automatically denying '
            f'AllocationRenewalRequest {renewal_request_obj.pk} after '
            f'SavioProjectAllocationRequest {request_id} was denied. '
            f'Details:')
        logger.error(message)
        logger.exception(e)
        return

    message = (
        f'Automatically denied AllocationRenewalRequest '
        f'{renewal_request_obj.pk} after SavioProjectAllocationRequest '
        f'{request_id} was denied.')
    logger.info(message)


@receiver(post_save, sender=ProjectUserRemovalRequest)
def proj_removal_request_account_deletion(sender, instance, created, *args, **kwargs):
    proj_users = ProjectUser.objects.filter(
        user=instance.user,
        status='Active').exists()

    # The request was set to complete and the user has no other projects.
    if instance.status.name == 'Complete' and not proj_users:
        runner = AccountDeletionRequestRunner(instance.user,
                                              instance.user, # TODO: who do we pass here?
                                              'System')
        runner.run()
        for message in runner.get_warning_messages():
            logger.warning(message)


@receiver(post_save, sender=ProjectUser)
def proj_user_account_deletion_cancel(sender, instance, created, *args, **kwargs):
    if created:
        account_deletion = AccountDeletionRequest.objects.filter(
            user=instance.user,
            status__name__in=['Queued', 'Ready'],
            requester__name='System'
        )

        if account_deletion.exists():
            account_deletion = account_deletion.first()
            account_deletion.status = \
                AccountDeletionRequestStatusChoice.objects.get(name='Cancelled')
            account_deletion.state['other'] = {
                'justification': f'User joined project {instance.project.name}.',
                'timestamp': utc_now_offset_aware().isoformat()}
            account_deletion.save()

            message = f'Set AccountDeletionRequest {account_deletion} to ' \
                      f'\"Cancelled.\" User {instance.user} joined project ' \
                      f'{instance.project.name}'
            logger.info(message)


@receiver(post_save, sender=ProjectUserJoinRequest)
def proj_user_account_deletion_cancel(sender, instance, created, *args, **kwargs):
    if created:
        account_deletion = AccountDeletionRequest.objects.filter(
            user=instance.project_user.user,
            status__name__in=['Queued', 'Ready'],
            requester__name='System'
        )

        if account_deletion.exists():
            account_deletion = account_deletion.first()
            account_deletion.status = \
                AccountDeletionRequestStatusChoice.objects.get(name='Cancelled')
            account_deletion.state['other'] = {
                'justification': f'User requested to join project '
                                 f'{instance.project_user.project.name}.',
                'timestamp': utc_now_offset_aware().isoformat()}
            account_deletion.save()

            message = f'Set AccountDeletionRequest {account_deletion} to ' \
                      f'\"Cancelled.\" User {instance.project_user.user} ' \
                      f'requested to join project ' \
                      f'{instance.project_user.project.name}.'
            logger.info(message)


@receiver(post_save, sender=SavioProjectAllocationRequest)
def savio_proj_request_account_deletion_cancel(sender, instance, created, *args, **kwargs):
    if created:
        account_deletion = AccountDeletionRequest.objects.filter(
            user=instance.requester,
            status__name__in=['Queued', 'Ready'],
            requester__name='System'
        )

        if account_deletion.exists():
            account_deletion = account_deletion.first()
            account_deletion.status = \
                AccountDeletionRequestStatusChoice.objects.get(name='Cancelled')
            account_deletion.state['other'] = {
                'justification': f'User requested to create project '
                                 f'{instance.project.name}.',
                'timestamp': utc_now_offset_aware().isoformat()}
            account_deletion.save()

            message = f'Set AccountDeletionRequest {account_deletion} to ' \
                      f'\"Cancelled.\" User requested to create project ' \
                      f'{instance.project.name}.'
            logger.info(message)


@receiver(post_save, sender=SavioProjectAllocationRequest)
def vector_proj_request_account_deletion_cancel(sender, instance, created, *args, **kwargs):
    if created:
        account_deletion = AccountDeletionRequest.objects.filter(
            user=instance.requester,
            status__name__in=['Queued', 'Ready'],
            requester__name='System'
        )

        if account_deletion.exists():
            account_deletion = account_deletion.first()
            account_deletion.status = \
                AccountDeletionRequestStatusChoice.objects.get(name='Cancelled')
            account_deletion.state['other'] = {
                'justification': f'User requested to create project '
                                 f'{instance.project.name}.',
                'timestamp': utc_now_offset_aware().isoformat()}
            account_deletion.save()

            message = f'Set AccountDeletionRequest {account_deletion} to ' \
                      f'\"Cancelled.\" User requested to create project ' \
                      f'{instance.project.name}.'
            logger.info(message)
