from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import (AttributeType,
                                              AllocationAdditionRequestStatusChoice,
                                              AllocationAttributeType,
                                              AllocationRenewalRequestStatusChoice,
                                              AllocationStatusChoice,
                                              AllocationUserStatusChoice,
                                              ClusterAccessRequestStatusChoice)

from flags.state import flag_enabled


class Command(BaseCommand):
    help = 'Add default allocation related choices'

    def handle(self, *args, **options):

        for attribute_type in ('Date', 'Float', 'Int', 'Text', 'Yes/No'):
            AttributeType.objects.get_or_create(name=attribute_type)

        for choice in ('Active', 'Denied', 'Expired',
                       'New', 'Paid', 'Payment Pending',
                       'Payment Requested', 'Payment Declined',
                       'Renewal Requested', 'Revoked', 'Unpaid',):
            AllocationStatusChoice.objects.get_or_create(name=choice)

        for choice in ('Active', 'Error', 'Removed', ):
            AllocationUserStatusChoice.objects.get_or_create(name=choice)

        for name, attribute_type, has_usage, is_private in (
            ('Cloud Account Name', 'Text', False, False),
            ('CLOUD_USAGE_NOTIFICATION', 'Yes/No', False, True),
            ('Cluster Account Status', 'Text', False, False),
            ('Core Usage (Hours)', 'Int', True, False),
            ('Cloud Storage Quota (TB)', 'Float', True, False),
            ('EXPIRE NOTIFICATION', 'Yes/No', False, True),
            ('freeipa_group', 'Text', False, False),
            ('Is Course?', 'Yes/No', False, True),
            ('Paid', 'Float', False, False),
            ('Paid Cloud Support (Hours)', 'Float', True, True),
            ('Paid Network Support (Hours)', 'Float', True, True),
            ('Paid Storage Support (Hours)', 'Float', True, True),
            ('Purchase Order Number', 'Int', False, True),
            ('send_expiry_email_on_date', 'Date', False, True),
            ('slurm_account_name', 'Text', False, False),
            ('slurm_specs', 'Text', False, True),
            ('slurm_user_specs', 'Text', False, True),
            ('Storage Quota (GB)', 'Int', False, False),
            ('Storage_Group_Name', 'Text', False, False),
            ('SupportersQOS', 'Yes/No', False, False),
            ('SupportersQOSExpireDate', 'Date', False, False),
        ):
            AllocationAttributeType.objects.get_or_create(name=name, attribute_type=AttributeType.objects.get(
                name=attribute_type), has_usage=has_usage, is_private=is_private)

        # Make 'Cluster Account Status' unique.
        AllocationAttributeType.objects.filter(
            name='Cluster Account Status').update(is_unique=True)

        # Create LRC-only AllocationAttributeTypes.
        if flag_enabled('LRC_ONLY'):
            # The primary key of the BillingActivity object to be treated as
            # the default for the Allocation.
            AllocationAttributeType.objects.update_or_create(
                attribute_type=AttributeType.objects.get(name='Int'),
                name='Billing Activity',
                defaults={
                    'has_usage': False,
                    'is_required': False,
                    'is_unique': True,
                    'is_private': True,
                })

        choices = [
            'Under Review',
            'Approved',
            'Denied',
            'Complete',
        ]
        for choice in choices:
            AllocationRenewalRequestStatusChoice.objects.get_or_create(
                name=choice)

        choices = [
            'Under Review',
            'Denied',
            'Complete',
        ]
        for choice in choices:
            AllocationAdditionRequestStatusChoice.objects.get_or_create(
                name=choice)

        choices = [
            'Denied',
            'Complete',
            'Pending - Add',
            'Processing'
        ]
        for choice in choices:
            ClusterAccessRequestStatusChoice.objects.get_or_create(
                name=choice)
