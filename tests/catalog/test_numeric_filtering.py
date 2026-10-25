from decimal import Decimal

import pytest

from shop.models import (
    AnimalType,
    Category,
    ProductVariantAttribute,
    Product,
    ProductAttribute,
)
from shop.services.variant_attribute_sync import (
    ensure_attribute_for_all_product_variants,
)
from shop.filters.catalog import apply_catalog_filters
from shop.filters.query_param_validation import (
    CatalogFilterParams,
    NumericAttributeFilter,
    SelectAttributeFilter,
)

pytestmark = pytest.mark.django_db


def test_partial_save_updates_numeric_canonical_fields(
    make_product,
    make_variant,
    weight_attribute,
):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )
    product = make_product(
        name="Product",
        category=category,
    )
    variant = make_variant(
        product=product,
        price=Decimal("500.00"),
    )
    variant_attribute = ProductVariantAttribute.objects.create(
        variant=variant,
        attribute=weight_attribute,
        value_numeric=Decimal("10"),
        unit="kg",
    )
    assert variant_attribute.value_numeric_base == Decimal("10000.000")
    assert variant_attribute.base_unit == "g"

    variant_attribute.value_numeric = Decimal("500")
    variant_attribute.unit = "g"

    variant_attribute.save(
        update_fields=["value_numeric", "unit"],
    )

    variant_attribute.refresh_from_db()

    assert variant_attribute.value_numeric == Decimal("500.000")
    assert variant_attribute.unit == "g"
    assert variant_attribute.value_numeric_base == Decimal("500.000")
    assert variant_attribute.base_unit == "g"


def test_variant_attribute_sync_updates_numeric_canonical_fields(
    make_product,
    make_variant,
    weight_attribute,
):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )
    product = make_product(
        name="Product",
        category=category,
    )
    source_variant = make_variant(
        product=product,
        price=Decimal("500.00"),
    )
    target_variant = make_variant(
        product=product,
        price=Decimal("600.00"),
    )
    source_attribute = ProductVariantAttribute.objects.create(
        variant=source_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("10"),
        unit="kg",
    )
    target_attribute = ProductVariantAttribute.objects.create(
        variant=target_variant,
        attribute=weight_attribute,
    )
    ensure_attribute_for_all_product_variants(source_attribute)

    target_attribute.refresh_from_db()

    assert target_attribute.value_numeric == Decimal("10.000")
    assert target_attribute.unit == "kg"
    assert target_attribute.value_numeric_base == Decimal("10000.000")
    assert target_attribute.base_unit == "g"


def test_variant_attribute_bulk_copy_recalculates_numeric_canonical_fields(
    make_product,
    make_variant,
    weight_attribute,
):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )

    product = make_product(
        name="Product",
        category=category,
    )

    source_variant = make_variant(
        product=product,
        price=Decimal("500.00"),
    )
    target_variant = make_variant(
        product=product,
        price=Decimal("600.00"),
    )

    source_attribute = ProductVariantAttribute.objects.create(
        variant=source_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("10"),
        unit="kg",
    )

    ProductVariantAttribute.objects.filter(
        pk=source_attribute.pk,
    ).update(
        value_numeric_base=None,
        base_unit="",
    )

    source_attribute.refresh_from_db()

    ensure_attribute_for_all_product_variants(source_attribute)

    target_attribute = ProductVariantAttribute.objects.get(
        variant=target_variant,
        attribute=weight_attribute,
    )

    assert target_attribute.value_numeric == Decimal("10.000")
    assert target_attribute.unit == "kg"
    assert target_attribute.value_numeric_base == Decimal("10000.000")
    assert target_attribute.base_unit == "g"


