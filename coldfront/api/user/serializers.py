from coldfront.core.allocation.models import \
    ClusterAccountDeactivationRequestReasonChoice, \
    ClusterAccountDeactivationRequestStatusChoice, \
    ClusterAccountDeactivationRequest
from coldfront.core.user.models import IdentityLinkingRequest
from coldfront.core.user.models import IdentityLinkingRequestStatusChoice
from django.contrib.auth.models import User
from rest_framework import serializers


class IdentityLinkingRequestSerializer(serializers.ModelSerializer):
    """A serializer for the IdentityLinkingRequest model."""

    status = serializers.SlugRelatedField(
        slug_field='name',
        queryset=IdentityLinkingRequestStatusChoice.objects.all())

    class Meta:
        model = IdentityLinkingRequest
        fields = (
            'id', 'requester', 'request_time', 'completion_time', 'status')
        extra_kwargs = {
            'id': {'read_only': True},
            'requester': {'read_only': True},
            'request_time': {'read_only': True},
        }


class UserSerializer(serializers.ModelSerializer):
    """A serializer for the User model."""

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email')


class ClusterAccountDeactivationRequestSerializer(serializers.ModelSerializer):
    """A serializer for the ClusterAccountDeactivationRequest model."""
    user = serializers.SlugRelatedField(
        slug_field='username',
        queryset=User.objects.all())

    status = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ClusterAccountDeactivationRequestStatusChoice.objects.all())

    reason = serializers.CharField(max_length=200)

    justification = serializers.CharField(allow_null=True, required=False)

    compute_resources = serializers.CharField(allow_null=True, required=False)

    class Meta:
        model = ClusterAccountDeactivationRequest
        fields = (
            'id', 'user', 'status', 'reason', 'justification', 'compute_resources')
        extra_kwargs = {
            'id': {'read_only': True}
        }

    def validate(self, data):
        # If the status is being changed to 'Cancelled', ensure that a
        # justification are given.
        if 'status' in data and data['status'].name == 'Cancelled':
            if not isinstance(data.get('justification', None), str):
                message = 'No justification is given.'
                raise serializers.ValidationError(message)

        if 'reason' in data:
            reasons = data.get('reason').split(',')
            for name in reasons:
                query = \
                    ClusterAccountDeactivationRequestReasonChoice.objects.filter(
                        name=name)
                if not query.exists():
                    message = f'Invalid reason \"{name}\" given.'
                    raise serializers.ValidationError(message)

        return data
