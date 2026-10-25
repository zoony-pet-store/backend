from decimal import Decimal
from uuid import UUID

import pytest
from django.http import QueryDict
from rest_framework.exceptions import ValidationError

from shop.filters.query_param_validation import (
    SelectAttributeFilter,
    NumericAttributeFilter,
    validate_catalog_filter_params,
)


def test_rating_min_is_parsed_as_decimal():
    query_params = QueryDict("rating_min=4")

    params = validate_catalog_filter_params(query_params)

    assert params.rating_min == Decimal("4")


def test_price_min_preserves_decimal_precision():
    query_params = QueryDict("price_min=500.50")

    params = validate_catalog_filter_params(query_params)

    assert params.price_min == Decimal("500.50")


def test_in_stock_true_is_parsed_as_boolean():
    query_params = QueryDict("in_stock=true")

    params = validate_catalog_filter_params(query_params)

    assert params.in_stock is True


def test_in_stock_false_is_parsed_as_boolean():
    query_params = QueryDict("in_stock=false")

    params = validate_catalog_filter_params(query_params)

    assert params.in_stock is False


def test_in_stock_rejects_invalid_boolean():
    query_params = QueryDict("in_stock=abc")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert str(exc_info.value.detail["in_stock"]) == "Must be either 'true' or 'false'."


def test_price_min_cannot_be_greater_than_price_max():
    query_params = QueryDict("price_min=500.50&price_max=400.70")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "price_min" in exc_info.value.detail


def test_rating_min_cannot_be_greater_than_rating_max():
    query_params = QueryDict("rating_min=5.5&rating_max=4.7")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "rating_min" in exc_info.value.detail


def test_invalid_decimal_is_rejected():
    query_params = QueryDict("price_min=abc")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "price_min" in exc_info.value.detail


def test_price_min_can_be_used_without_price_max():
    query_params = QueryDict("price_min=500")

    params = validate_catalog_filter_params(query_params)

    assert params.price_min == Decimal("500")
    assert params.price_max is None


def test_price_max_can_be_used_without_price_min():
    query_params = QueryDict("price_max=1000")

    params = validate_catalog_filter_params(query_params)

    assert params.price_min is None
    assert params.price_max == Decimal("1000")


def test_empty_query_params_returns_empty_filter_values():
    query_params = QueryDict("")

    params = validate_catalog_filter_params(query_params)

    assert params.select_attributes == ()
    assert params.numeric_attributes == ()
    assert params.animal_type is None
    assert params.category is None
    assert params.brands == ()
    assert params.price_min is None
    assert params.price_max is None
    assert params.rating_min is None
    assert params.rating_max is None
    assert params.in_stock is None


@pytest.mark.parametrize(
    "value",
    ["NaN", "Infinity", "-Infinity"],
)
def test_non_finite_decimal_is_rejected(value):
    query_params = QueryDict(f"price_min={value}")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert str(exc_info.value.detail["price_min"]) == "Must be a finite number."


def test_animal_type_is_slug():
    query_params = QueryDict("animal_type=dogs")

    params = validate_catalog_filter_params(query_params)

    assert params.animal_type == "dogs"


def test_category_is_parsed_as_uuid():
    category_id = "550e8400-e29b-41d4-a716-446655440000"
    query_params = QueryDict(f"category={category_id}")

    params = validate_catalog_filter_params(query_params)

    assert params.category == UUID(category_id)


def test_invalid_category_is_rejected():
    query_params = QueryDict("category=abc")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "category" in exc_info.value.detail


def test_multiple_brands_parsed_from_comma_separated_value():
    query_params = QueryDict("brand=royal-canin,brit,acana")

    params = validate_catalog_filter_params(query_params)

    assert params.brands == ("royal-canin", "brit", "acana")


def test_missing_brand_return_empty_tuple():
    query_params = QueryDict("")

    params = validate_catalog_filter_params(query_params)

    assert params.brands == ()


