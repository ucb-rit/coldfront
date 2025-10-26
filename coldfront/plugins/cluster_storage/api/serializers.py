import os

from rest_framework import serializers

from coldfront.plugins.cluster_storage.models import FacultyStorageAllocationRequest


"""Serializers for cluster storage API."""


class StorageRequestNextSerializer(serializers.ModelSerializer):
    """Serializer for the next storage request to be processed by the agent.

    This includes all information needed for the agent to idempotently set
    the quota.
    """
    directory_path = serializers.SerializerMethodField()
    set_size_gb = serializers.SerializerMethodField()
    requested_delta_gb = serializers.IntegerField(source='approved_amount_gb', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = FacultyStorageAllocationRequest
        fields = [
            'id',
            'project_name',
            'directory_path',
            'set_size_gb',
            'requested_delta_gb',
            'status',
            'approval_time',
        ]
        read_only_fields = fields

    def get_directory_path(self, obj):
        """Get the full directory path from the resource attribute."""
        from coldfront.core.resource.models import Resource

        directory_name = obj.state.get('setup', {}).get('directory_name', '')
        if not directory_name:
            # Fallback to project name if not set
            directory_name = obj.project.name

        # Get the base path from the resource attribute
        faculty_storage_resource = Resource.objects.get(
            name='Scratch Faculty Storage Directory')
        base_path_attr = faculty_storage_resource.resourceattribute_set.get(
            resource_attribute_type__name='path')

        # Construct full path using base path + directory name
        return os.path.join(base_path_attr.value, directory_name)

    def get_set_size_gb(self, obj):
        """Calculate the total size to set (current + approved delta).

        This is the idempotent quota value the agent should set.
        """
        from coldfront.plugins.cluster_storage.services import DirectoryService

        directory_name = obj.state.get('setup', {}).get('directory_name', '')
        if not directory_name:
            directory_name = obj.project.name

        # Get current quota from the allocation
        directory_service = DirectoryService(obj.project, directory_name)
        current_quota_gb = directory_service.get_current_quota_gb()

        # Add the approved amount to get the total size to set
        # approved_amount_gb is guaranteed to be set by approve_request()
        set_size_gb = current_quota_gb + obj.approved_amount_gb

        return set_size_gb


class StorageRequestCompletionSerializer(serializers.Serializer):
    """Serializer for marking a storage request as complete.

    The agent must provide the directory_name it actually used when setting
    the quota. This ensures the state accurately reflects what was done.
    """
    directory_name = serializers.CharField(
        required=True,
        max_length=255,
        help_text="The directory name used for the storage allocation"
    )

    def validate_directory_name(self, value):
        """Validate the directory name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Directory name cannot be empty.")
        return value.strip()
