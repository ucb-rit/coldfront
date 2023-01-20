from datetime import datetime

from django.contrib.auth.models import User
from rest_framework import serializers

from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectUserRemovalRequestStatusChoice
from coldfront.core.project.models import ProjectUserRemovalRequest
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import SavioProjectAllocationRequest


class NewProjectRequestSetupSerializerField(serializers.Field):
    """A serializer field that handles the representation of the 'setup'
    entry in the state field of a SavioProjectAllocationRequest."""

    def get_attribute(self, request):
        return request.state['setup']

    def to_representation(self, setup):
        return setup

    def to_internal_value(self, data):
        return data


class NewProjectRequestSerializer(serializers.ModelSerializer):
    """A serializer for the SavioProjectAllocationRequest model."""

    status = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ProjectAllocationRequestStatusChoice.objects.all())
    setup = NewProjectRequestSetupSerializerField()

    class Meta:
        model = SavioProjectAllocationRequest
        fields = (
            'id', 'project', 'pi', 'requester', 'allocation_period', 'pool',
            'status', 'request_time', 'approval_time', 'completion_time',
            'billing_activity', 'setup')
        read_only_fields = (
            'id', 'project', 'pi', 'requester', 'allocation_period', 'pool',
            'request_time', 'approval_time', 'completion_time',
            'billing_activity')

    # def validate(self, data):
    #     """TODO"""


class ProjectSerializer(serializers.ModelSerializer):
    """A serializer for the Project model."""

    class Meta:
        model = Project
        fields = '__all__'


class ProjectUserSerializer(serializers.ModelSerializer):
    """A serializer for the ProjectUser model."""

    status = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ProjectUserStatusChoice.objects.all())
    role = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ProjectUserRoleChoice.objects.all())
    user = serializers.SlugRelatedField(
        slug_field='username',
        queryset=User.objects.all())
    project = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Project.objects.all())

    class Meta:
        model = ProjectUser
        fields = ('id', 'user', 'project', 'role', 'status')


class ProjectUserRemovalRequestSerializer(serializers.ModelSerializer):
    """A serializer for the ProjectUserRemovalRequest model."""
    status = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ProjectUserRemovalRequestStatusChoice.objects.all())

    project_user = ProjectUserSerializer(read_only=True,
                                         allow_null=True,
                                         required=False)

    class Meta:
        model = ProjectUserRemovalRequest
        fields = ('id', 'completion_time', 'status', 'project_user')
        extra_kwargs = {
            'id': {'read_only': True},
            'completion_time': {'required': False, 'allow_null': True},
        }

    def validate(self, data):
        """If the status is being changed to 'Complete', ensure that a
        completion_time is given."""
        complete_status = ProjectUserRemovalRequestStatusChoice.objects.get(
            name='Complete')
        if 'status' in data and data['status'] == complete_status:
            if not isinstance(data.get('completion_time', None), datetime):
                message = 'No completion_time is given.'
                raise serializers.ValidationError(message)
        return data
