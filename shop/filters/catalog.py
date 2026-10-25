from uuid import UUID

from django.db.models import QuerySet, Exists, OuterRef

from shop.filters.query_param_validation import CatalogFilterParams
from shop.models import Product, Category, ProductVariant, ProductVariantAttribute
from shop.models.product_attribute import normalize_numeric_attribute_to_base


def get_matching_variants_queryset(
    params: CatalogFilterParams,
    queryset: QuerySet[ProductVariant] | None = None,
) -> QuerySet[ProductVariant]:
    if queryset is None:
        queryset = ProductVariant.objects.all()

    queryset = queryset.filter(is_active=True)

    if params.price_min is not None:
        queryset = queryset.filter(
            price__gte=params.price_min,
        )

    if params.price_max is not None:
        queryset = queryset.filter(
            price__lte=params.price_max,
        )

    if params.in_stock is True:
        queryset = queryset.filter(
            stock__gt=0,
        )

    if params.in_stock is False:
        queryset = queryset.filter(
            stock=0,
        )

    for select_filter in params.select_attributes:
        matching_attribute = ProductVariantAttribute.objects.filter(
            variant_id=OuterRef("pk"),
            attribute__slug=select_filter.attribute_slug,
            value__slug__in=select_filter.value_slugs,
        )

        queryset = queryset.filter(Exists(matching_attribute))

    for numeric_filter in params.numeric_attributes:
        min_value_base = None
        max_value_base = None
        base_unit = None

        if numeric_filter.min_value is not None:
            min_value_base, min_base_unit = normalize_numeric_attribute_to_base(
                value=numeric_filter.min_value,
                unit=numeric_filter.unit,
            )
            base_unit = min_base_unit

        if numeric_filter.max_value is not None:
            max_value_base, max_base_unit = normalize_numeric_attribute_to_base(
                value=numeric_filter.max_value,
                unit=numeric_filter.unit,
            )

            if base_unit is None:
                base_unit = max_base_unit

        matching_attribute = ProductVariantAttribute.objects.filter(
            variant_id=OuterRef("pk"),
            attribute__slug=numeric_filter.attribute_slug,
            base_unit=base_unit,
        )

        if min_value_base is not None:
            matching_attribute = matching_attribute.filter(
                value_numeric_base__gte=min_value_base,
            )

        if max_value_base is not None:
            matching_attribute = matching_attribute.filter(
                value_numeric_base__lte=max_value_base,
            )

        queryset = queryset.filter(Exists(matching_attribute))

    return queryset


def has_variant_filters(params: CatalogFilterParams) -> bool:
    return (
        params.price_min is not None
        or params.price_max is not None
        or params.in_stock is not None
        or bool(params.select_attributes)
        or bool(params.numeric_attributes)
    )


def apply_catalog_filters(
    queryset: QuerySet[Product],
    params: CatalogFilterParams,
) -> QuerySet[Product]:
    queryset = apply_product_level_filters(
        queryset=queryset,
        params=params,
    )

    if has_variant_filters(params):
        matching_variants = get_matching_variants_queryset(
            params=params,
            queryset=ProductVariant.objects.filter(
                product_id=OuterRef("pk"),
            ),
        )

        queryset = queryset.filter(Exists(matching_variants))

    return queryset


def apply_product_level_filters(
    queryset: QuerySet[Product],
    params: CatalogFilterParams,
) -> QuerySet[Product]:
    if params.animal_type is not None:
        queryset = queryset.filter(
            category__animal_type__slug=params.animal_type,
        )

    if params.brands:
        queryset = queryset.filter(
            brand__slug__in=params.brands,
        )

    if params.rating_min is not None:
        queryset = queryset.filter(
            rating__gte=params.rating_min,
        )

    if params.rating_max is not None:
        queryset = queryset.filter(
            rating__lte=params.rating_max,
        )

    if params.category is not None:
        category_ids = _get_category_subtree_ids(params.category)
        queryset = queryset.filter(
            category_id__in=category_ids,
        )

    return queryset


def _get_category_subtree_ids(category_id: UUID) -> tuple[UUID, ...]:
    category_ids = [category_id]
    seen_ids = {category_id}
    parent_ids = [category_id]

    while parent_ids:
        child_ids = list(
            Category.objects.filter(
                parent_id__in=parent_ids,
                is_active=True,
            ).values_list("id", flat=True)
        )

        new_child_ids = [child_id for child_id in child_ids if child_id not in seen_ids]

        if not new_child_ids:
            break

        category_ids.extend(new_child_ids)
        seen_ids.update(new_child_ids)
        parent_ids = new_child_ids

    return tuple(category_ids)
