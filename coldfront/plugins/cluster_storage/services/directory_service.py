import os

from django.db import transaction

from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.utils import get_or_create_active_allocation_user
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.resource.models import Resource


class DirectoryService:
    """
    Service for managing faculty storage directories and their
    allocations.

    This service handles all operations related to faculty storage
    directories, including:
        - Creating directories (allocations)
        - Setting and updating storage quotas
        - Adding users to directory allocations
        - Looking up existing directory information

    Usage:
        # When you know the directory name (e.g., from a request)
        service = DirectoryService(project, directory_name)
        service.create_directory()
        service.set_directory_quota(500)

        # When working with an existing allocation
        service = DirectoryService.for_project(project)
        if service:
            service.add_user_to_directory(user)
    """

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

    @staticmethod
    def get_directory_name_for_project(project):
        """
        Look up the directory name for a project's existing faculty
        storage allocation.

        Args:
            project: The Project object

        Returns:
            The directory name (string), or None if no allocation exists

        Raises:
            ValueError: If multiple allocations exist (shouldn't happen)
        """
        faculty_storage_resource = Resource.objects.get(
            name='Scratch Faculty Storage Directory')

        allocations = Allocation.objects.filter(
            project=project,
            resources=faculty_storage_resource
        )

        if not allocations.exists():
            return None

        if allocations.count() > 1:
            raise ValueError(
                f'Project {project.name} has multiple faculty storage '
                f'allocations, which should not be possible'
            )

        allocation = allocations.first()

        # Extract directory name from the allocation's path attribute
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Directory Access')
        try:
            path_attr = AllocationAttribute.objects.get(
                allocation=allocation,
                allocation_attribute_type=allocation_attribute_type
            )
            # The path is like /global/scratch/my_project_dir
            # Extract just the directory name (last component)
            directory_name = os.path.basename(path_attr.value)
        except AllocationAttribute.DoesNotExist:
            # Shouldn't happen, but fallback to project name
            directory_name = project.name

        return directory_name

    @classmethod
    def for_project(cls, project):
        """
        Create a DirectoryService instance for a project's existing
        allocation.

        This looks up the directory name from the allocation and returns
        a properly-initialized DirectoryService that can perform any
        operation (add users, set quotas, etc.).

        Args:
            project: The Project object

        Returns:
            DirectoryService instance, or None if no allocation exists

        Raises:
            ValueError: If multiple allocations exist (shouldn't happen)
        """
        directory_name = cls.get_directory_name_for_project(project)

        if directory_name is None:
            return None

        return cls(project, directory_name)

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
        allocation = self._get_allocation(refresh=True)
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

    def add_user_to_directory(self, user):
        """
        Add a user to this directory's allocation.

        Args:
            user: The User object to add

        Returns:
            The AllocationUser object

        Raises:
            ValueError: If the directory allocation does not exist
        """
        allocation = self._get_allocation()
        if allocation is None:
            raise ValueError(
                f'Cannot add user to directory: allocation does not exist '
                f'for project {self.project.name} with directory name '
                f'{self.directory_name}. Call create_directory() first.'
            )

        return get_or_create_active_allocation_user(allocation, user)

    def add_project_users_to_directory(self):
        """
        Add all active ProjectUsers to this directory's allocation.

        This operation is atomic - either all users are added
        successfully, or none are added if any error occurs.

        Returns:
            List of created/retrieved AllocationUser objects

        Raises:
            ValueError: If the directory allocation does not exist
        """
        allocation = self._get_allocation()
        if allocation is None:
            raise ValueError(
                f'Cannot add users to directory: allocation does not exist '
                f'for project {self.project.name} with directory name '
                f'{self.directory_name}. Call create_directory() first.'
            )

        active_project_users = ProjectUser.objects.filter(
            project=self.project,
            status__name='Active'
        )

        allocation_users = []
        with transaction.atomic():
            for project_user in active_project_users:
                allocation_user = get_or_create_active_allocation_user(
                    allocation, project_user.user)
                allocation_users.append(allocation_user)

        return allocation_users

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


# TODO: Verify implementation.