@pytest.mark.parametrize(
    ("query_string", "param_name"),
    [
        ("animal_type=", "animal_type"),
        ("brand=", "brand"),
        ("brand=royal-canin,,brit", "brand"),
    ],
)
def test_empty_slug_values_are_rejected(query_string, param_name):
    query_params = QueryDict(query_string)

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert param_name in exc_info.value.detail


def test_brand_values_stripped_and_deduplicated():
    query_params = QueryDict("brand=royal-canin,%20brit,royal-canin")
    params = validate_catalog_filter_params(query_params)

    assert params.brands == ("royal-canin", "brit")


def test_slug_format_is_rejected():
    query_params = QueryDict("animal_type=dogs!")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "animal_type" in exc_info.value.detail


def test_select_attribute_filter_is_parsed(flavor_values):
    query_params = QueryDict("attr.flavor=duck,chicken")

    params = validate_catalog_filter_params(query_params)

    assert params.select_attributes == (
        SelectAttributeFilter(
            attribute_slug="flavor",
            value_slugs=("duck", "chicken"),
        ),
    )


def test_numeric_attribute_filter_is_parsed(weight_attribute):
    query_params = QueryDict("attr.weight.min=5&attr.weight.max=7&attr.weight.unit=kg")

    params = validate_catalog_filter_params(query_params)

    assert params.numeric_attributes == (
        NumericAttributeFilter(
            attribute_slug="weight",
            min_value=Decimal("5"),
            max_value=Decimal("7"),
            unit="kg",
        ),
    )


def test_numeric_attribute_min_cannot_be_greater_than_max():
    query_params = QueryDict(
        "attr.weight.min=10" "&attr.weight.max=2" "&attr.weight.unit=kg"
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "attr.weight.min" in exc_info.value.detail


def test_numeric_attribute_range_requires_unit():
    query_params = QueryDict("attr.weight.min=5" "&attr.weight.max=7")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "attr.weight.unit" in exc_info.value.detail


@pytest.mark.django_db
def test_unknown_attribute_is_rejected():
    query_params = QueryDict("attr.unknown=some-value")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "attr.unknown" in exc_info.value.detail


def test_select_syntax_is_rejected_for_numeric_attribute(weight_attribute):
    query_params = QueryDict("attr.weight=large")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "attr.weight" in exc_info.value.detail


def test_numeric_syntax_is_rejected_for_select_attribute(flavor_attribute):
    query_params = QueryDict("attr.flavor.min=5&attr.flavor.unit=kg")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "attr.flavor" in exc_info.value.detail


def test_unknown_select_value_is_rejected(flavor_values):
    query_params = QueryDict("attr.flavor=duck,nonexistent-flavor")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "attr.flavor" in exc_info.value.detail


def test_unsupported_numeric_unit_is_rejected(weight_attribute):
    query_params = QueryDict("attr.weight.min=5&attr.weight.unit=ml")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "attr.weight.unit" in exc_info.value.detail


def test_non_filterable_attribute_is_rejected(non_filterable_attribute):
    query_params = QueryDict("attr.internal-code=test")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "attr.internal-code" in exc_info.value.detail


def test_numeric_attribute_unit_without_range_is_rejected(weight_attribute):
    query_params = QueryDict("attr.weight.unit=kg")

    with pytest.raises(ValidationError) as exc_info:
        validate_catalog_filter_params(query_params)

    assert "attr.weight" in exc_info.value.detail


def test_select_and_numeric_attributes_can_be_used_together(
    flavor_values, weight_attribute
):
    query_params = QueryDict(
        "attr.flavor=duck&attr.weight.min=5&attr.weight.max=10&attr.weight.unit=kg"
    )

    params = validate_catalog_filter_params(query_params)

    assert params.select_attributes == (
        SelectAttributeFilter(
            attribute_slug="flavor",
            value_slugs=("duck",),
        ),
    )
    assert params.numeric_attributes == (
        NumericAttributeFilter(
            attribute_slug="weight",
            min_value=Decimal("5"),
            max_value=Decimal("10"),
            unit="kg",
        ),
    )
