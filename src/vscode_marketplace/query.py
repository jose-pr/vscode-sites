import re
from typing import Callable, Generator
from django.db.models import Avg, Q, QuerySet
from .typing.gallery import *
from . import models


def sort_extensions(sortOrder: SortOrder, sortBy: SortBy):
    statistic_name = None
    orderby = "_orderby"
    qs = models.GalleryExtension.annotated().prefetch_related(
        "publisher", "tags", "categories"
    )
    if sortBy is SortBy.AverageRating:
        statistic_name = "averagerating"
    elif sortBy is SortBy.InstallCount:
        statistic_name = "install"
    elif sortBy is SortBy.WeightedRating:
        statistic_name = "weightedRating"
    elif sortBy is SortBy.Title:
        orderby = "display_name"
    elif sortBy is SortBy.PublisherName:
        orderby = "publisher__display_name"
    elif sortBy is SortBy.PublishedDate:
        orderby = "published"
    elif sortBy is SortBy.LastUpdatedDate:
        qs = qs
    else:
        orderby = "name"

    if SortOrder.Descending is sortOrder:
        orderby = f"-{orderby}"
    if statistic_name:
        qs = qs.annotate(
            _orderby=Avg("statistic__value", filter=Q(name=statistic_name))
        )
    return qs.order_by(orderby)


def token_regex(token: str):
    return re.compile(
        r"\b" + token + r'("([^"]*)"|([^"]\S*))(\s+|\b|$)', flags=re.IGNORECASE
    )


def collect_filter_token(
    type: FilterType, token: re.Pattern, search: str, criteria: "list[GalleryCriterium]"
):
    def collect(match: re.Match):
        criteria.append({"filterType": type, "value": match[1]})
        return ""

    search = token.sub(collect, search)
    return search


CATEGORY_TOKEN = token_regex("category:")
TAG_TOKEN = token_regex("tag:")
TEXT_TOKEN = token_regex("")


def extension_filter(criterium: GalleryCriterium) -> None:
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
        criteria: "list[GalleryCriterium]" = []
        value = collect_filter_token(
            FilterType.Category, CATEGORY_TOKEN, value, criteria
        )
        value = collect_filter_token(FilterType.Tag, TAG_TOKEN, value, criteria)

        query = criteria_query(criteria)

        search_texts = [match[0] for match in TEXT_TOKEN.findall(value)]
        for text in search_texts:
            query = query.add(Q(description__icontains=text), Q.OR)
        return query

    elif type is FilterType.ExcludeWithFlags:
        flags = GalleryFlags(int(value))
        if GalleryFlags.Unpublished in flags:
            return Q()  # "unpublished" not in ext["flags"]

        else:
            return Q()


AND_FILTERS = [FilterType.Target, FilterType.Featured, FilterType.ExcludeWithFlags]


def criteria_query(criteria: "list[GalleryCriterium]"):
    query = Q()
    filters = [(extension_filter(c), FilterType(c["filterType"])) for c in criteria]
    for f in [f for f, type in filters if type not in AND_FILTERS and f is not None]:
        query.add(f, Q.OR)
    for f in [f for f, type in filters if type in AND_FILTERS and f is not None]:
        query.add(f, Q.AND)
    return query


def paged_extensions(
    criteria: "list[GalleryCriterium]" = None,
    page: int = 1,
    pageSize: int = 10,
    sortBy: SortBy = SortBy.NoneOrRelevance,
    sortOrder: SortOrder = SortOrder.Default,
) -> QuerySet[models.GalleryExtension]:
    start = ((page or 1) - 1) * pageSize
    end = start + pageSize
    sorted = sort_extensions(sortOrder, sortBy)
    if isinstance(criteria, str):
        criteria = [{"filterType": FilterType.SearchText, "value": criteria}]
    return (sorted.filter(criteria_query(criteria)) if criteria else sorted)[start:end]


def paged_extension_query(
    criteria: "list[GalleryCriterium]",
    flags: GalleryFlags,
    assetTypes: "list[str]",
    page: int = 1,
    pageSize: int = 10,
    sortBy: SortBy = SortBy.NoneOrRelevance,
    sortOrder: SortOrder = SortOrder.Default,
) -> Generator[GalleryExtension, None, "list[GalleryExtensionQueryResultMetadata]"]:
    start = ((page or 1) - 1) * pageSize
    end = start + pageSize
    cats = {}

    sorted = sort_extensions(sortOrder, sortBy)
    filtered = sorted.filter(criteria_query(criteria))
    extensions = [
        {"name": ext.name, "publisher": ext.publisher.name}
        for ext in filtered[start:end]
    ]
    return {
        "extensions": extensions,
        "resultMetadata": [
            {
                "metadataType": "ResultCount",
                "metadataItems": [
                    {"name": "TotalCount", "count": filtered.count()},
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
