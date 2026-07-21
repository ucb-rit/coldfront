from rest_framework import serializers

from coldfront.core.resource.models import Resource


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ("name",)
