from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import AnimalType, Brand, Category, Product
from ..serializers import (
    AnimalTypeWithCategoriesSerializer,
    BrandSerializer,
    CategoryWithChildrenSerializer,
    ProductCardSerializer,
)
from .product import (
    ProductPagination,
    get_product_base_queryset,
    get_request_query_params,
)


def get_category_by_path(animal_type_slug: str, category_path: str) -> Category:
    path_parts = [part for part in category_path.strip("/").split("/") if part]

    if not path_parts:
        raise Http404(_("Category path is required."))

    animal_type = get_object_or_404(
        AnimalType,
        slug=animal_type_slug,
        is_active=True,
    )

    parent = None
    current_category = None

    for slug in path_parts:
        current_category = get_object_or_404(
            Category,
            animal_type=animal_type,
            parent=parent,
            slug=slug,
            is_active=True,
        )
        parent = current_category

    if current_category is None:
        raise Http404(_("Category not found."))

    return current_category


def get_descendant_category_ids(category: Category) -> list:
    category_ids = [category.id]
    children = Category.objects.filter(parent=category, is_active=True).only("id")

    for child in children:
        category_ids.extend(get_descendant_category_ids(child))

    return category_ids


def get_category_tree_queryset(depth: int):
    queryset = (
        Category.objects.filter(is_active=True)
        .order_by("sort_order", "name")
        .prefetch_related("translations")
    )

    if depth <= 0:
        return queryset

    return queryset.prefetch_related(
        Prefetch(
            "children",
            queryset=get_category_tree_queryset(depth - 1),
            to_attr="prefetched_children",
        )
    )


class AnimalTypeCategoriesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, animal_type_slug):
        max_depth = 2

        root_categories_queryset = get_category_tree_queryset(max_depth).filter(
            parent__isnull=True
        )

        animal_type = get_object_or_404(
            AnimalType.objects.prefetch_related(
                "translations",
                Prefetch(
                    "categories",
                    queryset=root_categories_queryset,
                    to_attr="prefetched_root_categories",
                ),
            ),
            slug=animal_type_slug,
            is_active=True,
        )

        serializer = AnimalTypeWithCategoriesSerializer(
            animal_type,
            context={
                "request": request,
                "max_depth": max_depth,
            },
        )

        return Response(serializer.data)


class CategoryDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, animal_type_slug, category_path):
        category = get_category_by_path(
            animal_type_slug=animal_type_slug,
            category_path=category_path,
        )

        category = get_object_or_404(
            Category.objects.select_related("animal_type", "parent").prefetch_related(
                "translations",
                "animal_type__translations",
                "parent__translations",
                Prefetch(
                    "children",
                    queryset=(
                        Category.objects.filter(is_active=True)
                        .order_by("sort_order", "name")
                        .prefetch_related("translations")
                    ),
                    to_attr="prefetched_children",
                ),
            ),
            pk=category.pk,
        )

        serializer = CategoryWithChildrenSerializer(category)

        return Response({"category": serializer.data})


class BrandListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = BrandSerializer

    def get_queryset(self):
        return Brand.objects.filter(is_active=True).order_by("name")


class BrandDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = BrandSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "brand_slug"

    def get_queryset(self):
        return Brand.objects.filter(is_active=True)


class CategoryProductsView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductCardSerializer
    pagination_class = ProductPagination

    def get_queryset(self):
        animal_type_slug = self.kwargs["animal_type_slug"]
        category_path = self.kwargs["category_path"]

        try:
            category = get_category_by_path(
                animal_type_slug=animal_type_slug,
                category_path=category_path,
            )
        except Http404:
            return Product.objects.none()

        query_params = get_request_query_params(self.request)
        include_subcategories = query_params.get(
            "include_subcategories",
            "true",
        )

        if include_subcategories == "false":
            category_ids = [category.id]
        else:
            category_ids = get_descendant_category_ids(category)

        return (
            get_product_base_queryset().filter(category_id__in=category_ids).distinct()
        )
