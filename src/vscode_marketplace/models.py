from typing import TYPE_CHECKING, Any, Generic, Type, TypeVar, cast
import uuid
from django.db import models
from django.db.models import functions

from django.core.files.storage import storages, default_storage, Storage
from semver.version import Comparable
from taggit.managers import TaggableManager
from taggit.models import TagBase, ItemBase, GenericUUIDTaggedItemBase

from generic_storage.models import GenericStorageFileField, GenericStorageFieldFile

import semver
from .typing.gallery import AssetType, SortBy, SortOrder, GalleryCriterium, FilterType
from .typing import gallery as _gallery
from .api import utils as api_utils

if TYPE_CHECKING:
    from _typeshed import Self


__all__ = []
# Create your models here.

# https://learn.microsoft.com/en-us/visualstudio/extensibility/vsix-extension-schema-2-0-reference?view=vs-2022
# Info about field sizes


def _get_storage(
    field: "GenericStorageFileField", extension: "GalleryExtensionFile"
) -> Storage:
    if extension.storage:
        return storages[extension.storage]
    else:
        return default_storage


class _Version(semver.Version):
    def compare(self, other: Comparable) -> int:
        if isinstance(other, str) and other == "":
            return -1
        return super().compare(other)


class SemVerField(models.CharField):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["max_length"] = 255
        super(SemVerField, self).__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            # none here assumes the field will be nullable
            # if not nullable, the code will not be reach here. an error is thrown.
            return None

        return _Version.parse(value)

    def to_python(self, value):
        if isinstance(value, (_Version, semver.Version)) or value is None:
            return value

        return _Version.parse(value)

    def get_prep_value(self, value):
        value = models.Field.get_prep_value(self, value)
        if value is None:
            return None

        return str(value)


class GalleryExtensionTag(TagBase):
    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"


__all__.append(GalleryExtensionTag.__name__)


class GalleryExtensionTags(ItemBase):
    content_object = models.ForeignKey("GalleryExtension", on_delete=models.CASCADE)
    tag = models.ForeignKey(
        GalleryExtensionTag, on_delete=models.CASCADE, related_name="%(class)s_items"
    )

    class Meta:
        unique_together = ["content_object", "tag"]


class GalleryExtensionCategory(TagBase):
    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"


__all__.append(GalleryExtensionCategory.__name__)


class GalleryExtensionCategories(ItemBase):
    content_object = models.ForeignKey("GalleryExtension", on_delete=models.CASCADE)
    tag = models.ForeignKey(
        GalleryExtensionCategory,
        on_delete=models.CASCADE,
        related_name="%(class)s_items",
    )

    class Meta:
        unique_together = ["content_object", "tag"]


class _Named(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=50)

    class Meta:
        abstract = True


class GalleryExtensionPublisher(_Named):
    name = models.CharField(max_length=100, unique=True)
    domain = models.CharField(max_length=255, null=True)
    domain_verified = models.BooleanField(null=True)
    extensions: models.QuerySet["GalleryExtension"]

    def __str__(self) -> str:
        return self.name


__all__.append(GalleryExtensionPublisher.__name__)

M = TypeVar("M", bound=models.Model, covariant=True)


class PageQuerySet(models.QuerySet[M]):
    def page(self, page: int, page_size: int = 100) -> "PageQuerySet[M]":
        start = ((page or 1) - 1) * page_size
        end = start + page_size
        return self[start:end]


class _GalleryExtensionManager(
    cast(models.Manager["GalleryExtension"], models.Manager).from_queryset(PageQuerySet)
):
    def get_queryset(self) -> PageQuerySet["GalleryExtension"]:
        return (
            super(_GalleryExtensionManager, self)
            .get_queryset()
            .annotate(
                uid=functions.Concat(
                    "publisher__name",
                    models.Value("."),
                    "name",
                    output_field=models.CharField(),
                )
            )
        )


