from django.contrib.auth.models import User
from django.conf import settings
from django.core.management.base import BaseCommand

from coldfront.core.utils.mail import send_email_template
from coldfront.core.project.models import ProjectUserJoinRequest, Project
from coldfront.core.project.utils import project_join_list_url
from coldfront.core.project.utils import review_project_join_requests_url

import logging

"""An admin command that sends PIs reminder emails of pending join requests."""


class Command(BaseCommand):

    help = (
        'Send PIs reminder emails of pending join requests.')
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):

        proj_join_requests_queryset = \
            ProjectUserJoinRequest.objects.filter(
                project_user__status__name='Pending - Add')

        projects_with_pending_join_requests = proj_join_requests_queryset.values_list(
            'project_user__project', flat=True).distinct()

        users_with_pending_join_requests = proj_join_requests_queryset.values_list(
            'project_user__user', flat=True).distinct()

        emails_sent = 0
        for pk in projects_with_pending_join_requests:
            project = Project.objects.get(pk=pk)
            proj_join_requests_queryset = \
                ProjectUserJoinRequest.objects.filter(
                    project_user__project=project,
                    project_user__status__name='Pending - Add').\
                    order_by('project_user', '-created').\
                    distinct('project_user')

            if settings.EMAIL_ENABLED:

                request_entries = []
                for request in proj_join_requests_queryset:
                    first_name = request.project_user.user.first_name
                    last_name = request.project_user.user.last_name
                    email = request.project_user.user.email
                    created = request.created.strftime("%m/%d/%Y, %H:%M")
                    request_entries.append({
                        'name': f'{first_name} {last_name}',
                        'email': email,
                        'created': created,
                    })

                context = {
                    'PORTAL_NAME': settings.PORTAL_NAME,
                    'project_name': project.name,
                    'request_entries': request_entries,
                    'num_requests': proj_join_requests_queryset.count(),
                    'verb': 'are' if proj_join_requests_queryset.count() > 1 else 'is',
                    'pk': project.pk,
                    'review_url': review_project_join_requests_url(project),
                    'signature': settings.EMAIL_SIGNATURE,
                    'signature_html': settings.EMAIL_SIGNATURE.replace('\n', '<br>'),
                }

                recipients = project.managers_and_pis_emails()
                try:
                    subject = 'Pending Project Join Requests'
                    plain_template = 'email/project_join_request/' \
                                     'pending_project_join_requests.txt'
                    html_template = 'email/project_join_request/' \
                                    'pending_project_join_requests.html'
                    send_email_template(subject,
                                        plain_template,
                                        context,
                                        settings.EMAIL_SENDER,
                                        recipients,
                                        html_template=html_template)

                    emails_sent += len(recipients)
                except Exception as e:
                    message = 'Failed to send reminder email. Details:'
                    self.stderr.write(self.style.ERROR(message))
                    self.stderr.write(self.style.ERROR(str(e)))
                    self.logger.error(message)
                    self.logger.exception(e)

        for pk in users_with_pending_join_requests:
            user = User.objects.get(pk=pk)
            proj_join_requests_queryset = \
                ProjectUserJoinRequest.objects.filter(
                    project_user__user=user,
                    project_user__status__name='Pending - Add'). \
                    order_by('project_user', '-created'). \
                    distinct('project_user')

            if settings.EMAIL_ENABLED:
                request_entries = []
                for request in proj_join_requests_queryset:
                    project_name = request.project_user.project.name
                    created = request.created.strftime("%m/%d/%Y, %H:%M")
                    request_entries.append({
                        'project': project_name,
                        'created': created,
                    })

                context = {
                    'PORTAL_NAME': settings.PORTAL_NAME,
                    'user_name': f'{user.first_name} {user.last_name}',
                    'request_entries': request_entries,
                    'num_requests': proj_join_requests_queryset.count(),
                    'review_url': project_join_list_url(),
                    'signature': settings.EMAIL_SIGNATURE,
                    'signature_html': settings.EMAIL_SIGNATURE.replace('\n', '<br>'),
                }

                try:
                    send_email_template(
                        'Pending Project Join Requests',
                        'email/project_join_request/pending_project_join_request_user.txt',
                        context,
                        settings.EMAIL_SENDER,
                        [user.email],
                        html_template='email/project_join_request/pending_project_join_request_user.html')
                    emails_sent += 1
                except Exception as e:
                    message = 'Failed to send reminder email. Details:'
                    self.stderr.write(self.style.ERROR(message))
                    self.stderr.write(self.style.ERROR(str(e)))
                    self.logger.error(message)
                    self.logger.exception(e)

        self.stdout.write(self.style.SUCCESS(f'Sent {str(emails_sent)} '
                                             f'reminder emails.'))
