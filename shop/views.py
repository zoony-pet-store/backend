from datetime import timedelta

import cloudinary.uploader
from django.db.models import Avg, Count, F, Prefetch, Q
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import (
    AnimalType,
    Brand,
    Category,
    Customer,
    Product,
    ProductImage,
    ProductReview,
    ProductVariant,
)
from .serializers import (
    AnimalTypeWithCategoriesSerializer,
    BrandSerializer,
    CategoryWithChildrenSerializer,
    GoogleAuthSerializer,
    LoginSerializer,
    ProductCardSerializer,
    ProductDetailSerializer,
    ProductReviewCreateSerializer,
    ProductReviewItemSerializer,
    UserRegisterSerializer,
)


def health_check(request):
    return JsonResponse({"status": "ok", "message": "Service is healthy"})


def index(request: HttpRequest) -> HttpResponse:
    num_products = Product.objects.count()
    count_users = Customer.objects.count()
    count_categories = Category.objects.count()

    context = {
        "num_products": num_products,
        "count_users": count_users,
        "count_categories": count_categories,
    }

    return render(request, "home_page.html", context)


def get_token_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


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


def update_product_review_stats(product):
    stats = product.reviews.filter(is_active=True).aggregate(
        avg_rating=Avg("rating"),
        review_count=Count("id"),
    )

    product.rating = stats["avg_rating"] or 0
    product.review_count = stats["review_count"] or 0
    product.save(update_fields=["rating", "review_count"])


def get_category_by_path(animal_type_slug: str, category_path: str) -> Category:
    path_parts = [part for part in category_path.strip("/").split("/") if part]

    if not path_parts:
        raise Http404("Category path is required.")

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
        raise Http404("Category not found.")

    return current_category


def get_descendant_category_ids(category: Category) -> list:
    category_ids = [category.id]
    children = Category.objects.filter(parent=category, is_active=True).only("id")

    for child in children:
        category_ids.extend(get_descendant_category_ids(child))

    return category_ids


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Registration new user",
        request_body=UserRegisterSerializer,
        responses={201: openapi.Response("User registered successfully")},
    )
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            tokens = get_token_for_user(user)

            return Response(
                {"message": "User registered successfully", "tokens": tokens},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Login with email and password",
        request_body=LoginSerializer,
        responses={200: openapi.Response("Login successfully")},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            user = serializer.validated_data["user"]
            tokens = get_token_for_user(user)

            return Response({"message": "Login successfully", "tokens": tokens})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Login with Google OAuth2",
        request_body=GoogleAuthSerializer,
        responses={200: openapi.Response("Google authentication successfully")},
    )
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]
            tokens = get_token_for_user(user)

            return Response(
                {"message": "Google authentication successfully", "tokens": tokens}
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenRefreshView(TokenRefreshView):
    @swagger_auto_schema(
        operation_description="Updating the access token using a refresh token",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "refresh": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Refresh token",
                ),
            },
            required=["refresh"],
        ),
        responses={200: openapi.Response("Access token updated successfully")},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class AnimalTypeCategoriesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, animal_type_slug):
        animal_type = get_object_or_404(
            AnimalType,
            slug=animal_type_slug,
            is_active=True,
        )

        serializer = AnimalTypeWithCategoriesSerializer(
            animal_type,
            context={"max_depth": 2},
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
                Prefetch(
                    "children",
                    queryset=Category.objects.filter(is_active=True).order_by(
                        "sort_order", "name"
                    ),
                )
            ),
            pk=category.pk,
        )

        serializer = CategoryWithChildrenSerializer(category)

        return Response({"category": serializer.data})


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


class ProductReviewCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create product review",
        request_body=ProductReviewCreateSerializer,
        responses={
            201: ProductReviewItemSerializer,
            400: "Bad Request",
            401: "Unauthorized",
            404: "Product not found",
        },
    )
    def post(self, request, product_id):
        product = get_object_or_404(
            Product,
            id=product_id,
            is_active=True,
        )

        serializer = ProductReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review = serializer.save(
            product=product,
            user=request.user,
            is_active=True,
            is_verified=False,
        )

        update_product_review_stats(product)

        response_serializer = ProductReviewItemSerializer(
            review,
            context={"request": request},
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class DashboardView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        thirty_days_ago = timezone.now() - timedelta(days=30)

        base_queryset = get_product_base_queryset()

        new_arrivals = base_queryset.filter(
            created_at__gte=thirty_days_ago,
        ).order_by(
            "-created_at"
        )[:20]

        best_sellers = base_queryset.filter(
            rating__gte=4.5,
            review_count__gte=10,
        ).order_by("-rating", "-review_count")[:20]

        discounted_products = (
            base_queryset.filter(
                variants__is_active=True,
                variants__stock__gt=0,
                variants__old_price__isnull=False,
                variants__old_price__gt=F("variants__price"),
            )
            .distinct()
            .order_by("-created_at")[:20]
        )

        context = {"request": request}

        data = {
            "new_arrivals": ProductCardSerializer(
                new_arrivals,
                many=True,
                context=context,
            ).data,
            "best_sellers": ProductCardSerializer(
                best_sellers,
                many=True,
                context=context,
            ).data,
            "discounted_products": ProductCardSerializer(
                discounted_products,
                many=True,
                context=context,
            ).data,
        }

        return Response(data)


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


class ProductImageUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Upload product or variant image to Cloudinary",
        manual_parameters=[
            openapi.Parameter(
                name="product_id",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                required=True,
                description="Product UUID",
            ),
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                required=False,
                description=(
                    "Variant UUID. Optional. If provided, image belongs to variant."
                ),
            ),
            openapi.Parameter(
                name="image",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="Image file, max 5MB",
            ),
            openapi.Parameter(
                name="alt_text",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                required=False,
                description="Image alt text",
            ),
            openapi.Parameter(
                name="is_main",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description="Set image as main image",
            ),
            openapi.Parameter(
                name="display_order",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="Display order",
            ),
        ],
        responses={
            201: openapi.Response(
                description="Uploaded",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING),
                        "url": openapi.Schema(type=openapi.TYPE_STRING),
                        "public_id": openapi.Schema(type=openapi.TYPE_STRING),
                        "product_id": openapi.Schema(type=openapi.TYPE_STRING),
                        "variant_id": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_main": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "display_order": openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
            ),
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found",
        },
    )
    def post(self, request):
        if "image" not in request.FILES:
            return Response(
                {"error": "No image provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["image"]

        if file.size > 5 * 1024 * 1024:
            return Response(
                {"error": "Image too large (max 5MB)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product_id = request.data.get("product_id")

        if not product_id:
            return Response(
                {"error": "product_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = get_object_or_404(Product, id=product_id)
        variant_id = request.data.get("variant_id")

        variant = None

        if variant_id:
            variant = get_object_or_404(
                ProductVariant,
                id=variant_id,
                product=product,
            )

        alt_text = request.data.get("alt_text", "")

        is_main_raw = request.data.get("is_main", "false")
        is_main = str(is_main_raw).lower() in ["true", "1", "yes", "on"]

        display_order_raw = request.data.get("display_order", 0)

        try:
            display_order = int(display_order_raw)
        except (TypeError, ValueError):
            return Response(
                {"error": "display_order must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = cloudinary.uploader.upload(
            file,
            folder="products",
            resource_type="image",
        )

        if is_main:
            if variant:
                ProductImage.objects.filter(
                    product=product,
                    variant=variant,
                    is_main=True,
                ).update(is_main=False)
            else:
                ProductImage.objects.filter(
                    product=product,
                    variant__isnull=True,
                    is_main=True,
                ).update(is_main=False)

        image = ProductImage.objects.create(
            product=product,
            variant=variant,
            image_url=result["secure_url"],
            alt_text=alt_text,
            is_main=is_main,
            display_order=display_order,
            cloudinary_public_id=result["public_id"],
        )

        return Response(
            {
                "id": str(image.id),
                "url": image.image_url,
                "public_id": image.cloudinary_public_id,
                "product_id": str(product.id),
                "variant_id": str(variant.id) if variant else None,
                "is_main": image.is_main,
                "display_order": image.display_order,
            },
            status=status.HTTP_201_CREATED,
        )
