from io import StringIO
from pathlib import Path
from urllib.parse import unquote, urlparse
from django.http import HttpResponse, HttpRequest
from django.template import loader

import mimetypes

import semver

from . import models, query
from .typing.gallery import (
    AssetType,
    GalleryFlags,
    GalleryQueryResult,
    SortBy,
    SortOrder,
)


def items(request: HttpRequest):
    uid = request.GET.get("itemName", None)
    if uid:
        extension = models.GalleryExtension.annotated().filter(uid=uid).first()
        template = loader.get_template("vscode_marketplace/item.html")
        context = {"extension": extension}
        print(extension.versions.count())
    else:
        criteria = request.GET.get('searchText')
        filter = {
            'pageSize': 10,
            'page': 1,
        }
        extensions = query.paged_extensions(criteria, **filter)  
        template = loader.get_template("vscode_marketplace/items.html")
        context = {
            "extensions": extensions,
        }
    return HttpResponse(template.render(context, request))


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
    AssetType.Icon: None,
    AssetType.License: None,
    AssetType.Repository: None,
    AssetType.VSIX: "vsix",
}
import json

ACCESS_CONTROL_ALLOW_ORIGIN = "access-control-allow-origin"
ACCESS_CONTROL_EXPOSE_HEADERS = "access-control-expose-headers"
ACCESS_CONTROL_ALLOW_CREDENTIALS = "access-control-allow-credentials"
ACCESS_CONTROL_ALLOW_HEADERS = "access-control-allow-headers"
ACCESS_CONTROL_ALLOW_METHODS = "access-control-allow-methods"
ACCESS_CONTROL_MAX_AGE = "access-control-max-age"
ACCESS_CONTROL_REQUEST_PRIVATE_NETWORK = "access-control-request-private-network"
ACCESS_CONTROL_ALLOW_PRIVATE_NETWORK = "access-control-allow-private-network"

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt 
def extensionquery(request: HttpRequest):
    method = request.method.lower()
    origin = request.headers.get("origin")
    if method == "options":
        response = HttpResponse(headers={"content-length": "0"})
        response[ACCESS_CONTROL_ALLOW_ORIGIN] = origin
        response[ACCESS_CONTROL_ALLOW_HEADERS] = request.headers[
            "Access-Control-Request-Headers"
        ]
        response[ACCESS_CONTROL_ALLOW_METHODS] = request.headers[
            "Access-Control-Request-Method"
        ]
        return response

    elif method == "post":
        _query = json.loads(request.body)
    else:
        _query = query.simple_query(request.GET.get("searchText"))
    flags = GalleryFlags(_query["flags"])
    assetTypes = _query["assetTypes"]

    result: GalleryQueryResult = {"results": []}

    for filter in _query["filters"]:
        result["results"].append(
            query.paged_extension(
                filter["criteria"],
                flags,
                assetTypes,
                filter["pageNumber"],
                filter["pageSize"],
                SortBy(filter["sortBy"]),
                SortOrder(filter["sortOrder"]),
            )
        )
    resp = HttpResponse(json.dumps(result), content_type="application/json;api-version=3.0-preview.1")
    resp[ACCESS_CONTROL_ALLOW_ORIGIN] = origin
    resp[ACCESS_CONTROL_ALLOW_METHODS] = method.upper()
    return resp

def filename_from_url(url: str):
    url_parsed = urlparse(url)
    file_path = unquote(Path(url_parsed.path).name)
    return file_path


def assets_extensions(
    request, publisher: str, extension: str, version: str, asset: str
):
    disposition = "inline"
    filename = f"{publisher}_{extension}_v{version}"

    ext = models.GalleryExtension.objects.filter(
        publisher__name=publisher, name=extension
    )[:1]
    vers = models.GalleryExtensionVersion.objects.filter(
        extension_id=ext.values("id"), version=semver.Version.parse(version)
    )[:1]

    suffix = _ASSET.get(asset)
    if suffix:
        filename = f"{filename}.{suffix}"
        default_mimetype = _MIMETYPE.guess_type(filename)[0]

    for _asset in models.GalleryExtensionFile.objects.filter(
        extension_version_id=vers.values("id"), type=asset
    ):
        if _asset.file:
            if _asset.source:
                source = filename_from_url(_asset.source)
                mimetype = _MIMETYPE.guess_type(source)[0]
            try:
                response = HttpResponse(
                    _asset.file, content_type=mimetype or default_mimetype
                )
                response["Content-Disposition"] = f"{disposition}; filename={filename}"
                return response
            except:
                print(
                    f"Was not able to serve file: {_asset.file} from storage:{_asset.storage}"
                )
