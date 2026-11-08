from decimal import Decimal

import pytest

from shop.models import (
    AnimalType,
    Category,
    ProductVariantAttribute,
    ProductVariant,
    Brand,
    ProductImage,
    Badge,
)

pytestmark = pytest.mark.django_db


def test_catalog_filters_by_numeric_attribute(
    client,
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
        stock=5,
    )
    too_light_product_variant = make_variant(
        product=too_light_product,
        price=Decimal("500.00"),
        stock=5,
    )
    ProductVariantAttribute.objects.create(
        variant=matching_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("7500"),
        unit="g",
    )
    ProductVariantAttribute.objects.create(
        variant=too_light_product_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("4000"),
        unit="g",
    )

    response = client.get(
        "/api/catalog",
        {
            "attr.weight.min": "5",
            "attr.weight.max": "10",
            "attr.weight.unit": "kg",
        },
    )

    assert response.status_code == 200
    assert response.data["count"] == 1

    returned_variant_ids = {item["variant_id"] for item in response.data["results"]}

    assert returned_variant_ids == {str(matching_variant.id)}


def test_catalog_rejects_unsupported_numeric_unit(
    client,
    weight_attribute,
):
    response = client.get(
        "/api/catalog",
        {
            "attr.weight.min": "5",
            "attr.weight.unit": "ml",
        },
    )

    assert response.status_code == 400
    assert "attr.weight.unit" in response.data