class GalleryExtension(_Named):
    objects = _GalleryExtensionManager()
    uid: str
    description = models.CharField(max_length=1000)
    publisher = models.ForeignKey(
        GalleryExtensionPublisher, related_name="extension", on_delete=models.CASCADE
    )
    publisher: GalleryExtensionPublisher
    versions: models.QuerySet["GalleryExtensionVersion"]
    statistics: models.QuerySet["GalleryExtensionStatistic"]
    tags = TaggableManager(through=GalleryExtensionTags)
    released = models.DateTimeField()
    published = models.DateTimeField()
    categories = TaggableManager(through=GalleryExtensionCategories)
    flags = models.CharField(max_length=255)

    @property
    def latest_version(self):
        return self.versions.order_by("-last_updated").first()

    @classmethod
    def sort(
        cls, sortOrder: _gallery.SortOrder, sortBy: _gallery.SortBy
    ) -> PageQuerySet["GalleryExtension"]:
        statistic_name = None
        orderby = "_orderby"
        qs = cls.objects.get_queryset().prefetch_related("publisher", "tags", "categories")
        if sortBy is _gallery.SortBy.AverageRating:
            statistic_name = "averagerating"
        elif sortBy is _gallery.SortBy.InstallCount:
            statistic_name = "install"
        elif sortBy is _gallery.SortBy.WeightedRating:
            statistic_name = "weightedRating"
        elif sortBy is _gallery.SortBy.Title:
            orderby = "display_name"
        elif sortBy is _gallery.SortBy.PublisherName:
            orderby = "publisher__display_name"
        elif sortBy is _gallery.SortBy.PublishedDate:
            orderby = "published"
        elif sortBy is _gallery.SortBy.LastUpdatedDate:
            qs = qs
        else:
            orderby = "name"

        if _gallery.SortOrder.Descending is sortOrder:
            orderby = f"-{orderby}"
        if statistic_name:
            qs = qs.annotate(
                _orderby=models.Avg(
                    "statistic__value", filter=models.Q(name=statistic_name)
                )
            )
        return qs.order_by(orderby)

    @classmethod
    def query(
        cls,
        criteria: "list[GalleryCriterium]" = None,
        sortBy: SortBy = SortBy.NoneOrRelevance,
        sortOrder: SortOrder = SortOrder.Default,
    ):
        sorted = cls.sort(sortOrder, sortBy)
        if not criteria:
            criteria = []
        elif isinstance(criteria, str):
            criteria = [{"filterType": FilterType.SearchText, "value": criteria}]
        return sorted.filter(api_utils.criteria_query(criteria)) if criteria else sorted

    def __str__(self) -> str:
        return self.uid

    class Meta:
        base_manager_name = 'objects'
        constraints = [
            models.UniqueConstraint(
                fields=["name", "publisher"], name="gallery_extension_unique_name"
            )
        ]


__all__.append(GalleryExtension.__name__)


class GalleryExtensionStatistic(models.Model):
    extension = models.ForeignKey(
        GalleryExtension, on_delete=models.CASCADE, related_name="statistics"
    )
    name = models.CharField(max_length=255)
    value = models.FloatField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "extension"], name="gallery_extension_statistic_uid"
            )
        ]


class GalleryExtensionVersion(models.Model):
    extension = models.ForeignKey(
        GalleryExtension, on_delete=models.CASCADE, related_name="versions"
    )
    extension: GalleryExtension
    version = SemVerField()
    last_updated = models.DateTimeField()
    assets: models.QuerySet["GalleryExtensionFile"]
    properties: models.QuerySet["GalleryExtensionProperty"]
    target_platform = models.CharField(max_length=100, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["version", "extension"], name="gallery_extension_version_uid"
            )
        ]

    def __str__(self) -> str:
        return f"{self.extension.uid} v{self.version}"

    def icon(self):
        icon = self.assets.filter(type=_gallery.AssetType.Icon).first()
        if icon:
            return f'/assets/extensions/{self.extension.publisher.name}/{self.extension.name}/{self.version}/{AssetType.Icon}'

__all__.append(GalleryExtensionVersion.__name__)


class _ExtVerLinked(models.Model):
    extension_version = models.ForeignKey(
        GalleryExtensionVersion, on_delete=models.CASCADE
    )
    extension_version: GalleryExtensionVersion

    class Meta:
        abstract = True

    @property
    def extension(self):
        self.extension_version.extension


class GalleryExtensionFile(_ExtVerLinked):
    extension_version = models.ForeignKey(
        GalleryExtensionVersion, on_delete=models.CASCADE, related_name="assets"
    )
    type = models.CharField(max_length=255)
    source = models.URLField(null=True)
    file = GenericStorageFileField(storage=_get_storage)
    file: "models.FieldFile"
    storage = models.CharField(max_length=255, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["extension_version", "type", "storage"],
                name="gallery_extension_file_uid",
            )
        ]


__all__.append(GalleryExtensionFile.__name__)


class GalleryExtensionProperty(_ExtVerLinked):
    extension_version = models.ForeignKey(
        GalleryExtensionVersion, on_delete=models.CASCADE, related_name="properties"
    )
    key = models.CharField(max_length=255)
    value = models.TextField()

    class Meta:
        verbose_name = "GalleryExtensionProperty"
        verbose_name_plural = "GalleryExtensionProperties"
        constraints = [
            models.UniqueConstraint(
                fields=["extension_version", "key"],
                name="gallery_extension_property_uid",
            )
        ]


__all__.append(GalleryExtensionProperty.__name__)
