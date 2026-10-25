from decimal import Decimal

import pytest

from shop.filters.catalog import apply_catalog_filters
from shop.filters.query_param_validation import (
    CatalogFilterParams,
    SelectAttributeFilter,
)
from shop.models import (
    AnimalType,
    Brand,
    Category,
    Product,
    ProductAttribute,
    ProductAttributeValue,
)

pytestmark = pytest.mark.django_db


def test_filters_products_by_animal_type(make_product):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )

    cats = AnimalType.objects.create(
        name="Cats",
        slug="cats",
    )

    dog_food = Category.objects.create(
        name="Dog Food",
        slug="dog-food",
        animal_type=dogs,
    )

    cat_food = Category.objects.create(
        name="Cat Food",
        slug="cat-food",
        animal_type=cats,
    )

    dog_product = make_product(
        name="Dog Product",
        category=dog_food,
    )

    make_product(
        name="Cat Product",
        category=cat_food,
    )

    params = CatalogFilterParams(
        animal_type="dogs",
    )

    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )

    assert list(queryset) == [dog_product]


def test_filters_products_by_multiple_brands(make_product):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )
    royal_canin = Brand.objects.create(
        name="Royal Canin",
        slug="royal-canin",
    )
    brit = Brand.objects.create(
        name="Brit",
        slug="brit",
    )
    acana = Brand.objects.create(
        name="Acana",
        slug="acana",
    )

    royal_product = make_product(
        name="Royal Product",
        category=category,
        brand=royal_canin,
    )
    brit_product = make_product(
        name="Brit Product",
        category=category,
        brand=brit,
    )
    make_product(
        name="Acana Product",
        category=category,
        brand=acana,
    )
    params = CatalogFilterParams(
        brands=("royal-canin", "brit"),
    )
    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )

    result = list(queryset)
    assert len(result) == 2
    assert set(result) == {
        royal_product,
        brit_product,
    }


def test_filters_products_by_rating_range(make_product):
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
        name="Matching",
        category=category,
        rating=Decimal("4.50"),
    )
    make_product(
        name="Too low",
        category=category,
        rating=Decimal("3.50"),
    )
    params = CatalogFilterParams(
        rating_min=Decimal("4.50"),
        rating_max=Decimal("5.50"),
    )
    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )
    assert list(queryset) == [matching_product]


def test_parent_category_includes_descendant_categories(make_product):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    food = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )
    dry_food = Category.objects.create(
        name="Dry food",
        slug="dry-food",
        animal_type=dogs,
        parent=food,
    )
    veterinary_food = Category.objects.create(
        name="Veterinary food",
        slug="veterinary-food",
        animal_type=dogs,
        parent=dry_food,
    )
    toys = Category.objects.create(
        name="Toys",
        slug="toys",
        animal_type=dogs,
    )

    root_product = make_product(
        name="Root Product",
        category=food,
    )
    child_product = make_product(
        name="Child Product",
        category=dry_food,
    )
    grandchild_product = make_product(
        name="Grandchild Product",
        category=veterinary_food,
    )

    make_product(
        name="Toys",
        category=toys,
    )
    params = CatalogFilterParams(
        category=food.id,
    )
    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )
    result = list(queryset)
    assert len(result) == 3
    assert set(result) == {
        root_product,
        child_product,
        grandchild_product,
    }


def test_filters_products_by_variant_price_range(make_product, make_variant):
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
    expensive_product = make_product(
        name="Expensive Product",
        category=category,
    )
    make_variant(product=matching_product, price=Decimal("600.00"), stock=5)
    make_variant(product=expensive_product, price=Decimal("1200.00"), stock=5)
    params = CatalogFilterParams(
        price_min=Decimal("500.00"),
        price_max=Decimal("700.00"),
    )
    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )
    assert list(queryset) == [matching_product]


def test_inactive_variant_cannot_satisfy_price_filter(make_product, make_variant):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )
    active_product = make_product(
        name="Activated Variant Product",
        category=category,
    )
    inactive_product = make_product(
        name="Inactive Variant Product",
        category=category,
    )
    make_variant(
        product=active_product,
        price=Decimal("600.00"),
        stock=5,
    )
    make_variant(
        product=inactive_product,
        price=Decimal("600.00"),
        stock=5,
        is_active=False,
    )
    params = CatalogFilterParams(
        price_min=Decimal("500.00"),
        price_max=Decimal("700.00"),
    )
    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )
    assert list(queryset) == [active_product]


def test_price_and_stock_must_match_same_variant(make_product, make_variant):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )
    split_match_product = make_product(
        name="Split Match",
        category=category,
    )
    make_variant(
        product=split_match_product,
        price=Decimal("400.00"),
        stock=0,
    )
    make_variant(
        product=split_match_product,
        price=Decimal("600.00"),
        stock=10,
    )
    matching_product = make_product(
        name="Real Match",
        category=category,
    )
    make_variant(
        product=matching_product,
        price=Decimal("400.00"),
        stock=10,
    )
    params = CatalogFilterParams(
        price_max=Decimal("500.00"),
        in_stock=True,
    )
    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )
    assert list(queryset) == [matching_product]


