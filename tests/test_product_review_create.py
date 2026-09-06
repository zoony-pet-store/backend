from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from shop.models import (
    AnimalType,
    Category,
    Product,
    ProductReview,
)


pytestmark = pytest.mark.django_db


def get_review_create_url(product):
    return reverse(
        "shop:product-review-create",
        kwargs={"product_id": product.id},
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    User = get_user_model()

    return User.objects.create_user(
        username="review-test-user",
        email="user@example.com",
        password="test-password",
    )


@pytest.fixture
def product():
    animal_type = AnimalType.objects.create(
        name="Коти",
        slug="review-test-cats",
        is_active=True,
    )

    category = Category.objects.create(
        name="Сухий корм",
        slug="review-test-dry-food",
        animal_type=animal_type,
        is_active=True,
    )

    return Product.objects.create(
        name="Тестовий товар",
        slug="review-test-product",
        category=category,
        is_active=True,
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


def test_review_can_be_created_without_comment(
    authenticated_client,
    product,
):
    response = authenticated_client.post(
        get_review_create_url(product),
        data={
            "rating": "4.5",
            "reviewer_name": "Ivan",
            "reviewer_email": "ivan@example.com",
        },
        format="json",
    )

    assert response.status_code == 201

    review = ProductReview.objects.get(
        product=product,
        reviewer_email="ivan@example.com",
    )

    assert review.reviewer_name == "Ivan"
    assert review.reviewer_email == "ivan@example.com"
    assert review.rating_score == 9
    assert review.comment == ""


def test_review_can_be_created_with_blank_comment(
    authenticated_client,
    product,
):
    response = authenticated_client.post(
        get_review_create_url(product),
        data={
            "rating": "5.0",
            "reviewer_name": "Ivan",
            "reviewer_email": "ivan@example.com",
            "comment": "   ",
        },
        format="json",
    )

    assert response.status_code == 201

    review = ProductReview.objects.get(
        product=product,
        reviewer_email="ivan@example.com",
    )

    assert review.comment == ""


@pytest.mark.parametrize(
    ("missing_field", "payload"),
    [
        (
            "rating",
            {
                "reviewer_name": "Ivan",
                "reviewer_email": "ivan@example.com",
            },
        ),
        (
            "reviewer_name",
            {
                "rating": "4.5",
                "reviewer_email": "ivan@example.com",
            },
        ),
        (
            "reviewer_email",
            {
                "rating": "4.5",
                "reviewer_name": "Ivan",
            },
        ),
    ],
)
def test_review_requires_rating_name_and_email(
    authenticated_client,
    product,
    missing_field,
    payload,
):
    response = authenticated_client.post(
        get_review_create_url(product),
        data=payload,
        format="json",
    )

    assert response.status_code == 400
    assert missing_field in response.data


def test_review_rating_must_use_half_star_steps(
    authenticated_client,
    product,
):
    response = authenticated_client.post(
        get_review_create_url(product),
        data={
            "rating": "4.3",
            "reviewer_name": "Ivan",
            "reviewer_email": "ivan@example.com",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "rating" in response.data

    assert not ProductReview.objects.filter(
        product=product,
    ).exists()
