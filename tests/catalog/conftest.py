from decimal import Decimal

import pytest

from shop.models import (
    ProductAttribute,
    ProductAttributeValue,
    Product,
    ProductVariant,
    ProductVariantAttribute,
    Category,
    Brand,
)


@pytest.fixture
def flavor_attribute(db):
    return ProductAttribute.objects.create(
        name="Flavor",
        slug="flavor",
        type=ProductAttribute.AttributeType.SELECT,
        filterable=True,
    )


@pytest.fixture
def flavor_values(flavor_attribute):
    duck = ProductAttributeValue.objects.create(
        attribute=flavor_attribute,
        value="Duck",
        slug="duck",
    )
    chicken = ProductAttributeValue.objects.create(
        attribute=flavor_attribute,
        value="Chicken",
        slug="chicken",
    )
    beef = ProductAttributeValue.objects.create(
        attribute=flavor_attribute,
        value="Beef",
        slug="beef",
    )
    return duck, chicken, beef


@pytest.fixture
def weight_attribute(db):
    return ProductAttribute.objects.create(
        name="Weight",
        slug="weight",
        type=ProductAttribute.AttributeType.NUMERIC,
        available_units=["g", "kg"],
        filterable=True,
    )


@pytest.fixture
def non_filterable_attribute(db):
    return ProductAttribute.objects.create(
        name="Internal code",
        slug="internal-code",
        type=ProductAttribute.AttributeType.SELECT,
        filterable=False,
    )


@pytest.fixture
def make_product(db):
    def _make_product(
        *,
        name: str,
        category: Category,
        brand: Brand | None = None,
        rating: Decimal = Decimal("0"),
        is_active: bool = True,
    ):
        return Product.objects.create(
            name=name,
            slug=name.lower().replace(" ", "-"),
            category=category,
            brand=brand,
            rating=rating,
            is_active=is_active,
        )

    return _make_product


@pytest.fixture
def make_variant(db):
    def _make_variant(
        *,
        product: Product,
        price: Decimal,
        stock: int = 0,
        is_active: bool = True,
    ):
        return ProductVariant.objects.create(
            product=product,
            price=price,
            stock=stock,
            is_active=is_active,
            auto_badges_enabled=False,
        )

    return _make_variant


@pytest.fixture
def make_select_variant_attribute(db):
    def _make_select_variant_attribute(
        *,
        variant: ProductVariant,
        attribute: ProductAttribute,
        value: ProductAttributeValue,
    ) -> ProductVariantAttribute:
        return ProductVariantAttribute.objects.create(
            variant=variant,
            attribute=attribute,
            value=value,
        )

    return _make_select_variant_attribute
