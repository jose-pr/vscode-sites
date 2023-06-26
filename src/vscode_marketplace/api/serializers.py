from rest_framework import serializers

from taggit.serializers import (TagListSerializerField,
                                TaggitSerializer)

from .. import models


class GalleryExtensionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.GalleryExtension
        fields = ["id", "name", "display_name"]


class PublisherSerializer(serializers.Serializer):
    publisherId = serializers.UUIDField(source="id")
    publisherName = serializers.CharField(source="name")
    displayName = serializers.CharField(source="display_name")
    domain = serializers.CharField()
    isDomainVerified = serializers.BooleanField(source="domain_verified")


class AssetSerializer(serializers.Serializer):
    assetType = serializers.CharField(source="type")
    source = serializers.URLField()


class PropertySerializer(serializers.Serializer):
    key = serializers.CharField()
    value = serializers.CharField()


class VersionSerializer(serializers.Serializer):
    version = serializers.CharField()
    lastUpdated = serializers.DateTimeField(source="last_updated")
    files = AssetSerializer(source="assets", many=True)
    properties = PropertySerializer(many=True)
    targetPlatform = serializers.CharField(source="target_platform")
   # flags = serializers.CharField()


# def _files(self, )

class StatisticSerializer(serializers.Serializer):
    statisticName = serializers.CharField(source='name')
    value = serializers.FloatField()



class ExtensionSerializer(serializers.Serializer):
    extensionId = serializers.UUIDField(source="id")
    extensionName = serializers.CharField(source="name")
    displayName = serializers.CharField(source="display_name")
    shortDescription = serializers.CharField(source="description")
    publisher = PublisherSerializer()
    tags = TagListSerializerField()
    releaseDate = serializers.DateTimeField(source='released')
    publishedDate = serializers.DateTimeField(source='published')
    lastUpdated = serializers.DateTimeField(source='last_updated')
    categories = TagListSerializerField()
    flags = serializers.CharField()
    versions = serializers.SerializerMethodField("_versions")
    statistics = StatisticSerializer(many=True)


    def _versions(self, obj: models.GalleryExtension):
        qs = obj.versions.all()[:5]
        return VersionSerializer(instance=qs, many=True).data