def test_numeric_filter_uses_canonical_units(
    make_product,
    make_variant,
    weight_attribute,
):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )
    matching_product = make_product(
        name="Matching Product",
        category=category,
    )
    too_light_product = make_product(
        name="Too Light Product",
        category=category,
    )
    matching_variant = make_variant(
        product=matching_product,
        price=Decimal("500.00"),
    )
    too_light_variant = make_variant(
        product=too_light_product,
        price=Decimal("500.00"),
    )
    ProductVariantAttribute.objects.create(
        variant=matching_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("7500"),
        unit="g",
    )
    ProductVariantAttribute.objects.create(
        variant=too_light_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("4000"),
        unit="g",
    )

    params = CatalogFilterParams(
        numeric_attributes=(
            NumericAttributeFilter(
                attribute_slug="weight",
                min_value=Decimal("5"),
                max_value=Decimal("10"),
                unit="kg",
            ),
        ),
    )

    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )

    assert list(queryset) == [matching_product]


def test_numeric_filter_supports_min_only(
    make_product,
    make_variant,
    weight_attribute,
):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )

    matching_product = make_product(
        name="Matching Product",
        category=category,
    )
    too_light_product = make_product(
        name="Too Light Product",
        category=category,
    )

    matching_variant = make_variant(
        product=matching_product,
        price=Decimal("500.00"),
    )
    too_light_variant = make_variant(
        product=too_light_product,
        price=Decimal("500.00"),
    )

    ProductVariantAttribute.objects.create(
        variant=matching_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("7500"),
        unit="g",
    )
    ProductVariantAttribute.objects.create(
        variant=too_light_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("4000"),
        unit="g",
    )

    params = CatalogFilterParams(
        numeric_attributes=(
            NumericAttributeFilter(
                attribute_slug="weight",
                min_value=Decimal("5"),
                unit="kg",
            ),
        ),
    )

    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )

    assert list(queryset) == [matching_product]


def test_numeric_filter_supports_max_only(
    make_product,
    make_variant,
    weight_attribute,
):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )

    matching_product = make_product(
        name="Matching Product",
        category=category,
    )
    too_heavy_product = make_product(
        name="Too Heavy Product",
        category=category,
    )

    matching_variant = make_variant(
        product=matching_product,
        price=Decimal("500.00"),
    )
    too_heavy_variant = make_variant(
        product=too_heavy_product,
        price=Decimal("500.00"),
    )

    ProductVariantAttribute.objects.create(
        variant=matching_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("7500"),
        unit="g",
    )
    ProductVariantAttribute.objects.create(
        variant=too_heavy_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("12000"),
        unit="g",
    )

    params = CatalogFilterParams(
        numeric_attributes=(
            NumericAttributeFilter(
                attribute_slug="weight",
                max_value=Decimal("10"),
                unit="kg",
            ),
        ),
    )

    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )

    assert list(queryset) == [matching_product]


def test_select_and_numeric_filters_must_match_same_variant(
    make_product,
    make_variant,
    make_select_variant_attribute,
    flavor_attribute,
    flavor_values,
    weight_attribute,
):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )

    duck, chicken, _ = flavor_values

    split_product = make_product(
        name="Split Product",
        category=category,
    )

    split_variant_a = make_variant(
        product=split_product,
        price=Decimal("500.00"),
    )
    split_variant_b = make_variant(
        product=split_product,
        price=Decimal("600.00"),
    )

    make_select_variant_attribute(
        variant=split_variant_a,
        attribute=flavor_attribute,
        value=duck,
    )
    ProductVariantAttribute.objects.create(
        variant=split_variant_a,
        attribute=weight_attribute,
        value_numeric=Decimal("4000"),
        unit="g",
    )

    make_select_variant_attribute(
        variant=split_variant_b,
        attribute=flavor_attribute,
        value=chicken,
    )
    ProductVariantAttribute.objects.create(
        variant=split_variant_b,
        attribute=weight_attribute,
        value_numeric=Decimal("7500"),
        unit="g",
    )

    matching_product = make_product(
        name="Matching Product",
        category=category,
    )
    matching_variant = make_variant(
        product=matching_product,
        price=Decimal("500.00"),
    )

    make_select_variant_attribute(
        variant=matching_variant,
        attribute=flavor_attribute,
        value=duck,
    )
    ProductVariantAttribute.objects.create(
        variant=matching_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("7500"),
        unit="g",
    )

    params = CatalogFilterParams(
        select_attributes=(
            SelectAttributeFilter(
                attribute_slug="flavor",
                value_slugs=("duck",),
            ),
        ),
        numeric_attributes=(
            NumericAttributeFilter(
                attribute_slug="weight",
                min_value=Decimal("5"),
                max_value=Decimal("10"),
                unit="kg",
            ),
        ),
    )

    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )

    assert list(queryset) == [matching_product]


