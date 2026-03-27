from django.utils import timezone
from datetime import timedelta

from django.db.models import Prefetch, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, generics, permissions
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import cloudinary.uploader

from .models import (
    Product,
    Customer,
    Category,
    AnimalType,
    ProductImage,
    ProductVariant,
    ProductReview,
    Brand,
)
from .serializers import (
    UserRegisterSerializer,
    LoginSerializer,
    GoogleAuthSerializer,
    BrandSerializer,
    ProductCardSerializer,
    ProductDetailSerializer,
    ProductVariantSerializer,
    AnimalTypeWithCategoriesSerializer,
    CategoryWithChildrenSerializer,
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
                    type=openapi.TYPE_STRING, description="Refresh token"
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
            AnimalType, slug=animal_type_slug, is_active=True
        )

        serializer = AnimalTypeWithCategoriesSerializer(
            animal_type, context={"max_depth": 2}
        )

        return Response(serializer.data)


class CategoryDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, animal_type_slug, category_path):
        # (food or food/dry-food)
        path_parts = category_path.strip("/").split("/")

        animal_type = get_object_or_404(
            AnimalType, slug=animal_type_slug, is_active=True
        )

        categories = Category.objects.filter(
            animal_type=animal_type,
            parent__isnull=True,
            is_active=True,
        )

        current_category = None
        for i, slug in enumerate(path_parts):
            if i == 0:
                current_category = get_object_or_404(categories, slug=slug)
            else:
                current_category = get_object_or_404(
                    current_category.children.filter(is_active=True), slug=slug
                )

        current_category = (
            Category.objects.filter(pk=current_category.pk)
            .prefetch_related(
                Prefetch("children", queryset=Category.objects.filter(is_active=True))
            )
            .first()
        )

        serializer = CategoryWithChildrenSerializer(current_category)

        return Response({"category": serializer.data})


class ProductPagination(PageNumberPagination):
    """Custom pagination for products"""

    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 100


class ProductListView(generics.ListAPIView):
    """
    List all products with filtering, sorting and pagination.
    Supports filtering by category, brand, animal type, price range, etc.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductCardSerializer
    pagination_class = ProductPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]

    # Fields for DjangoFilterBackend
    filterset_fields = {
        "category": ["exact"],
        "brand": ["exact"],
        "rating": ["gte", "lte"],
        "show_on_dashboard": ["exact"],
        "category__animal_type__slug": ["exact"],
    }

    # Fields available for ordering
    ordering_fields = ["name", "rating", "created_at", "review_count"]
    ordering = ["-created_at"]  # Default ordering

    def get_queryset(self):
        """Build optimized queryset with all filters applied"""
        queryset = Product.objects.filter(is_active=True)

        # Filter by price range
        price_min = self.request.query_params.get("price_min")
        price_max = self.request.query_params.get("price_max")

        if price_min or price_max:
            variants_qs = ProductVariant.objects.filter(is_active=True)
            if price_min:
                variants_qs = variants_qs.filter(price__gte=price_min)
            if price_max:
                variants_qs = variants_qs.filter(price__lte=price_max)

            product_ids = variants_qs.values_list("product_id", flat=True).distinct()
            queryset = queryset.filter(id__in=product_ids)

        # Search by text
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(brand__name__icontains=search)
                | Q(category__name__icontains=search)
            )

        # Filter by stock availability
        in_stock = self.request.query_params.get("in_stock")
        if in_stock == "true":
            variants_in_stock = (
                ProductVariant.objects.filter(is_active=True, stock__gt=0)
                .values_list("product_id", flat=True)
                .distinct()
            )
            queryset = queryset.filter(id__in=variants_in_stock)

        # Optimize queries with select_related and prefetch_related
        queryset = (
            queryset.select_related("brand", "category", "category__animal_type")
            .prefetch_related(
                Prefetch(
                    "images", queryset=ProductImage.objects.order_by("display_order")
                ),
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.filter(
                        is_active=True
                    ).prefetch_related("attributes"),
                ),
            )
            .distinct()
        )

        return queryset


class ProductDetailView(generics.RetrieveAPIView):
    """
    Retrieve detailed information about a specific product.
    Includes variants, images, reviews, and all related data.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = "id"
    lookup_url_kwarg = "product_id"

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related("brand", "category", "category__animal_type")
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=ProductImage.objects.order_by("display_order"),
                ),
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.filter(
                        is_active=True
                    ).prefetch_related("attributes", "images"),
                ),
                Prefetch(
                    "reviews",
                    queryset=ProductReview.objects.filter(is_active=True)
                    .select_related("user")
                    .order_by("-created_at"),
                ),
            )
        )


