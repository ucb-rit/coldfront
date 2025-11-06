import os

from rest_framework import serializers

from coldfront.plugins.faculty_storage_allocations.models import FacultyStorageAllocationRequest


"""Serializers for Faculty Storage Allocations API."""


class FSARequestNextSerializer(serializers.ModelSerializer):
    """Serializer for the next FSA request to be processed by the agent.

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
        from coldfront.plugins.faculty_storage_allocations.services import DirectoryService

        # Use service to get the directory path (handles both pending and existing)
        return DirectoryService.get_directory_path_for_project(
            obj.project, fsa_request=obj
        )

    def get_set_size_gb(self, obj):
        """Calculate the total size to set (current + approved delta).

        This is the idempotent quota value the agent should set.
        """
        from coldfront.plugins.faculty_storage_allocations.services import DirectoryService

        # Use service to get the directory name (handles both pending and existing)
        directory_name = DirectoryService.get_directory_name_for_project(
            obj.project, fsa_request=obj
        )

        # Get current quota from the allocation
        directory_service = DirectoryService(obj.project, directory_name)
        current_quota_gb = directory_service.get_current_quota_gb()

        # If directory doesn't exist yet, current quota is 0
        if current_quota_gb is None:
            current_quota_gb = 0

        # Add the approved amount to get the total size to set
        # If approved_amount_gb not set, use requested_amount_gb as fallback
        approved_amount = obj.approved_amount_gb or obj.requested_amount_gb
        set_size_gb = current_quota_gb + approved_amount

        return set_size_gb


class FSARequestCompletionSerializer(serializers.Serializer):
    """Serializer for marking a FSA request as complete.

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
