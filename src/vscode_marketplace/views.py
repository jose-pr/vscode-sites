from io import StringIO
from django.http import HttpResponse, HttpRequest
from django.template import loader
import semver

from vscode_marketplace.typing.gallery import AssetType
from . import models, utils


def items(request: HttpRequest):
    uid = request.GET.get("itemName", None)
    if uid:
        extension = (
            models.GalleryExtension.objects.get_queryset().filter(uid=uid).first()
        )
        template = loader.get_template("vscode_marketplace/item.html")
        context = {"extension": extension}
    else:
        criteria = request.GET.get("searchText")
        extensions = models.GalleryExtension.query(criteria).page(page=1, page_size=10)
        template = loader.get_template("vscode_marketplace/items.html")
        context = {
            "extensions": extensions,
        }
    return HttpResponse(template.render(context, request))


import mimetypes

_MIMETYPE = mimetypes.MimeTypes(strict=False)
_MIMETYPE.readfp(
    StringIO(
        """
application/vsix				vsix
text/markdown                     md
"""
    )
)


_ASSET: dict[AssetType, str] = {
    AssetType.Manifest: "json",
    AssetType.Changelog: "txt",
    AssetType.Details: None,
    AssetType.Icon: "png",
    AssetType.License: None,
    AssetType.Repository: None,
    AssetType.VSIX: "vsix",
}


def assets_extensions(
    request, publisher: str, extension: str, version: semver, asset: str
):
    disposition = "inline"
    filename = f"{publisher}_{extension}_v{version}"

    ext = models.GalleryExtension.objects.get_queryset().filter(
        publisher__name=publisher, name=extension
    )[:1]
    vers = models.GalleryExtensionVersion.objects.filter(
        extension_id=ext.values("id"), version=version
    )[:1]

    suffix = _ASSET.get(asset)
    if suffix:
        filename = f"{filename}.{suffix}"
        default_mimetype = _MIMETYPE.guess_type(filename)[0]
    else:
        default_mimetype = None

    for _asset in models.GalleryExtensionFile.objects.filter(
        extension_version_id=vers.values("id"), type=asset
    ):
        if _asset.file:
            if _asset.source:
                source = utils.filename_from_url(_asset.source)
                mimetype = _MIMETYPE.guess_type(source)[0]
            try:
                response = HttpResponse(
                    _asset.file, content_type=mimetype or default_mimetype
                )
                response["Content-Disposition"] = f"{disposition}; filename={filename}"
                return response
            except Exception as _e:
                print(
                    f"Was not able to serve file: {_asset.file} from storage:{_asset.storage}"
                )

