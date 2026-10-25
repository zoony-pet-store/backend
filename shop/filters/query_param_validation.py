from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from uuid import UUID

from shop.models import ProductAttribute
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_slug
from django.http import QueryDict
from rest_framework.exceptions import ValidationError


@dataclass(frozen=True)
class SelectAttributeFilter:
    attribute_slug: str
    value_slugs: tuple[str, ...]


@dataclass(frozen=True)
class NumericAttributeFilter:
    attribute_slug: str
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    unit: str | None = None


@dataclass(frozen=True)
class CatalogFilterParams:
    animal_type: str | None = None
    category: UUID | None = None
    brands: tuple[str, ...] = ()

    rating_min: Decimal | None = None
    rating_max: Decimal | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    in_stock: bool | None = None

    select_attributes: tuple[SelectAttributeFilter, ...] = ()
    numeric_attributes: tuple[NumericAttributeFilter, ...] = ()


def validate_catalog_filter_params(query_params: QueryDict) -> CatalogFilterParams:
    animal_type = _parse_slug(query_params, "animal_type")
    category = _parse_uuid(query_params, "category")
    brands = _parse_comma_separated_slugs(query_params, "brand")
    rating_min = _parse_decimal(query_params, "rating_min")
    rating_max = _parse_decimal(query_params, "rating_max")
    price_min = _parse_decimal(query_params, "price_min")
    price_max = _parse_decimal(query_params, "price_max")
    in_stock = _parse_boolean(query_params, "in_stock")
    select_attributes, numeric_attributes = _parse_attribute_filters(query_params)

    _validate_range(
        min_value=rating_min,
        max_value=rating_max,
        min_param="rating_min",
        max_param="rating_max",
    )
    _validate_range(
        min_value=price_min,
        max_value=price_max,
        min_param="price_min",
        max_param="price_max",
    )

    _validate_attribute_filters(
        select_filters=select_attributes, numeric_filters=numeric_attributes
    )

    return CatalogFilterParams(
        animal_type=animal_type,
        category=category,
        brands=brands,
        rating_min=rating_min,
        rating_max=rating_max,
        price_min=price_min,
        price_max=price_max,
        in_stock=in_stock,
        select_attributes=select_attributes,
        numeric_attributes=numeric_attributes,
    )


def _validate_range(
    min_value: Decimal | None,
    max_value: Decimal | None,
    min_param: str,
    max_param: str,
) -> None:
    if min_value is None or max_value is None:
        return

    if min_value > max_value:
        raise ValidationError({min_param: f"Must be less or equal to {max_param}"})


def _parse_decimal(query_params: QueryDict, param_name: str) -> Decimal | None:
    value = query_params.get(param_name)

    if value is None:
        return None
    try:
        decimal_value = Decimal(value)
    except InvalidOperation:
        raise ValidationError({param_name: "Must be a valid decimal number."})

    if not decimal_value.is_finite():
        raise ValidationError({param_name: "Must be a finite number."})

    return decimal_value


def _parse_boolean(query_params: QueryDict, param_name: str) -> bool | None:
    value = query_params.get(param_name)
    if value is None:
        return None
    if value == "true":
        return True
    if value == "false":
        return False

    raise ValidationError({param_name: "Must be either 'true' or 'false'."})


def _parse_uuid(query_params: QueryDict, param_name: str) -> UUID | None:
    value = query_params.get(param_name)

    if value is None:
        return None

    try:
        return UUID(value)

    except ValueError:
        raise ValidationError({param_name: "Must be a valid UUID."})


def _parse_slug(query_params: QueryDict, param_name: str) -> str | None:
    value = query_params.get(param_name)

    if value is None:
        return None

    value = value.strip()

    if not value:
        raise ValidationError({param_name: "Must be not empty."})

    try:
        validate_slug(value)
    except DjangoValidationError:
        raise ValidationError({param_name: "Must be a valid slug."})

    return value


def _parse_comma_separated_slugs(
    query_params: QueryDict, param_name: str
) -> tuple[str, ...]:
    raw_value = query_params.get(param_name)

    if raw_value is None:
        return ()

    values = tuple(value.strip() for value in raw_value.split(","))

    if any(not value for value in values):
        raise ValidationError({param_name: "Must not contain empty values."})

    for value in values:
        try:
            validate_slug(value)
        except DjangoValidationError:
            raise ValidationError({param_name: f"'{value}' is not a valid slug."})

    return tuple(dict.fromkeys(values))