def test_product_is_not_duplicated_when_multiple_variants_match(
    make_product, make_variant
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
    make_variant(
        product=product,
        price=Decimal("400.00"),
        stock=5,
    )
    make_variant(
        product=product,
        price=Decimal("450.00"),
        stock=3,
    )
    params = CatalogFilterParams(
        price_max=Decimal("500.00"),
        in_stock=True,
    )
    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )
    assert list(queryset) == [product]


def test_in_stock_true_requires_positive_stock(
    make_product,
    make_variant,
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

    in_stock_product = make_product(
        name="In Stock",
        category=category,
    )
    out_of_stock_product = make_product(
        name="Out Of Stock",
        category=category,
    )

    make_variant(
        product=in_stock_product,
        price=Decimal("500.00"),
        stock=5,
    )
    make_variant(
        product=out_of_stock_product,
        price=Decimal("500.00"),
        stock=0,
    )

    params = CatalogFilterParams(
        in_stock=True,
    )

    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )

    assert list(queryset) == [in_stock_product]


def test_in_stock_false_requires_zero_stock(
    make_product,
    make_variant,
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

    in_stock_product = make_product(
        name="In Stock",
        category=category,
    )
    out_of_stock_product = make_product(
        name="Out Of Stock",
        category=category,
    )

    make_variant(
        product=in_stock_product,
        price=Decimal("500.00"),
        stock=5,
    )
    make_variant(
        product=out_of_stock_product,
        price=Decimal("500.00"),
        stock=0,
    )

    params = CatalogFilterParams(
        in_stock=False,
    )

    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )

    assert list(queryset) == [out_of_stock_product]


def test_filters_products_by_select_attribute(
    make_product,
    make_variant,
    make_select_variant_attribute,
    flavor_attribute,
    flavor_values,
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

    duck_product = make_product(
        name="Duck Product",
        category=category,
    )
    chicken_product = make_product(
        name="Chicken Product",
        category=category,
    )

    duck_variant = make_variant(
        product=duck_product,
        price=Decimal("500.00"),
    )
    chicken_variant = make_variant(
        product=chicken_product,
        price=Decimal("500.00"),
    )

    make_select_variant_attribute(
        variant=duck_variant,
        attribute=flavor_attribute,
        value=duck,
    )
    make_select_variant_attribute(
        variant=chicken_variant,
        attribute=flavor_attribute,
        value=chicken,
    )

    params = CatalogFilterParams(
        select_attributes=(
            SelectAttributeFilter(
                attribute_slug="flavor",
                value_slugs=("duck",),
            ),
        ),
    )

    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )

    assert list(queryset) == [duck_product]


def test_multiple_values_of_same_select_attribute_use_or(
    make_product,
    make_variant,
    make_select_variant_attribute,
    flavor_attribute,
    flavor_values,
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

    duck, chicken, beef = flavor_values

    duck_product = make_product(
        name="Duck Product",
        category=category,
    )
    chicken_product = make_product(
        name="Chicken Product",
        category=category,
    )
    beef_product = make_product(
        name="Beef Product",
        category=category,
    )

    duck_variant = make_variant(
        product=duck_product,
        price=Decimal("500.00"),
    )
    chicken_variant = make_variant(
        product=chicken_product,
        price=Decimal("500.00"),
    )
    beef_variant = make_variant(
        product=beef_product,
        price=Decimal("500.00"),
    )

    make_select_variant_attribute(
        variant=duck_variant,
        attribute=flavor_attribute,
        value=duck,
    )
    make_select_variant_attribute(
        variant=chicken_variant,
        attribute=flavor_attribute,
        value=chicken,
    )
    make_select_variant_attribute(
        variant=beef_variant,
        attribute=flavor_attribute,
        value=beef,
    )

    params = CatalogFilterParams(
        select_attributes=(
            SelectAttributeFilter(
                attribute_slug="flavor",
                value_slugs=("duck", "chicken"),
            ),
        ),
    )

    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )

    result = list(queryset)

    assert len(result) == 2
    assert set(result) == {
        duck_product,
        chicken_product,
    }


def test_different_select_attributes_must_match_same_variant(
    make_product,
    make_variant,
    make_select_variant_attribute,
    flavor_attribute,
    flavor_values,
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

    size_attribute = ProductAttribute.objects.create(
        name="Size",
        slug="size",
        type=ProductAttribute.AttributeType.SELECT,
        filterable=True,
    )

    small = ProductAttributeValue.objects.create(
        attribute=size_attribute,
        value="Small",
        slug="small",
    )
    large = ProductAttributeValue.objects.create(
        attribute=size_attribute,
        value="Large",
        slug="large",
    )

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
    make_select_variant_attribute(
        variant=split_variant_a,
        attribute=size_attribute,
        value=small,
    )

    make_select_variant_attribute(
        variant=split_variant_b,
        attribute=flavor_attribute,
        value=chicken,
    )
    make_select_variant_attribute(
        variant=split_variant_b,
        attribute=size_attribute,
        value=large,
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
    make_select_variant_attribute(
        variant=matching_variant,
        attribute=size_attribute,
        value=large,
    )

    params = CatalogFilterParams(
        select_attributes=(
            SelectAttributeFilter(
                attribute_slug="flavor",
                value_slugs=("duck",),
            ),
            SelectAttributeFilter(
                attribute_slug="size",
                value_slugs=("large",),
            ),
        ),
    )

    queryset = apply_catalog_filters(
        Product.objects.all(),
        params,
    )

    assert list(queryset) == [matching_product]
