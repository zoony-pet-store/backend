import pytest
from django.urls import reverse

from shop.models import AnimalType, Category


pytestmark = pytest.mark.django_db


def test_category_admin_add_page_loads(admin_client):
    response = admin_client.get(reverse("admin:shop_category_add"))

    assert response.status_code == 200


def test_category_admin_change_page_loads(admin_client):
    animal_type = AnimalType.objects.create(
        name="Dogs",
        slug="dogs",
    )

    category = Category.objects.create(
        name="Food",
        slug="food",
        animal_type=animal_type,
    )

    response = admin_client.get(
        reverse(
            "admin:shop_category_change",
            args=[category.pk],
        )
    )

    assert response.status_code == 200