def _parse_attribute_filters(
    query_params: QueryDict,
) -> tuple[
    tuple[SelectAttributeFilter, ...],
    tuple[NumericAttributeFilter, ...],
]:
    select_filters: list[SelectAttributeFilter] = []
    numeric_parts: dict[str, set[str]] = {}

    for param_name in query_params.keys():
        if not param_name.startswith("attr."):
            continue

        parts = param_name.split(".")

        if len(parts) not in (2, 3):
            raise ValidationError({param_name: "Invalid attribute filter format."})

        attribute_slug = parts[1]

        if not attribute_slug:
            raise ValidationError({param_name: "Attribute slug must not be empty."})

        try:
            validate_slug(attribute_slug)
        except DjangoValidationError:
            raise ValidationError({param_name: "Attribute slug must be a valid slug."})

        if len(parts) == 2:
            value_slugs = _parse_comma_separated_slugs(
                query_params,
                param_name,
            )

            select_filters.append(
                SelectAttributeFilter(
                    attribute_slug=attribute_slug,
                    value_slugs=value_slugs,
                )
            )
            continue

        operation = parts[2]

        if operation not in {"min", "max", "unit"}:
            raise ValidationError(
                {param_name: "Unsupported numeric attribute operation."}
            )

        numeric_parts.setdefault(attribute_slug, set()).add(operation)

    numeric_filters: list[NumericAttributeFilter] = []

    for attribute_slug, operations in numeric_parts.items():
        min_param = f"attr.{attribute_slug}.min"
        max_param = f"attr.{attribute_slug}.max"
        unit_param = f"attr.{attribute_slug}.unit"

        min_value = (
            _parse_decimal(query_params, min_param) if "min" in operations else None
        )
        max_value = (
            _parse_decimal(query_params, max_param) if "max" in operations else None
        )
        unit = _parse_slug(query_params, unit_param) if "unit" in operations else None

        if unit is None:
            raise ValidationError(
                {unit_param: "Unit is required for numeric attribute filters."}
            )

        if min_value is None and max_value is None:
            raise ValidationError(
                {
                    f"attr.{attribute_slug}": "Numeric attribute filter requires min or max."
                }
            )

        _validate_range(
            min_value=min_value,
            max_value=max_value,
            min_param=min_param,
            max_param=max_param,
        )

        numeric_filters.append(
            NumericAttributeFilter(
                attribute_slug=attribute_slug,
                min_value=min_value,
                max_value=max_value,
                unit=unit,
            )
        )

    return tuple(select_filters), tuple(numeric_filters)


def _validate_attribute_filters(
    select_filters: tuple[SelectAttributeFilter, ...],
    numeric_filters: tuple[NumericAttributeFilter, ...],
) -> None:
    requested_slugs = tuple(
        dict.fromkeys(
            [filter_.attribute_slug for filter_ in select_filters]
            + [filter_.attribute_slug for filter_ in numeric_filters]
        )
    )

    if not requested_slugs:
        return

    attributes = ProductAttribute.objects.filter(
        slug__in=requested_slugs
    ).prefetch_related("values")

    attributes_by_slug = {attribute.slug: attribute for attribute in attributes}

    for attribute_slug in requested_slugs:
        attribute = attributes_by_slug.get(attribute_slug)

        if attribute is None:
            raise ValidationError(
                {f"attr.{attribute_slug}": "Unknown product attribute."}
            )
        if not attribute.filterable:
            raise ValidationError(
                {
                    f"attr.{attribute_slug}": "This attribute cannot be used for filtering."
                }
            )

    for select_filter in select_filters:
        attribute = attributes_by_slug[select_filter.attribute_slug]

        if attribute.type != ProductAttribute.AttributeType.SELECT:
            raise ValidationError(
                {
                    f"attr.{select_filter.attribute_slug}": "This attribute does not support select filtering."
                }
            )

        available_value_slugs = {value.slug for value in attribute.values.all()}

        unknown_value_slugs = [
            value_slug
            for value_slug in select_filter.value_slugs
            if value_slug not in available_value_slugs
        ]

        if unknown_value_slugs:
            raise ValidationError(
                {
                    f"attr.{select_filter.attribute_slug}": "Unknown attribute value(s):"
                    + ", ".join(unknown_value_slugs)
                }
            )
    for numeric_filter in numeric_filters:
        attribute = attributes_by_slug[numeric_filter.attribute_slug]

        if attribute.type != ProductAttribute.AttributeType.NUMERIC:
            raise ValidationError(
                {
                    f"attr.{numeric_filter.attribute_slug}": "This attribute does not support numeric filtering."
                }
            )

        if numeric_filter.unit not in attribute.allowed_units:
            raise ValidationError(
                {
                    f"attr.{numeric_filter.attribute_slug}.unit": f"Unsupported unit '{numeric_filter.unit}'."
                }
            )
