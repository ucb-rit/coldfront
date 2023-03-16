from django.core.management import BaseCommand
from django.contrib.auth.models import User
from coldfront.core.department.utils.ldap import fetch_and_set_user_departments
from coldfront.core.utils.common import add_argparse_dry_run_argument
import logging

class Command(BaseCommand):

    help = 'Populates every users authoritative departments if found via LDAP'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        add_argparse_dry_run_argument(parser)
    
    def log(self, message, dry_run):
        if not dry_run:
            self.logger.info(message)
        print(message)

    def handle(self, *args, **options):
        for user in User.objects.select_related('userprofile').all():
            user_profile = user.userprofile
            fetch_and_set_user_departments(user, user_profile)