def test_catalog_filters_by_select_attribute(
    client,
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

    matching_product = make_product(
        name="Duck Product",
        category=category,
    )
    non_matching_product = make_product(
        name="Chicken Product",
        category=category,
    )

    matching_variant = make_variant(
        product=matching_product,
        price=Decimal("500.00"),
    )
    non_matching_variant = make_variant(
        product=non_matching_product,
        price=Decimal("600.00"),
    )

    make_select_variant_attribute(
        variant=matching_variant,
        attribute=flavor_attribute,
        value=duck,
    )
    make_select_variant_attribute(
        variant=non_matching_variant,
        attribute=flavor_attribute,
        value=chicken,
    )

    response = client.get(
        "/api/catalog",
        {
            "attr.flavor": "duck",
        },
    )

    assert response.status_code == 200
    assert response.data["count"] == 1

    returned_variant_ids = {item["variant_id"] for item in response.data["results"]}

    assert returned_variant_ids == {str(matching_variant.id)}


def test_catalog_select_and_numeric_must_match_same_variant(
    client,
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

    response = client.get(
        "/api/catalog",
        {
            "attr.flavor": "duck",
            "attr.weight.min": "5",
            "attr.weight.max": "10",
            "attr.weight.unit": "kg",
        },
    )

    assert response.status_code == 200
    assert response.data["count"] == 1

    returned_variant_ids = {item["variant_id"] for item in response.data["results"]}

    assert returned_variant_ids == {str(matching_variant.id)}

    card = response.data["results"][0]

    assert card["product_id"] == str(matching_product.id)
    assert card["price"] == str(matching_variant.price)


def test_catalog_parent_category_includes_descendants(
    client,
    make_product,
    make_variant,
):
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
        name="Dry Food",
        slug="dry-food",
        animal_type=dogs,
        parent=food,
    )

    puppy_food = Category.objects.create(
        name="Puppy Food",
        slug="puppy-food",
        animal_type=dogs,
        parent=dry_food,
    )

    wet_food = Category.objects.create(
        name="Wet Food",
        slug="wet-food",
        animal_type=dogs,
        parent=food,
    )

    toys = Category.objects.create(
        name="Toys",
        slug="toys",
        animal_type=dogs,
    )

    puppy_product = make_product(
        name="Puppy Product",
        category=puppy_food,
    )

    wet_product = make_product(
        name="Wet Product",
        category=wet_food,
    )

    toy_product = make_product(
        name="Toy Product",
        category=toys,
    )

    for product in (puppy_product, wet_product, toy_product):
        make_variant(
            product=product,
            price=Decimal("500.00"),
        )

    response = client.get(
        "/api/catalog",
        {
            "category": str(food.id),
        },
    )

    assert response.status_code == 200
    assert response.data["count"] == 2

    returned_product_ids = {item["product_id"] for item in response.data["results"]}

    assert returned_product_ids == {
        str(puppy_product.id),
        str(wet_product.id),
    }


def test_catalog_orders_filtered_variants_by_product_name(
    client,
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

    alpha_product = make_product(
        name="Alpha Product",
        category=category,
    )
    zulu_product = make_product(
        name="Zulu Product",
        category=category,
    )
    excluded_product = make_product(
        name="Beta Product",
        category=category,
    )

    product_with_weight = (
        (alpha_product, Decimal("7500")),
        (zulu_product, Decimal("8000")),
        (excluded_product, Decimal("4000")),
    )

    for product, weight in product_with_weight:
        variant = make_variant(
            product=product,
            price=Decimal("500.00"),
        )
        ProductVariantAttribute.objects.create(
            variant=variant,
            attribute=weight_attribute,
            value_numeric=weight,
            unit="g",
        )

    response = client.get(
        "/api/catalog",
        {
            "attr.weight.min": "5",
            "attr.weight.unit": "kg",
            "ordering": "name",
        },
    )

    assert response.status_code == 200
    assert response.data["count"] == 2

    returned_product_ids = [item["product_id"] for item in response.data["results"]]

    assert returned_product_ids == [
        str(alpha_product.id),
        str(zulu_product.id),
    ]


def test_catalog_paginates_filtered_variants(
    client,
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

    variants = {}

    for name in ("Alpha", "Bravo", "Charlie", "Delta", "Echo"):
        product = make_product(
            name=name,
            category=category,
        )

        variant = make_variant(
            product=product,
            price=Decimal("500.00"),
        )

        ProductVariantAttribute.objects.create(
            variant=variant,
            attribute=weight_attribute,
            value_numeric=Decimal("7500"),
            unit="g",
        )

        variants[name] = variant

    excluded_product = make_product(
        name="Excluded",
        category=category,
    )
    excluded_variant = make_variant(
        product=excluded_product,
        price=Decimal("500.00"),
    )

    ProductVariantAttribute.objects.create(
        variant=excluded_variant,
        attribute=weight_attribute,
        value_numeric=Decimal("4000"),
        unit="g",
    )

    query_params = {
        "attr.weight.min": "5",
        "attr.weight.unit": "kg",
        "ordering": "name",
        "page_size": "2",
    }

    page_1 = client.get(
        "/api/catalog",
        {**query_params, "page": "1"},
    )

    page_2 = client.get(
        "/api/catalog",
        {**query_params, "page": "2"},
    )

    page_3 = client.get(
        "/api/catalog",
        {**query_params, "page": "3"},
    )

    assert page_1.status_code == 200
    assert page_2.status_code == 200
    assert page_3.status_code == 200

    assert page_1.data["count"] == 5
    assert page_2.data["count"] == 5
    assert page_3.data["count"] == 5

    assert [item["variant_id"] for item in page_1.data["results"]] == [
        str(variants["Alpha"].id),
        str(variants["Bravo"].id),
    ]

    assert [item["variant_id"] for item in page_2.data["results"]] == [
        str(variants["Charlie"].id),
        str(variants["Delta"].id),
    ]

    assert [item["variant_id"] for item in page_3.data["results"]] == [
        str(variants["Echo"].id),
    ]

    assert page_1.data["previous"] is None
    assert page_1.data["next"] is not None

    assert page_2.data["previous"] is not None
    assert page_2.data["next"] is not None

    assert page_3.data["previous"] is not None
    assert page_3.data["next"] is None


def test_products_api_returns_single_card_with_default_variant(
    client,
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

    product = make_product(
        name="Dog Food",
        category=category,
    )

    default_variant = make_variant(
        product=product,
        price=Decimal("500.00"),
        stock=0,
    )

    available_variant = make_variant(
        product=product,
        price=Decimal("700.00"),
        stock=5,
    )

    ProductVariant.objects.filter(
        product=product,
    ).update(is_default=False)

    ProductVariant.objects.filter(
        pk=default_variant.pk,
    ).update(is_default=True)

    response = client.get("/api/products")

    assert response.status_code == 200
    assert response.data["count"] == 1

    card = response.data["results"][0]

    assert card["id"] == str(product.id)
    assert card["default_variant_id"] == str(default_variant.id)
    assert card["price"] == "500.00"

    assert len(card["variants"]) == 2
    assert {variant["id"] for variant in card["variants"]} == {
        str(default_variant.id),
        str(available_variant.id),
    }


def test_catalog_returns_matching_variant_instead_of_default(
    client,
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

    product = make_product(
        name="Dog Food",
        category=category,
    )

    duck, chicken, _ = flavor_values

    duck_variant = make_variant(
        product=product,
        price=Decimal("500.00"),
        stock=0,
    )

    chicken_variant = make_variant(
        product=product,
        price=Decimal("700.00"),
        stock=5,
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

    ProductVariant.objects.filter(
        product=product,
    ).update(is_default=False)

    ProductVariant.objects.filter(
        pk=chicken_variant.pk,
    ).update(is_default=True)

    response = client.get(
        "/api/catalog",
        {
            "attr.flavor": "duck",
        },
    )

    assert response.status_code == 200
    assert response.data["count"] == 1

    card = response.data["results"][0]

    assert card["variant_id"] == str(duck_variant.id)
    assert card["product_id"] == str(product.id)
    assert card["price"] == str(duck_variant.price)
    assert card["in_stock"] is False


def test_catalog_returns_one_card_per_matching_variant(
    client,
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

    product = make_product(
        name="Dog Food",
        category=category,
    )

    duck, chicken, _ = flavor_values

    duck_variant_1 = make_variant(
        product=product,
        price=Decimal("500.00"),
        stock=5,
    )
    duck_variant_2 = make_variant(
        product=product,
        price=Decimal("700.00"),
        stock=3,
    )
    chicken_variant = make_variant(
        product=product,
        price=Decimal("900.00"),
        stock=10,
    )

    for variant, flavor in (
        (duck_variant_1, duck),
        (duck_variant_2, duck),
        (chicken_variant, chicken),
    ):
        make_select_variant_attribute(
            variant=variant,
            attribute=flavor_attribute,
            value=flavor,
        )

    response = client.get(
        "/api/catalog",
        {"attr.flavor": "duck"},
    )

    assert response.status_code == 200
    assert response.data["count"] == 2

    cards = response.data["results"]

    cards_by_variant_id = {card["variant_id"]: card for card in cards}

    assert set(cards_by_variant_id) == {
        str(duck_variant_1.id),
        str(duck_variant_2.id),
    }

    assert all(card["product_id"] == str(product.id) for card in cards)

    assert cards_by_variant_id[str(duck_variant_1.id)]["price"] == "500.00"
    assert cards_by_variant_id[str(duck_variant_2.id)]["price"] == "700.00"


def test_catalog_orders_matching_variants_by_price(
    client,
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

    product = make_product(
        name="Dog Food",
        category=category,
    )

    duck, chicken, _ = flavor_values

    expensive_variant = make_variant(
        product=product,
        price=Decimal("700.00"),
    )

    cheap_variant = make_variant(
        product=product,
        price=Decimal("500.00"),
    )

    excluded_variant = make_variant(
        product=product,
        price=Decimal("400.00"),
    )

    for variant in (expensive_variant, cheap_variant):
        make_select_variant_attribute(
            variant=variant,
            attribute=flavor_attribute,
            value=duck,
        )

    make_select_variant_attribute(
        variant=excluded_variant,
        attribute=flavor_attribute,
        value=chicken,
    )

    ascending_response = client.get(
        "/api/catalog",
        {
            "attr.flavor": "duck",
            "ordering": "price",
        },
    )

    descending_response = client.get(
        "/api/catalog",
        {
            "attr.flavor": "duck",
            "ordering": "-price",
        },
    )

    assert ascending_response.status_code == 200
    assert descending_response.status_code == 200

    assert ascending_response.data["count"] == 2
    assert descending_response.data["count"] == 2

    ascending_variant_ids = [
        card["variant_id"] for card in ascending_response.data["results"]
    ]
    descending_variant_ids = [
        card["variant_id"] for card in descending_response.data["results"]
    ]

    assert ascending_variant_ids == [
        str(cheap_variant.id),
        str(expensive_variant.id),
    ]

    assert descending_variant_ids == [
        str(expensive_variant.id),
        str(cheap_variant.id),
    ]


def test_catalog_paginates_variants_by_default(
    client,
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

    product = make_product(
        name="Dog Food",
        category=category,
    )

    variants = [
        make_variant(
            product=product,
            price=Decimal("100.00") + index,
            stock=1,
        )
        for index in range(21)
    ]

    query_params = {
        "ordering": "price",
    }

    page_1 = client.get(
        "/api/catalog",
        {**query_params, "page": "1"},
    )

    page_2 = client.get(
        "/api/catalog",
        {**query_params, "page": "2"},
    )

    assert page_1.status_code == 200
    assert page_1.data["count"] == 21
    assert len(page_1.data["results"]) == 20

    assert page_2.status_code == 200
    assert page_2.data["count"] == 21
    assert len(page_2.data["results"]) == 1

    page_1_variant_ids = [card["variant_id"] for card in page_1.data["results"]]

    page_2_variant_ids = [card["variant_id"] for card in page_2.data["results"]]

    assert page_1_variant_ids == [str(variant.id) for variant in variants[:20]]

    assert page_2_variant_ids == [str(variant.id) for variant in variants[20:]]

    assert page_1.data["previous"] is None
    assert page_1.data["next"] is not None

    assert page_2.data["previous"] is not None
    assert page_2.data["next"] is None


def test_catalog_excludes_inactive_variants(
    client,
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

    product = make_product(
        name="Dog Food",
        category=category,
    )

    duck, _, _ = flavor_values

    active_variant = make_variant(
        product=product,
        price=Decimal("700.00"),
        stock=5,
        is_active=True,
    )

    inactive_variant = make_variant(
        product=product,
        price=Decimal("400.00"),
        stock=10,
        is_active=False,
    )

    for variant in (active_variant, inactive_variant):
        make_select_variant_attribute(
            variant=variant,
            attribute=flavor_attribute,
            value=duck,
        )

    response = client.get(
        "/api/catalog",
        {
            "attr.flavor": "duck",
        },
    )

    assert response.status_code == 200
    assert response.data["count"] == 1

    card = response.data["results"][0]

    assert card["variant_id"] == str(active_variant.id)
    assert card["product_id"] == str(product.id)
    assert card["price"] == str(active_variant.price)


def test_catalog_price_and_stock_filters_match_same_variant(
    client,
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

    split_product = make_product(
        name="Split Product",
        category=category,
    )

    out_of_stock_variant = make_variant(
        product=split_product,
        price=Decimal("600.00"),
        stock=0,
    )

    expensive_variant = make_variant(
        product=split_product,
        price=Decimal("900.00"),
        stock=5,
    )

    matching_product = make_product(
        name="Matching Product",
        category=category,
    )

    matching_variant = make_variant(
        product=matching_product,
        price=Decimal("650.00"),
        stock=4,
    )

    response = client.get(
        "/api/catalog",
        {
            "price_min": "500",
            "price_max": "700",
            "in_stock": "true",
        },
    )

    assert response.status_code == 200
    assert response.data["count"] == 1

    results = response.data["results"]

    assert len(results) == 1

    card = results[0]

    assert card["variant_id"] == str(matching_variant.id)
    assert card["product_id"] == str(matching_product.id)
    assert card["price"] == str(matching_variant.price)
    assert card["in_stock"] is True


def test_catalog_filters_variants_by_animal_type_brand_and_rating(
    client,
    make_product,
    make_variant,
):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )
    cats = AnimalType.objects.create(
        name="Cats",
        slug="cats",
    )

    dog_category = Category.objects.create(
        name="Dog Food",
        slug="dog-food",
        animal_type=dogs,
    )
    cat_category = Category.objects.create(
        name="Cat Food",
        slug="cat-food",
        animal_type=cats,
    )

    royal_canin = Brand.objects.create(
        name="Royal Canin",
        slug="royal-canin",
    )
    brit = Brand.objects.create(
        name="Brit",
        slug="brit",
    )

    matching_product = make_product(
        name="Matching Dog Food",
        category=dog_category,
        brand=royal_canin,
        rating=Decimal("4.80"),
    )

    first_matching_variant = make_variant(
        product=matching_product,
        price=Decimal("500.00"),
        stock=5,
    )
    second_matching_variant = make_variant(
        product=matching_product,
        price=Decimal("700.00"),
        stock=3,
    )

    wrong_brand_product = make_product(
        name="Brit Dog Food",
        category=dog_category,
        brand=brit,
        rating=Decimal("4.80"),
    )

    wrong_rating_product = make_product(
        name="Low Rated Dog Food",
        category=dog_category,
        brand=royal_canin,
        rating=Decimal("3.50"),
    )

    wrong_animal_product = make_product(
        name="Royal Cat Food",
        category=cat_category,
        brand=royal_canin,
        rating=Decimal("4.80"),
    )

    for product in (
        wrong_brand_product,
        wrong_rating_product,
        wrong_animal_product,
    ):
        make_variant(
            product=product,
            price=Decimal("600.00"),
            stock=5,
        )

    response = client.get(
        "/api/catalog",
        {
            "animal_type": "dogs",
            "brand": "royal-canin",
            "rating_min": "4.5",
        },
    )

    assert response.status_code == 200
    assert response.data["count"] == 2

    results = response.data["results"]

    assert len(results) == 2

    returned_variant_ids = {card["variant_id"] for card in results}

    assert returned_variant_ids == {
        str(first_matching_variant.id),
        str(second_matching_variant.id),
    }

    assert all(card["product_id"] == str(matching_product.id) for card in results)


def test_catalog_variant_image_falls_back_to_product_image(
    client,
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

    product = make_product(
        name="Dog Food",
        category=category,
    )

    variant_with_image = make_variant(
        product=product,
        price=Decimal("500.00"),
    )

    variant_without_image = make_variant(
        product=product,
        price=Decimal("700.00"),
    )

    ProductImage.objects.create(
        product=product,
        image_url="https://example.com/product-secondary.jpg",
        display_order=0,
    )

    ProductImage.objects.create(
        product=product,
        image_url="https://example.com/product-main.jpg",
        is_main=True,
        display_order=1,
    )

    ProductImage.objects.create(
        product=product,
        variant=variant_with_image,
        image_url="https://example.com/variant-main.jpg",
        is_main=True,
    )

    response = client.get("/api/catalog")

    assert response.status_code == 200
    assert response.data["count"] == 2

    cards_by_variant_id = {
        card["variant_id"]: card for card in response.data["results"]
    }

    assert (
        cards_by_variant_id[str(variant_with_image.id)]["image_url"]
        == "https://example.com/variant-main.jpg"
    )

    assert (
        cards_by_variant_id[str(variant_without_image.id)]["image_url"]
        == "https://example.com/product-main.jpg"
    )


def test_catalog_variant_image_fallback_handles_main_image_and_missing_images(
    client,
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

    product_with_main_image = make_product(
        name="Product With Main Image",
        category=category,
    )

    product_with_main_image.main_image = "https://example.com/product-fallback.jpg"
    product_with_main_image.save(update_fields=["main_image"])

    variant_with_fallback = make_variant(
        product=product_with_main_image,
        price=Decimal("500.00"),
    )

    product_without_images = make_product(
        name="Product Without Images",
        category=category,
    )

    variant_without_images = make_variant(
        product=product_without_images,
        price=Decimal("700.00"),
    )

    response = client.get("/api/catalog")

    assert response.status_code == 200
    assert response.data["count"] == 2

    cards_by_variant_id = {
        card["variant_id"]: card for card in response.data["results"]
    }

    assert (
        cards_by_variant_id[str(variant_with_fallback.id)]["image_url"]
        == "https://example.com/product-fallback.jpg"
    )

    assert cards_by_variant_id[str(variant_without_images.id)]["image_url"] is None


def test_catalog_combines_product_and_matching_variant_badges(
    client,
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

    product = make_product(
        name="Dog Food",
        category=category,
    )

    first_variant = make_variant(
        product=product,
        price=Decimal("500.00"),
    )

    second_variant = make_variant(
        product=product,
        price=Decimal("700.00"),
    )

    product_badge = Badge.objects.create(
        name="Bestseller",
        slug="bestseller",
        label="Bestseller",
    )

    shared_badge = Badge.objects.create(
        name="Featured",
        slug="featured",
        label="Featured",
    )

    first_variant_badge = Badge.objects.create(
        name="Sale",
        slug="sale",
        label="Sale",
    )

    second_variant_badge = Badge.objects.create(
        name="Limited",
        slug="limited",
        label="Limited",
    )

    inactive_badge = Badge.objects.create(
        name="Hidden",
        slug="hidden",
        label="Hidden",
        is_active=False,
    )

    product.badges.add(
        product_badge,
        shared_badge,
        inactive_badge,
    )

    first_variant.badges.add(
        shared_badge,
        first_variant_badge,
    )

    second_variant.badges.add(
        second_variant_badge,
    )

    response = client.get("/api/catalog")

    assert response.status_code == 200
    assert response.data["count"] == 2

    cards_by_variant_id = {
        card["variant_id"]: card for card in response.data["results"]
    }

    first_card = cards_by_variant_id[str(first_variant.id)]
    second_card = cards_by_variant_id[str(second_variant.id)]

    first_badge_slugs = {badge["slug"] for badge in first_card["badges"]}

    second_badge_slugs = {badge["slug"] for badge in second_card["badges"]}

    assert first_badge_slugs == {
        "bestseller",
        "featured",
        "sale",
    }

    assert second_badge_slugs == {
        "bestseller",
        "featured",
        "limited",
    }

    assert len(first_card["badges"]) == 3
    assert len(second_card["badges"]) == 3


def test_catalog_variant_card_contains_required_product_and_variant_fields(
    client,
    make_product,
    make_variant,
):
    dogs = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )

    category = Category.objects.create(
        name="Dog Food",
        slug="dog-food",
        animal_type=dogs,
    )

    brand = Brand.objects.create(
        name="Royal Canin",
        slug="royal-canin",
    )

    product = make_product(
        name="Royal Canin Adult",
        category=category,
        brand=brand,
        rating=Decimal("4.50"),
    )

    variant = make_variant(
        product=product,
        price=Decimal("750.00"),
        stock=5,
    )

    response = client.get("/api/catalog")

    assert response.status_code == 200
    assert response.data["count"] == 1

    card = response.data["results"][0]

    required_fields = {
        "id",
        "variant_id",
        "product_id",
        "slug",
        "name",
        "brand",
        "category_slug",
        "animal_type_slug",
        "price",
        "old_price",
        "stock",
        "in_stock",
        "image_url",
        "badges",
        "attributes",
        "attributes_raw",
        "rating",
        "review_count",
    }

    missing_fields = required_fields - set(card)

    assert not missing_fields, f"Missing catalog fields: {sorted(missing_fields)}"

    assert card["id"] == str(variant.id)
    assert card["variant_id"] == str(variant.id)
    assert card["product_id"] == str(product.id)

    assert card["slug"] == product.slug
    assert card["name"] == product.name

    assert card["brand"]["slug"] == brand.slug
    assert card["category_slug"] == category.slug
    assert card["animal_type_slug"] == dogs.slug

    assert card["price"] == str(variant.price)
    assert card["stock"] == variant.stock
    assert card["in_stock"] is True


def test_catalog_accepts_locale_query_parameter(client):
    response = client.get(
        "/api/catalog",
        {"locale": "uk"},
    )

    assert response.status_code == 200

def test_catalog_orders_variants_by_product_rating(
    client,
    make_product,
    make_variant,
):
    dogs = AnimalType.objects.create(name="Dogs", slug="dogs")
    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )

    low = make_product(
        name="Low Rated",
        category=category,
        rating=Decimal("3.00"),
    )
    high = make_product(
        name="High Rated",
        category=category,
        rating=Decimal("4.80"),
    )

    low_variant = make_variant(product=low, price=Decimal("500"))
    high_variant = make_variant(product=high, price=Decimal("700"))

    response = client.get("/api/catalog", {"ordering": "-rating"})

    assert response.status_code == 200
    assert [
        card["variant_id"] for card in response.data["results"]
    ] == [
        str(high_variant.id),
        str(low_variant.id),
    ]

@pytest.mark.django_db
def test_category_detail_includes_category_and_subcategory_ids(client):
    dogs = AnimalType.objects.create(name="Dogs", slug="dogs")

    food = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=dogs,
    )
    treats = Category.objects.create(
        name="Treats",
        slug="treats",
        animal_type=dogs,
        parent=food,
    )

    response = client.get("/api/dogs/food")

    assert response.status_code == 200
    assert response.data["category"]["id"] == str(food.id)
    assert response.data["category"]["subcategories"][0]["id"] == str(treats.id)

    leaf_response = client.get("/api/dogs/food/treats")

    assert leaf_response.status_code == 200
    assert leaf_response.data["category"]["id"] == str(treats.id)
