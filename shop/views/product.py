from django.db.models import Prefetch, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination

from ..models import Product, ProductImage, ProductReview, ProductVariant
from ..serializers import ProductCardSerializer, ProductDetailSerializer


def get_request_query_params(request):
    query_params = getattr(request, "query_params", None)

    if query_params is not None:
        return query_params

    return request.GET


def get_active_variant_queryset():
    return (
        ProductVariant.objects.filter(is_active=True)
        .prefetch_related(
            "badges",
            "images",
            "variant_attributes__attribute",
            "variant_attributes__value",
        )
        .order_by("-is_default", "price", "id")
    )


def get_product_base_queryset():
    return (
        Product.objects.filter(is_active=True)
        .select_related("brand", "category", "category__animal_type")
        .prefetch_related(
            "badges",
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
    return get_product_base_queryset().prefetch_related(
        Prefetch(
            "reviews",
            queryset=(
                ProductReview.objects.filter(is_active=True)
                .select_related("user")
                .order_by("-created_at")
            ),
        ),
    )


class ProductPagination(PageNumberPagination):
    page_size = 24
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
                | Q(brand__name__icontains=search)
                | Q(category__name__icontains=search)
            )

        in_stock = query_params.get("in_stock")

        if in_stock == "true":
            variants_in_stock = (
                ProductVariant.objects.filter(is_active=True, stock__gt=0)
                .values_list("product_id", flat=True)
                .distinct()
            )
            queryset = queryset.filter(id__in=variants_in_stock)

        elif in_stock == "false":
            variants_in_stock = (
                ProductVariant.objects.filter(is_active=True, stock__gt=0)
                .values_list("product_id", flat=True)
                .distinct()
            )
            queryset = queryset.exclude(id__in=variants_in_stock)

        return queryset.distinct()


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
                | Q(brand__name__icontains=query)
                | Q(category__name__icontains=query)
            )
            .distinct()
        )