class DashboardView(APIView):
    """
    1. New arrivals (20 newest products from last 30 days)
    2. Best sellers (20 products with highest rating)
    3. Discounted products (20 products with discounts)
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):

        thirty_days_ago = timezone.now() - timedelta(days=30)
        new_arrivals = (
            Product.objects.filter(created_at__gte=thirty_days_ago, is_active=True)
            .select_related("brand", "category", "category__animal_type")
            .prefetch_related("images", "variants")
            .order_by("-created_at")[:20]
        )

        best_sellers = (
            Product.objects.filter(
                rating__gte=4.5, review_count__gte=10, is_active=True
            )
            .select_related("brand", "category", "category__animal_type")
            .prefetch_related("images", "variants")
            .order_by("-rating", "-review_count")[:20]
        )

        discounted_products = (
            Product.objects.filter(
                variants__has_discount=True,
                variants__is_active=True,
                variants__stock__gt=0,
                is_active=True,
            )
            .distinct()
            .select_related("brand", "category", "category__animal_type")
            .prefetch_related("images", "variants")
            .order_by("-created_at")[:20]
        )

        context = {"request": request}

        data = {
            "new_arrivals": ProductCardSerializer(
                new_arrivals, many=True, context=context
            ).data,
            "best_sellers": ProductCardSerializer(
                best_sellers, many=True, context=context
            ).data,
            "discounted_products": ProductCardSerializer(
                discounted_products, many=True, context=context
            ).data,
        }

        return Response(data)


class BrandListView(generics.ListAPIView):
    """List all active brands"""

    permission_classes = [permissions.AllowAny]
    queryset = Brand.objects.filter(is_active=True).order_by("name")
    serializer_class = BrandSerializer


class BrandDetailView(generics.RetrieveAPIView):
    """Retrieve detailed information about a specific brand"""

    permission_classes = [permissions.AllowAny]
    serializer_class = BrandSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "brand_slug"

    def get_queryset(self):
        return Brand.objects.filter(is_active=True)


class FeaturedProductsView(generics.ListAPIView):
    """Get featured products (usually for homepage or promotions)"""

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductCardSerializer

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True, show_on_dashboard=True)
            .select_related("brand", "category")
            .prefetch_related("images", "variants")
            .order_by("-rating", "-review_count")[:12]
        )


class RelatedProductsView(generics.ListAPIView):
    """Get related products for a specific product"""

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductCardSerializer

    def get_queryset(self):
        product_id = self.kwargs["product_id"]

        try:
            product = Product.objects.get(id=product_id, is_active=True)
            return (
                Product.objects.filter(category=product.category, is_active=True)
                .exclude(id=product_id)
                .select_related("brand", "category")
                .prefetch_related("images", "variants")
                .order_by("-rating", "-review_count")[:6]
            )
        except Product.DoesNotExist:
            return Product.objects.none()


class ProductSearchView(generics.ListAPIView):
    """
    Search products by text query.
    Searches in name, description, brand name, and category name.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductCardSerializer
    pagination_class = ProductPagination

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()
        if not query or len(query) < 2:
            return Product.objects.none()

        return (
            Product.objects.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(short_description__icontains=query)
                | Q(brand__name__icontains=query)
                | Q(category__name__icontains=query)
            )
            .filter(is_active=True)
            .select_related("brand", "category")
            .prefetch_related("images", "variants")
            .distinct()
        )


class CategoryProductsView(generics.ListAPIView):
    """
    Simple version that finds category by last slug in path.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductCardSerializer
    pagination_class = ProductPagination

    def get_queryset(self):
        animal_type_slug = self.kwargs["animal_type_slug"]
        category_path = self.kwargs["category_path"]

        print(f"=== DEBUG ===")
        print(
            f"Request: animal_type_slug={animal_type_slug}, category_path={category_path}"
        )

        # Get the last part of the path
        target_slug = category_path.strip("/").split("/")[-1]
        print(f"Target slug: {target_slug}")

        # Try to find the category
        try:
            animal_type = AnimalType.objects.get(slug=animal_type_slug, is_active=True)
            print(f"Found animal_type: {animal_type}")

            # Try to find category with this slug for this animal_type
            category = Category.objects.get(
                animal_type=animal_type, slug=target_slug, is_active=True
            )
            print(f"Found category: {category.name} (parent: {category.parent})")

            # Get products in this category (just this category, not subcategories)
            products = Product.objects.filter(category=category, is_active=True)
            print(f"Found {products.count()} products")

            return products.select_related("brand", "category").prefetch_related(
                "images", "variants"
            )

        except (AnimalType.DoesNotExist, Category.DoesNotExist) as e:
            print(f"ERROR: {e}")
            return Product.objects.none()


class ProductImageUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Upload product image to Cloudinary",
        manual_parameters=[
            openapi.Parameter(
                name="product_id",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                required=True,
                description="Product UUID",
            ),
            openapi.Parameter(
                name="image",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="Image file (max 5MB)",
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
                    },
                ),
            ),
            400: "Bad Request",
            401: "Unauthorized",
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

        result = cloudinary.uploader.upload(
            file,
            folder="products",
            resource_type="image",
        )

        image = ProductImage.objects.create(
            product=product,
            image_url=result["secure_url"],
            cloudinary_public_id=result["public_id"],
        )

        return Response(
            {
                "id": str(image.id),
                "url": image.image_url,
                "public_id": image.cloudinary_public_id,
            },
            status=status.HTTP_201_CREATED,
        )
