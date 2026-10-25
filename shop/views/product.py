from django.db.models import Prefetch, Q
from rest_framework import generics, permissions
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from ..filters.catalog import (
    apply_product_level_filters,
    get_matching_variants_queryset,
)
from ..filters.query_param_validation import validate_catalog_filter_params
from ..models import (
    Product,
    ProductImage,
    ProductReview,
    ProductReviewImage,
    ProductVariant,
)
from ..models.product_review import (
    ReviewImageModerationStatus,
    ReviewModerationStatus,
)
from ..serializers import (
    ProductCardSerializer,
    ProductDetailSerializer,
    CatalogVariantCardSerializer,
)


def get_request_query_params(request):
    query_params = getattr(request, "query_params", None)

    if query_params is not None:
        return query_params

    return request.GET


def get_active_variant_queryset():
    return (
        ProductVariant.objects.filter(is_active=True)
        .prefetch_related(
            "translations",
            "badges",
            "badges__translations",
            "images",
            "variant_attributes__attribute",
            "variant_attributes__attribute__translations",
            "variant_attributes__value",
            "variant_attributes__value__translations",
        )
        .order_by("-is_default", "price", "id")
    )


def get_product_base_queryset():
    return (
        Product.objects.filter(is_active=True)
        .select_related("brand", "category", "category__animal_type")
        .prefetch_related(
            "translations",
            "badges",
            "badges__translations",
            "category__translations",
            "category__animal_type__translations",
            Prefetch(
                "images",
                queryset=ProductImage.objects.order_by("display_order", "id"),
            ),
            Prefetch(
                "variants",
                queryset=get_active_variant_queryset(),
                to_attr="active_variants",
            ),
        )
    )


def get_product_detail_queryset():
    approved_review_images = ProductReviewImage.objects.filter(
        moderation_status=ReviewImageModerationStatus.APPROVED,
    ).order_by(
        "position",
        "created_at",
    )

    approved_reviews = (
        ProductReview.objects.filter(
            is_active=True,
            moderation_status=ReviewModerationStatus.APPROVED,
        )
        .select_related("user")
        .prefetch_related(
            Prefetch(
                "images",
                queryset=approved_review_images,
                to_attr="approved_images",
            )
        )
        .order_by("-created_at")
    )

    return get_product_base_queryset().prefetch_related(
        Prefetch(
            "reviews",
            queryset=approved_reviews,
        ),
    )


class ProductPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 100


class CatalogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ProductListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductCardSerializer
    pagination_class = ProductPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]

    filterset_fields = {
        "category": ["exact"],
        "brand": ["exact"],
        "rating": ["gte", "lte"],
        "category__animal_type__slug": ["exact"],
    }

    ordering_fields = ["name", "rating", "created_at", "review_count"]
    ordering = ["-created_at"]

    def get_queryset(self):
        query_params = get_request_query_params(self.request)
        queryset = get_product_base_queryset()

        price_min = query_params.get("price_min")
        price_max = query_params.get("price_max")

        if price_min or price_max:
            variants_qs = ProductVariant.objects.filter(is_active=True)

            if price_min:
                variants_qs = variants_qs.filter(price__gte=price_min)

            if price_max:
                variants_qs = variants_qs.filter(price__lte=price_max)

            product_ids = variants_qs.values_list("product_id", flat=True).distinct()

            queryset = queryset.filter(id__in=product_ids)

        search = query_params.get("search", "").strip()

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(short_description__icontains=search)
                | Q(translations__name__icontains=search)
                | Q(translations__description__icontains=search)
                | Q(translations__short_description__icontains=search)
                | Q(brand__name__icontains=search)
                | Q(category__name__icontains=search)
                | Q(category__translations__name__icontains=search)
            )

        in_stock = query_params.get("in_stock")

        if in_stock == "true":
            variants_in_stock = (
                ProductVariant.objects.filter(
                    is_active=True,
                    stock__gt=0,
                )
                .values_list("product_id", flat=True)
                .distinct()
            )

            queryset = queryset.filter(id__in=variants_in_stock)

        elif in_stock == "false":
            variants_in_stock = (
                ProductVariant.objects.filter(
                    is_active=True,
                    stock__gt=0,
                )
                .values_list("product_id", flat=True)
                .distinct()
            )

            queryset = queryset.exclude(id__in=variants_in_stock)

        return queryset.distinct()


class CatalogVariantListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CatalogVariantCardSerializer
    pagination_class = CatalogPagination

    ORDERING_FIELDS = {
        "name": "product__name",
        "price": "price",
        "rating": "rating",
        "created_at": "product__created_at",
        "review_count": "product__review_count",
    }

    def get_queryset(self):
        query_params = get_request_query_params(self.request)
        params = validate_catalog_filter_params(query_params)

        requested_ordering = query_params.get("ordering", "-created_at")
        is_descending = requested_ordering.startswith("-")
        ordering_key = requested_ordering.removeprefix("-")

        orm_field = self.ORDERING_FIELDS.get(ordering_key)

        if orm_field is None:
            orm_field = self.ORDERING_FIELDS["created_at"]
            is_descending = True

        if is_descending:
            orm_field = f"-{orm_field}"

        products = apply_product_level_filters(
            queryset=Product.objects.filter(is_active=True),
            params=params,
        )

        variants = get_matching_variants_queryset(
            params=params,
            queryset=get_active_variant_queryset(),
        )

        return (
            variants.filter(
                product_id__in=products.values("pk"),
            )
            .select_related(
                "product",
                "product__brand",
                "product__category",
                "product__category__animal_type",
            )
            .prefetch_related(
                "product__translations",
                "product__badges",
                "product__badges__translations",
                Prefetch(
                    "product__images",
                    queryset=ProductImage.objects.filter(
                        variant__isnull=True,
                    ).order_by("display_order", "id"),
                    to_attr="catalog_product_images",
                ),
            )
            .order_by(orm_field, "pk")
        )


class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = "id"
    lookup_url_kwarg = "product_id"

    def get_queryset(self):
        return get_product_detail_queryset()


class RelatedProductsView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductCardSerializer

    def get_queryset(self):
        product_id = self.kwargs["product_id"]

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Product.objects.none()

        return (
            get_product_base_queryset()
            .filter(category=product.category)
            .exclude(id=product_id)
            .order_by("-rating", "-review_count")[:6]
        )


class ProductSearchView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductCardSerializer
    pagination_class = ProductPagination

    def get_queryset(self):
        query_params = get_request_query_params(self.request)
        query = query_params.get("q", "").strip()

        if not query or len(query) < 2:
            return Product.objects.none()

        return (
            get_product_base_queryset()
            .filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(short_description__icontains=query)
                | Q(translations__name__icontains=query)
                | Q(translations__description__icontains=query)
                | Q(translations__short_description__icontains=query)
                | Q(brand__name__icontains=query)
                | Q(category__name__icontains=query)
                | Q(category__translations__name__icontains=query)
            )
            .distinct()
        )
