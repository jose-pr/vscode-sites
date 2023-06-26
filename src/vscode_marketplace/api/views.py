from io import StringIO
import json
from django.http import HttpRequest, HttpResponse
from ..typing.gallery import (
    GalleryFlags,
    GalleryQueryResult,
    SortBy,
    SortOrder,
    GalleryExtension,
    GalleryCriterium,
    AssetType,
    GalleryExtensionQueryResult,
)
from .. import models
from .utils import simple_query


def paged_extension_query(
    criteria: "list[GalleryCriterium]",
    flags: GalleryFlags,
    assetTypes: "list[AssetType]",
    page: int = 1,
    pageSize: int = 10,
    sortBy: SortBy = SortBy.NoneOrRelevance,
    sortOrder: SortOrder = SortOrder.Default,
) -> GalleryExtensionQueryResult:
    qs = models.GalleryExtension.query(criteria, sortBy, sortOrder)
    extensions = [
        {"name": ext.name, "publisher": ext.publisher.name}
        for ext in qs.page(page, pageSize)
    ]
    return {
        "extensions": extensions,
        "resultMetadata": [
            {
                "metadataType": "ResultCount",
                "metadataItems": [
                    {"name": "TotalCount", "count": qs.count()},
                ],
            },
            #  {
            #      "metadataType": "Categories",
            #      "metadataItems": [
            #          {"name": cat, "count": count} for cat, count in cats.items()
            #      ],
            #  },
        ],
    }


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@csrf_exempt
@require_http_methods(["GET", "POST"])
def extensionquery(request: HttpRequest):
    method = request.method.lower()
    if method == "post":
        _query = json.loads(request.body)
    else:
        _query = simple_query(request.GET.get("searchText"))
    flags = GalleryFlags(_query["flags"])
    assetTypes = _query["assetTypes"]

    result: GalleryQueryResult = {"results": []}

    for filter in _query["filters"]:
        result["results"].append(
            paged_extension_query(
                filter["criteria"],
                flags,
                assetTypes,
                filter["pageNumber"],
                filter["pageSize"],
                SortBy(filter["sortBy"]),
                SortOrder(filter["sortOrder"]),
            )
        )
    resp = HttpResponse(
        json.dumps(result), content_type="application/json;api-version=3.0-preview.1"
    )
    return resp



from rest_framework import viewsets
from . import serializers


class GalleryExtensionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A simple ViewSet for viewing accounts.
    """
    queryset = models.GalleryExtension.objects.get_queryset().all()
    serializer_class = serializers.ExtensionSerializer
