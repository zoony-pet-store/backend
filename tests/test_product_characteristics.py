from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from shop.models import (
    AnimalType,
    AnimalTypeTranslation,
    Brand,
    Category,
    CategoryTranslation,
    Product,
    ProductAttribute,
    ProductAttributeTranslation,
    ProductAttributeValue,
    ProductAttributeValueTranslation,
    ProductVariant,
    ProductVariantAttribute,
)


pytestmark = pytest.mark.django_db


def get_characteristics(response):
    return {item["key"]: item for item in response.data["characteristics"]}


def get_product_detail(api_client, product, language="uk"):
    url = reverse(
        "shop:product-detail",
        kwargs={"product_id": product.id},
    )

    return api_client.get(
        url,
        HTTP_ACCEPT_LANGUAGE=language,
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def product_setup():
    animal_type = AnimalType.objects.create(
        name="Коти",
        slug="cats",
        is_active=True,
    )

    category = Category.objects.create(
        name="Сухий корм",
        slug="dry-food",
        animal_type=animal_type,
        is_active=True,
    )

    brand = Brand.objects.create(
        name="Test Brand",
        slug="test-brand",
        is_active=True,
    )

    product = Product.objects.create(
        name="Тестовий товар",
        slug="test-product",
        brand=brand,
        category=category,
        is_active=True,
    )

    variant = ProductVariant.objects.create(
        product=product,
        sku="TEST-VARIANT-1",
        price=Decimal("100.00"),
        stock=10,
        is_active=True,
        is_default=True,
    )

    return {
        "animal_type": animal_type,
        "category": category,
        "brand": brand,
        "product": product,
        "variant": variant,
    }


def test_product_detail_contains_base_characteristics(
    api_client,
    product_setup,
):
    product = product_setup["product"]

    response = get_product_detail(
        api_client,
        product,
        language="uk",
    )

    assert response.status_code == 200

    characteristics = get_characteristics(response)

    assert set(characteristics) == {
        "animal",
        "brand",
        "product_group",
    }

    assert characteristics["animal"] == {
        "key": "animal",
        "label": "Тварина",
        "values": [
            {
                "value": "Коти",
                "slug": "cats",
            }
        ],
    }

    assert characteristics["brand"] == {
        "key": "brand",
        "label": "Бренд",
        "values": [
            {
                "value": "Test Brand",
                "slug": "test-brand",
            }
        ],
    }

    assert characteristics["product_group"] == {
        "key": "product_group",
        "label": "Група товару",
        "values": [
            {
                "value": "Сухий корм",
                "slug": "dry-food",
            }
        ],
    }


def test_characteristics_aggregate_unique_select_values_from_variants(
    api_client,
    product_setup,
):
    product = product_setup["product"]
    first_variant = product_setup["variant"]

    second_variant = ProductVariant.objects.create(
        product=product,
        sku="TEST-VARIANT-2",
        price=Decimal("110.00"),
        stock=5,
        is_active=True,
        is_default=False,
    )

    color = ProductAttribute.objects.create(
        name="Колір",
        slug="color",
        type=ProductAttribute.AttributeType.SELECT,
    )

    red = ProductAttributeValue.objects.create(
        attribute=color,
        value="Червоний",
        slug="red",
    )

    size = ProductAttribute.objects.create(
        name="Розмір",
        slug="size",
        type=ProductAttribute.AttributeType.SELECT,
    )

    small = ProductAttributeValue.objects.create(
        attribute=size,
        value="Малий",
        slug="small",
    )

    large = ProductAttributeValue.objects.create(
        attribute=size,
        value="Великий",
        slug="large",
    )

    # Спочатку різний Size, щоб variants мали різні комбінації.
    ProductVariantAttribute.objects.create(
        variant=first_variant,
        attribute=size,
        value=small,
    )

    ProductVariantAttribute.objects.create(
        variant=second_variant,
        attribute=size,
        value=large,
    )

    # Color однаковий для обох variants.
    ProductVariantAttribute.objects.create(
        variant=first_variant,
        attribute=color,
        value=red,
    )

    ProductVariantAttribute.objects.create(
        variant=second_variant,
        attribute=color,
        value=red,
    )

    response = get_product_detail(
        api_client,
        product,
        language="uk",
    )

    assert response.status_code == 200

    characteristics = get_characteristics(response)

    color_values = characteristics["color"]["values"]

    assert color_values == [
        {
            "id": str(red.id),
            "value": "Червоний",
            "slug": "red",
        }
    ]

    size_slugs = {item["slug"] for item in characteristics["size"]["values"]}

    assert size_slugs == {"small", "large"}
    assert len(characteristics["size"]["values"]) == 2


def test_characteristics_aggregate_unique_select_values_from_variants(
    api_client,
    product_setup,
):
    product = product_setup["product"]
    first_variant = product_setup["variant"]

    second_variant = ProductVariant.objects.create(
        product=product,
        sku="TEST-VARIANT-2",
        price=Decimal("110.00"),
        stock=5,
        is_active=True,
        is_default=False,
    )

    color = ProductAttribute.objects.create(
        name="Колір",
        slug="color",
        type=ProductAttribute.AttributeType.SELECT,
    )

    red = ProductAttributeValue.objects.create(
        attribute=color,
        value="Червоний",
        slug="red",
    )

    size = ProductAttribute.objects.create(
        name="Розмір",
        slug="size",
        type=ProductAttribute.AttributeType.SELECT,
    )

    small = ProductAttributeValue.objects.create(
        attribute=size,
        value="Малий",
        slug="small",
    )

    large = ProductAttributeValue.objects.create(
        attribute=size,
        value="Великий",
        slug="large",
    )

    # Спочатку різний Size, щоб variants мали різні комбінації.
    ProductVariantAttribute.objects.create(
        variant=first_variant,
        attribute=size,
        value=small,
    )

    ProductVariantAttribute.objects.create(
        variant=second_variant,
        attribute=size,
        value=large,
    )

    # Color однаковий для обох variants.
    ProductVariantAttribute.objects.create(
        variant=first_variant,
        attribute=color,
        value=red,
    )

    ProductVariantAttribute.objects.create(
        variant=second_variant,
        attribute=color,
        value=red,
    )

    response = get_product_detail(
        api_client,
        product,
        language="uk",
    )

    assert response.status_code == 200

    characteristics = get_characteristics(response)

    color_values = characteristics["color"]["values"]

    assert color_values == [
        {
            "id": str(red.id),
            "value": "Червоний",
            "slug": "red",
        }
    ]

    size_slugs = {item["slug"] for item in characteristics["size"]["values"]}

    assert size_slugs == {"small", "large"}
    assert len(characteristics["size"]["values"]) == 2


def test_characteristics_aggregate_unique_numeric_values_from_variants(
    api_client,
    product_setup,
):
    product = product_setup["product"]
    first_variant = product_setup["variant"]

    second_variant = ProductVariant.objects.create(
        product=product,
        sku="TEST-VARIANT-2",
        price=Decimal("110.00"),
        stock=5,
        is_active=True,
        is_default=False,
    )

    third_variant = ProductVariant.objects.create(
        product=product,
        sku="TEST-VARIANT-3",
        price=Decimal("120.00"),
        stock=5,
        is_active=True,
        is_default=False,
    )

    color = ProductAttribute.objects.create(
        name="Колір",
        slug="color",
        type=ProductAttribute.AttributeType.SELECT,
    )

    red = ProductAttributeValue.objects.create(
        attribute=color,
        value="Червоний",
        slug="red",
    )
    green = ProductAttributeValue.objects.create(
        attribute=color,
        value="Зелений",
        slug="green",
    )
    blue = ProductAttributeValue.objects.create(
        attribute=color,
        value="Синій",
        slug="blue",
    )

    ProductVariantAttribute.objects.create(
        variant=first_variant,
        attribute=color,
        value=red,
    )
    ProductVariantAttribute.objects.create(
        variant=second_variant,
        attribute=color,
        value=green,
    )
    ProductVariantAttribute.objects.create(
        variant=third_variant,
        attribute=color,
        value=blue,
    )

    weight = ProductAttribute.objects.create(
        name="Вага",
        slug="weight",
        type=ProductAttribute.AttributeType.NUMERIC,
        available_units=["kg"],
    )

    ProductVariantAttribute.objects.create(
        variant=first_variant,
        attribute=weight,
        value_numeric=Decimal("3.000"),
        unit="kg",
    )

    ProductVariantAttribute.objects.create(
        variant=second_variant,
        attribute=weight,
        value_numeric=Decimal("3.000"),
        unit="kg",
    )

    ProductVariantAttribute.objects.create(
        variant=third_variant,
        attribute=weight,
        value_numeric=Decimal("5.000"),
        unit="kg",
    )

    response = get_product_detail(
        api_client,
        product,
        language="uk",
    )

    assert response.status_code == 200

    characteristics = get_characteristics(response)

    weight_values = characteristics["weight"]["values"]

    assert [(item["value_decimal"], item["unit"]) for item in weight_values] == [
        ("3.000", "kg"),
        ("5.000", "kg"),
    ]


def test_characteristics_ignore_inactive_variants(
    api_client,
    product_setup,
):
    product = product_setup["product"]
    active_variant = product_setup["variant"]

    inactive_variant = ProductVariant.objects.create(
        product=product,
        sku="TEST-INACTIVE-VARIANT",
        price=Decimal("90.00"),
        stock=10,
        is_active=False,
        is_default=False,
    )

    color = ProductAttribute.objects.create(
        name="Колір",
        slug="color",
        type=ProductAttribute.AttributeType.SELECT,
    )

    red = ProductAttributeValue.objects.create(
        attribute=color,
        value="Червоний",
        slug="red",
    )

    green = ProductAttributeValue.objects.create(
        attribute=color,
        value="Зелений",
        slug="green",
    )

    ProductVariantAttribute.objects.create(
        variant=active_variant,
        attribute=color,
        value=red,
    )

    ProductVariantAttribute.objects.create(
        variant=inactive_variant,
        attribute=color,
        value=green,
    )

    response = get_product_detail(
        api_client,
        product,
        language="uk",
    )

    assert response.status_code == 200

    characteristics = get_characteristics(response)

    assert characteristics["color"]["values"] == [
        {
            "id": str(red.id),
            "value": "Червоний",
            "slug": "red",
        }
    ]


def test_characteristics_support_product_without_brand(
    api_client,
    product_setup,
):
    product = product_setup["product"]

    product.brand = None
    product.save(update_fields=["brand"])

    response = get_product_detail(
        api_client,
        product,
        language="uk",
    )

    assert response.status_code == 200

    characteristics = get_characteristics(response)

    assert characteristics["brand"] == {
        "key": "brand",
        "label": "Бренд",
        "values": [],
    }


def test_characteristics_are_localized(
    api_client,
    product_setup,
):
    product = product_setup["product"]
    variant = product_setup["variant"]
    animal_type = product_setup["animal_type"]
    category = product_setup["category"]

    color = ProductAttribute.objects.create(
        name="Колір",
        slug="color",
        type=ProductAttribute.AttributeType.SELECT,
    )

    green = ProductAttributeValue.objects.create(
        attribute=color,
        value="Зелений",
        slug="green",
    )

    ProductVariantAttribute.objects.create(
        variant=variant,
        attribute=color,
        value=green,
    )

    AnimalTypeTranslation.objects.create(
        animal_type=animal_type,
        language="en",
        name="Cats",
    )

    CategoryTranslation.objects.create(
        category=category,
        language="en",
        name="Dry Food",
        description="",
    )

    ProductAttributeTranslation.objects.create(
        attribute=color,
        language="en",
        name="Color",
        description="",
    )

    ProductAttributeValueTranslation.objects.create(
        attribute_value=green,
        language="en",
        value="Green",
    )

    uk_response = get_product_detail(
        api_client,
        product,
        language="uk",
    )

    en_response = get_product_detail(
        api_client,
        product,
        language="en",
    )

    assert uk_response.status_code == 200
    assert en_response.status_code == 200

    uk_characteristics = get_characteristics(uk_response)
    en_characteristics = get_characteristics(en_response)

    # Stable machine identifiers.
    assert uk_characteristics["animal"]["key"] == "animal"
    assert en_characteristics["animal"]["key"] == "animal"

    assert uk_characteristics["color"]["key"] == "color"
    assert en_characteristics["color"]["key"] == "color"

    assert uk_characteristics["color"]["values"][0]["slug"] == "green"
    assert en_characteristics["color"]["values"][0]["slug"] == "green"

    # Ukrainian UI data.
    assert uk_characteristics["animal"]["label"] == "Тварина"
    assert uk_characteristics["animal"]["values"][0]["value"] == "Коти"

    assert uk_characteristics["color"]["label"] == "Колір"
    assert uk_characteristics["color"]["values"][0]["value"] == "Зелений"

    # English UI data.
    assert en_characteristics["animal"]["label"] == "Animal"
    assert en_characteristics["animal"]["values"][0]["value"] == "Cats"

    assert en_characteristics["product_group"]["label"] == "Product group"
    assert en_characteristics["product_group"]["values"][0]["value"] == "Dry Food"

    assert en_characteristics["color"]["label"] == "Color"
    assert en_characteristics["color"]["values"][0]["value"] == "Green"


def test_characteristics_update_after_variant_attribute_removed(
    api_client,
    product_setup,
):
    product = product_setup["product"]
    variant = product_setup["variant"]

    color = ProductAttribute.objects.create(
        name="Колір",
        slug="color",
        type=ProductAttribute.AttributeType.SELECT,
    )

    red = ProductAttributeValue.objects.create(
        attribute=color,
        value="Червоний",
        slug="red",
    )

    variant_attribute = ProductVariantAttribute.objects.create(
        variant=variant,
        attribute=color,
        value=red,
    )

    response_before = get_product_detail(
        api_client,
        product,
        language="uk",
    )

    assert response_before.status_code == 200

    characteristics_before = get_characteristics(
        response_before,
    )

    assert "color" in characteristics_before

    variant_attribute.delete()

    response_after = get_product_detail(
        api_client,
        product,
        language="uk",
    )

    assert response_after.status_code == 200

    characteristics_after = get_characteristics(
        response_after,
    )

    assert "color" not in characteristics_after
