import re
from ..typing.gallery import (
    VSCODE_INSTALLATION_TARGET,
    FilterType,
    GalleryCriterium,
    GalleryFlags,
    SortBy,
    SortOrder,
    GalleryExtensionQuery,
)
from django.db.models import Q

EXTENSION_FLAG_ALL = (
    GalleryFlags.IncludeStatistics
    | GalleryFlags.IncludeAssetUri
    | GalleryFlags.ExcludeNonValidated
    | GalleryFlags.IncludeVersionProperties
    | GalleryFlags.IncludeCategoryAndTags
    | GalleryFlags.IncludeFiles
    | GalleryFlags.IncludeVersions
)

EXTENSION_MINIMUM_FLAG = GalleryFlags.ExcludeNonValidated


def criterium_query(criterium: GalleryCriterium) -> Q:
    type = FilterType(criterium["filterType"])
    value = criterium["value"]
    if type is FilterType.Tag:
        value = value.lower()
        return Q(tags__name=value)
    elif type is FilterType.ExtensionId:
        value = value.lower()
        return Q(id=value)
    elif type is FilterType.Category:
        value = value
        return Q(categories__name=value)
    elif type is FilterType.ExtensionName:
        if "." in value:
            return Q(uid=value)
        else:
            return Q(name=value)
    elif type is FilterType.Target:
        value = value
        if value == VSCODE_INSTALLATION_TARGET:
            return Q()
        else:
            return Q(pk__in=[])
    elif type is FilterType.Featured:
        return Q()
    elif type is FilterType.SearchText:
        return (
            Q(description__icontains=value)
            | Q(name__icontains=value)
            | Q(publisher__name__icontains=value)
        )
    elif type is FilterType.ExcludeWithFlags:
        flags = GalleryFlags(int(value))
        if GalleryFlags.Unpublished in flags:
            return Q()  # "unpublished" not in ext["flags"]
        else:
            return Q()


def criteria_query(criteria: "list[GalleryCriterium]"):
    ors = []
    ands = []
    for f in criteria:
        type = FilterType(f["filterType"])
        if type is FilterType.SearchText:
            filters = GalleryCriterium.from_searchtext(f["value"])
        else:
            filters = [f]
        for f in filters:
            if type is None:
                continue
            q = criterium_query(f)
            if type in [
                FilterType.Target,
                FilterType.Featured,
                FilterType.ExcludeWithFlags,
            ]:
                ands.append(q)
            else:
                ors.append(q)
    query: Q = None
    for q in ors:
        if not query:
            query = q
        else:
            query |= q
    for q in ands:
        if not query:
            query = q
        else:
            query &= q
    if not query:
        query = Q(pk__in=[])
    return query


def simple_query(
    search: "str | list[GalleryCriterium]",
    page: int = 1,
    pageSize: int = 50,
    sortBy: SortBy = SortBy.NoneOrRelevance,
    sortOrder: SortOrder = SortOrder.Default,
    flags: GalleryFlags = GalleryFlags.IncludeStatistics
    | GalleryFlags.IncludeAssetUri
    | GalleryFlags.ExcludeNonValidated
    | GalleryFlags.IncludeVersionProperties
    | GalleryFlags.IncludeCategoryAndTags
    | GalleryFlags.IncludeFiles
    | GalleryFlags.IncludeVersions,
) -> GalleryExtensionQuery:
    return {
        "filters": [
            {
                "criteria": [
                    {
                        "filterType": FilterType.Target,
                        "value": VSCODE_INSTALLATION_TARGET,
                    },
                    {"filterType": FilterType.SearchText, "value": search},
                    {
                        "filterType": FilterType.ExcludeWithFlags,
                        "value": str(GalleryFlags.Unpublished),
                    },
                ]
                if isinstance(search, str)
                else search,
                "pageNumber": page,
                "pageSize": pageSize,
                "sortBy": sortBy,
                "sortOrder": sortOrder,
            }
        ],
        "assetTypes": [],
        "flags": flags,
    }
