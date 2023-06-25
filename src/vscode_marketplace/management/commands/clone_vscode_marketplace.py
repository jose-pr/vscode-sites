from typing import cast
from django.core.management.base import BaseCommand
import semver

from vscode_marketplace import models, query
from vscode_marketplace.typing import gallery
import requests

import itertools


def batched(it, size):
    it = iter(it)
    return iter(lambda: tuple(itertools.islice(it, size)), ())


class GalleryRecords:
    extensions: list[models.GalleryExtension]
    publishers: list[models.GalleryExtensionPublisher]
    versions: list[models.GalleryExtensionVersion]
    properties: list[models.GalleryExtensionProperty]
    assets: list[models.GalleryExtensionFile]
    statistics: list[models.GalleryExtensionStatistic]

    def __init__(self) -> None:
        self.extensions = []
        self.publishers = []
        self.versions = []
        self.properties = []
        self.assets = []
        self.statistics = []

    def update(self):
        models.GalleryExtensionPublisher.objects.bulk_create(
            self.publishers,
            update_fields=["name", "display_name", "domain", "domain_verified"],
            unique_fields=["id"],
            update_conflicts=True,
        )
        models.GalleryExtension.objects.bulk_create(
            self.extensions,
            update_fields=[
                "name",
                "display_name",
                "publisher_id",
                "description",
                "released",
                "published",
                "flags",
            ],
            update_conflicts=True,
            unique_fields=["id"],
        )
        models.GalleryExtensionStatistic.objects.bulk_create(
            self.statistics,
            update_conflicts=True,
            unique_fields=["extension_id", "name"],
            update_fields=["value"],
        )
        for ext in self.extensions:
            ext.categories.set(ext._categories)
            ext.tags.set(ext._tags)
        models.GalleryExtensionVersion.objects.bulk_create(
            self.versions,
            update_conflicts=True,
            unique_fields=["version", "extension_id"],
            update_fields=["last_updated", "target_platform"],
        )
        models.GalleryExtensionProperty.objects.bulk_create(
            self.properties,
            update_conflicts=True,
            unique_fields=["extension_version_id", "key"],
            update_fields=["value"],
        )
        models.GalleryExtensionFile.objects.bulk_create(
            self.assets,
            update_conflicts=True,
            unique_fields=["extension_version_id", "type", "storage"],
            update_fields=["source"],
        )


class Command(BaseCommand):
    help = "Displays current time"

    def add_arguments(self, parser):
        parser.add_argument(
            "--host",
            type=str,
            help="",
            default="https://marketplace.visualstudio.com",
            required=False,
        )
        parser.add_argument(
            "--endpoint", type=str, help="", default="/_apis", required=False
        )

    def handle(self, *args, **kwargs):
        api_url = f"{kwargs['host']}/{kwargs['endpoint'].strip('/')}/public/gallery/extensionquery"
        _query = query.simple_query(
            "python", pageSize=100, flags=query.EXTENSION_MINIMUM_FLAG
        )
        result = cast(
            gallery.GalleryQueryResult,
            requests.post(
                api_url,
                json=_query,
                headers={"accept": "application/json;api-version=1.0"},
            ).json(),
        )
        publisher_ids = set()
        extension_ids = set()
        for ext in result["results"][0]["extensions"]:
            extension_ids.add(ext["extensionId"])

        for group in batched(extension_ids, 50):
            update = GalleryRecords()
            for ext in cast(
                gallery.GalleryQueryResult,
                requests.post(
                    api_url,
                    headers={"accept": "application/json;api-version=3.0-preview.1"},
                    json=query.simple_query(
                        [
                            {
                                "filterType": query.FilterType.ExtensionId,
                                "value": uuid,
                            }
                            for uuid in group
                        ]
                    ),
                ).json(),
            )["results"][0]["extensions"]:
                pub = ext["publisher"]
                if pub["publisherId"] not in publisher_ids:
                    update.publishers.append(
                        models.GalleryExtensionPublisher(
                            id=pub["publisherId"],
                            name=pub["publisherName"],
                            display_name=pub["displayName"],
                            domain=pub.get("domain"),
                            domain_verified=pub.get("isDomainVerified"),
                        )
                    )
                    publisher_ids.add(pub["publisherId"])
                extension = models.GalleryExtension(
                    id=ext["extensionId"],
                    name=ext["extensionName"],
                    display_name=ext["displayName"],
                    publisher_id=pub["publisherId"],
                    description=ext.get("shortDescription", ""),
                    released=ext["releaseDate"],
                    published=ext["publishedDate"],
                    flags=ext["flags"],
                )
                for stat in ext["statistics"]:
                    update.statistics.append(
                        models.GalleryExtensionStatistic(
                            extension_id=extension.id,
                            name=stat["statisticName"],
                            value=stat["value"],
                        )
                    )
                setattr(extension, "_categories", ext["categories"] or [])
                setattr(extension, "_tags", ext.get("tags") or [])
                update.extensions.append(extension)
                for ver in ext["versions"]:
                    version = models.GalleryExtensionVersion(
                        extension_id=extension.id,
                        version=semver.Version.parse(ver["version"]),
                        last_updated=ver["lastUpdated"],
                        target_platform=ver.get("targetPlatform"),
                    )
                    version_id = models.GalleryExtensionVersion.objects.filter(
                        extension_id=extension.id, version=version.version
                    )[:1].values("id")
                    update.versions.append(version)
                    for prop in ver.get("properties", []):
                        prop = models.GalleryExtensionProperty(
                            key=prop["key"],
                            value=prop["value"],
                            extension_version_id=version_id,
                        )
                        update.properties.append(prop)
                    for asset in ver.get("files", []):
                        if asset["assetType"] == query.AssetType.VSIX:
                            skip = False
                        asset = models.GalleryExtensionFile(
                            extension_version_id=version_id,
                            type=asset["assetType"],
                            source=asset["source"],
                            storage="vscode_marketplace",
                            file=ver["assetUri"] + "/" + asset["assetType"],
                        )
                    
                        update.assets.append(asset)
            update.update()