def test_inactive_variant_cannot_satisfy_numeric_filter(
    make_product,
    make_variant,
    weight_attribute,
):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )

    matching_product = make_product(
        name="Matching Product",
        category=category,
    )
    inactive_match_product = make_product(
        name="Inactive Match Product",
        category=category,
    )

    matching_variant = make_variant(
        product=matching_product,
        price=Decimal("500.00"),
        is_active=True,
    )

    inactive_variant = make_variant(
        product=inactive_match_product,
        price=Decimal("500.00"),
        is_active=False,
    )

    ProductVariantAttribute.objects.create(
        variant=matching_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("7500"),
        unit="g",
    )

    ProductVariantAttribute.objects.create(
        variant=inactive_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("7500"),
        unit="g",
    )

    params = CatalogFilterParams(
        numeric_attributes=(
            NumericAttributeFilter(
                attribute_slug="weight",
                min_value=Decimal("5"),
                max_value=Decimal("10"),
                unit="kg",
            ),
        ),
    )

    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )

    assert list(queryset) == [matching_product]


def test_multiple_numeric_attributes_must_match_same_variant(
    make_product,
    make_variant,
    weight_attribute,
):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )

    volume_attribute = ProductAttribute.objects.create(
        name="Volume",
        slug="volume",
        type=ProductAttribute.AttributeType.NUMERIC,
        available_units=["ml", "l"],
        filterable=True,
    )

    split_product = make_product(
        name="Split Product",
        category=category,
    )

    variant_a = make_variant(
        product=split_product,
        price=Decimal("500.00"),
    )
    variant_b = make_variant(
        product=split_product,
        price=Decimal("600.00"),
    )

    ProductVariantAttribute.objects.create(
        variant=variant_a,
        attribute=weight_attribute,
        value_numeric=Decimal("7500"),
        unit="g",
    )
    ProductVariantAttribute.objects.create(
        variant=variant_a,
        attribute=volume_attribute,
        value_numeric=Decimal("500"),
        unit="ml",
    )

    ProductVariantAttribute.objects.create(
        variant=variant_b,
        attribute=weight_attribute,
        value_numeric=Decimal("3000"),
        unit="g",
    )
    ProductVariantAttribute.objects.create(
        variant=variant_b,
        attribute=volume_attribute,
        value_numeric=Decimal("1500"),
        unit="ml",
    )

    matching_product = make_product(
        name="Matching Product",
        category=category,
    )
    matching_variant = make_variant(
        product=matching_product,
        price=Decimal("500.00"),
    )

    ProductVariantAttribute.objects.create(
        variant=matching_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("7500"),
        unit="g",
    )
    ProductVariantAttribute.objects.create(
        variant=matching_variant,
        attribute=volume_attribute,
        value_numeric=Decimal("1500"),
        unit="ml",
    )

    params = CatalogFilterParams(
        numeric_attributes=(
            NumericAttributeFilter(
                attribute_slug="weight",
                min_value=Decimal("5"),
                max_value=Decimal("10"),
                unit="kg",
            ),
            NumericAttributeFilter(
                attribute_slug="volume",
                min_value=Decimal("1"),
                max_value=Decimal("2"),
                unit="l",
            ),
        ),
    )

    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )

    assert list(queryset) == [matching_product]
