import logging
import os

from django.core.management.base import BaseCommand

from coldfront.core.resource.models import AttributeType
from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceAttribute
from coldfront.core.resource.models import ResourceAttributeType
from coldfront.core.resource.models import ResourceType

from coldfront.plugins.cluster_storage.models import FacultyStorageAllocationRequestStatusChoice


"""An admin command that creates objects for storing 
relevant cluster directories."""


class Command(BaseCommand):
    help = 'Manually creates objects for storing relevant cluster directories.'
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        """
        Creates default objects used for storing cluster directories
        """
        path = ResourceAttributeType.objects.get(
            attribute_type=AttributeType.objects.get(name='Text'),
            name='path')

        cluster_directory = ResourceType.objects.get(name='Cluster Directory')

        scratch_directory = Resource.objects.get(
            resource_type=cluster_directory,
            name='Scratch Directory',
            description='The parent directory containing scratch data.')

        scratch_path = ResourceAttribute.objects.get(
            resource_attribute_type=path,
            resource=scratch_directory,
            value='/global/scratch/')

        scratch_faculty_storage_directory, _ = Resource.objects.get_or_create(
            parent_resource=scratch_directory,
            resource_type=cluster_directory,
            name='Scratch Faculty Storage Directory',
            description=(
                'The parent directory containing Faculty Storage Allocation '
                'data in the scratch directory.'))

        scratch_faculty_storage_path, _ = \
            ResourceAttribute.objects.get_or_create(
                resource_attribute_type=path,
                resource=scratch_faculty_storage_directory,
                value=os.path.join(scratch_path.value, 'fsa'))

        faculty_storage_allocation_request_status_choice_names = (
            'Under Review',
            'Approved - Queued',
            'Approved - Processing',
            'Approved - Complete',
            'Denied',
        )
        for name in faculty_storage_allocation_request_status_choice_names:
            FacultyStorageAllocationRequestStatusChoice.objects.get_or_create(
                name=name)
