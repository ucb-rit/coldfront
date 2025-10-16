import os

from django.db import transaction

from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource


class DirectoryService:

    def __init__(self, project, directory_name):
        assert isinstance(project, Project)
        self.project = project
        self.directory_name = directory_name

        self._faculty_storage_directory = Resource.objects.get(
            name='Scratch Faculty Storage Directory')

        # Get base directory path
        directory_path_attr = \
            self._faculty_storage_directory.resourceattribute_set.get(
                resource_attribute_type__name='path')
        self._directory_path = os.path.join(
            directory_path_attr.value, self.directory_name)

        # Cache for allocation (lazy-loaded)
        self._allocation = None

    def _get_allocation(self, refresh=False):
        """
        Get the allocation for this directory, with optional caching.

        Args:
            refresh: If True, bypass cache and fetch fresh from DB

        Returns:
            Allocation object or None if not found
        """
        if refresh or self._allocation is None:
            try:
                self._allocation = Allocation.objects.get(
                    project=self.project,
                    resources=self._faculty_storage_directory,
                    allocationattribute__value=self._directory_path
                )
            except Allocation.DoesNotExist:
                self._allocation = None
            except Allocation.MultipleObjectsReturned as e:
                raise e

        return self._allocation

    def create_directory(self):
        """Create a directory idempotently for the given project."""
        active_status = AllocationStatusChoice.objects.get(name='Active')
        allocation = self._get_allocation()

        if allocation is None:
            # Doesn't exist, create it
            with transaction.atomic():
                allocation = Allocation.objects.create(
                    project=self.project,
                    status=active_status)
                allocation.resources.add(self._faculty_storage_directory)
                allocation_attribute_type = AllocationAttributeType.objects.get(
                    name='Cluster Directory Access')
                AllocationAttribute.objects.create(
                    allocation_attribute_type=allocation_attribute_type,
                    allocation=allocation,
                    value=self._directory_path)
                # Cache the newly created allocation
                self._allocation = allocation
        else:
            # Exists, update status if needed
            allocation.status = active_status
            allocation.save()
            # Refresh cache
            self._allocation = allocation

        return allocation

    def directory_exists(self):
        """Check if the directory already exists for the project."""
        return Allocation.objects.filter(
            project=self.project,
            resources=self._faculty_storage_directory,
            allocationattribute__value=self._directory_path
        ).exists()

    def set_directory_quota(self, amount_gb):
        """
        Set the storage quota for the directory.

        Args:
            amount_gb: The quota amount in GB
        """
        allocation = self._get_allocation()
        if allocation is None:
            raise ValueError(
                'Cannot set quota: directory allocation does not exist. '
                'Call create_directory() first.'
            )

        quota_attribute_type = AllocationAttributeType.objects.get(
            name='Storage Quota (GB)')

        AllocationAttribute.objects.update_or_create(
            allocation_attribute_type=quota_attribute_type,
            allocation=allocation,
            defaults={'value': str(amount_gb)}
        )

    def add_to_directory_quota(self, additional_gb):
        """
        Add to the existing storage quota for the directory.

        Args:
            additional_gb: The amount to add in GB
        """
        allocation = self._get_allocation(refresh=True)  # Refresh for current quota
        if allocation is None:
            raise ValueError(
                'Cannot add to quota: directory allocation does not exist.'
            )

        quota_attribute_type = AllocationAttributeType.objects.get(
            name='Storage Quota (GB)')

        try:
            quota_attr = AllocationAttribute.objects.get(
                allocation_attribute_type=quota_attribute_type,
                allocation=allocation
            )
            current_quota = int(quota_attr.value)
            new_quota = current_quota + additional_gb
            quota_attr.value = str(new_quota)
            quota_attr.save()
        except AllocationAttribute.DoesNotExist:
            # No existing quota, just set it
            AllocationAttribute.objects.create(
                allocation_attribute_type=quota_attribute_type,
                allocation=allocation,
                value=str(additional_gb)
            )


# TODO: Verify implementation.
