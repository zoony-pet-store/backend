from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Product, Customer, Category, AnimalType
from .serializers import (
    UserRegisterSerializer,
    LoginSerializer,
    GoogleAuthSerializer,
    CategoryMinimalSerializer,
    CategoryDetailSerializer,
    CategoryCreateUpdateSerializer,
    CategoryTreeSerializer,
    AnimalTypeCreateSerializer,
    AnimalTypeSerializer,
)
from .services.category_service import CategoryTreeService


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


# AnimalType Views
class AnimalTypeListView(generics.ListAPIView):
    """List all active animal types"""

    permission_classes = [permissions.AllowAny]
    queryset = AnimalType.objects.filter(is_active=True)
    serializer_class = AnimalTypeSerializer


class AnimalTypeDetailView(generics.RetrieveAPIView):
    """Retrieve specific animal type details"""

    permission_classes = [permissions.AllowAny]
    queryset = AnimalType.objects.filter(is_active=True)
    serializer_class = AnimalTypeSerializer
    lookup_field = "slug"


class AnimalTypeCreateView(generics.CreateAPIView):
    """Create new animal type (Admin only)"""

    permission_classes = [permissions.IsAdminUser]
    queryset = AnimalType.objects.all()
    serializer_class = AnimalTypeCreateSerializer


class AnimalTypeUpdateView(generics.UpdateAPIView):
    """Update animal type (Admin only)"""

    permission_classes = [permissions.IsAdminUser]
    queryset = AnimalType.objects.all()
    serializer_class = AnimalTypeSerializer
    lookup_field = "slug"


class AnimalTypeDeleteView(generics.DestroyAPIView):
    """Delete animal type (Admin only)"""

    permission_classes = [permissions.IsAdminUser]
    queryset = AnimalType.objects.all()
    serializer_class = AnimalTypeSerializer
    lookup_field = "slug"

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


# Category Views
class CategoryTreeView(generics.GenericAPIView):
    """Get category tree with configurable depth"""

    permission_classes = [permissions.AllowAny]

    def get(self, request, animal_type_slug):
        depth = int(request.query_params.get("depth", 2))

        try:
            AnimalType.objects.get(slug=animal_type_slug, is_active=True)
            tree_data = CategoryTreeService.get_full_tree(animal_type_slug, depth)
            serializer = CategoryTreeSerializer(tree_data)
            return Response(serializer.data)
        except AnimalType.DoesNotExist:
            return Response(
                {"error": "Animal type not found"}, status=status.HTTP_404_NOT_FOUND
            )


class CategoryDetailView(generics.RetrieveAPIView):
    """Retrieve detailed category information"""

    permission_classes = [permissions.AllowAny]
    serializer_class = CategoryDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Category.objects.filter(
            is_active=True,
            animal_type__slug=self.kwargs["animal_type_slug"],
            animal_type__is_active=True,
        ).select_related("animal_type", "parent")


class CategoryCreateView(generics.CreateAPIView):
    """Create new category (Admin only)"""

    permission_classes = [permissions.IsAdminUser]
    queryset = Category.objects.all()
    serializer_class = CategoryCreateUpdateSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        CategoryTreeService.clear_cache(instance.animal_type.slug)


class CategoryUpdateView(generics.UpdateAPIView):
    """Update category (Admin only)"""

    permission_classes = [permissions.IsAdminUser]
    queryset = Category.objects.all()
    serializer_class = CategoryCreateUpdateSerializer
    lookup_field = "slug"

    def perform_update(self, serializer):
        instance = serializer.save()
        CategoryTreeService.clear_cache(instance.animal_type.slug)


class CategoryDeleteView(generics.DestroyAPIView):
    """Delete category (Admin only)"""

    permission_classes = [permissions.IsAdminUser]
    queryset = Category.objects.all()
    serializer_class = CategoryDetailSerializer
    lookup_field = "slug"

    def perform_destroy(self, instance):
        animal_type_slug = instance.animal_type.slug
        instance.is_active = False
        instance.save()
        CategoryTreeService.clear_cache(animal_type_slug)


class SubcategoriesListView(generics.ListAPIView):
    """List subcategories for specific category"""

    permission_classes = [permissions.AllowAny]
    serializer_class = CategoryMinimalSerializer

    def get_queryset(self):
        return Category.objects.filter(
            animal_type__slug=self.kwargs["animal_type_slug"],
            parent__slug=self.kwargs["category_slug"],
            is_active=True,
        ).order_by("sort_order", "name")


class LeafCategoriesView(generics.ListAPIView):
    """Get all leaf categories (for filters)"""

    permission_classes = [permissions.AllowAny]
    serializer_class = CategoryMinimalSerializer

    def get_queryset(self):
        return CategoryTreeService.get_leaf_categories(self.kwargs["animal_type_slug"])


class CategorySearchView(generics.ListAPIView):
    """Search categories by name"""

    permission_classes = [permissions.AllowAny]
    serializer_class = CategoryMinimalSerializer

    def get_queryset(self):
        search_query = self.request.query_params.get("q", "")
        animal_type_slug = self.kwargs.get("animal_type_slug")

        queryset = Category.objects.filter(is_active=True, animal_type__is_active=True)

        if animal_type_slug:
            queryset = queryset.filter(animal_type__slug=animal_type_slug)

        if search_query:
            queryset = queryset.filter(name__icontains=search_query)

        return queryset.order_by("sort_order", "name")


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def cache_test(request):
    """Test Redis cache functionality"""
    from django.core.cache import cache
    import time

    # Test data
    test_data = {
        "timestamp": time.time(),
        "message": "Hello from Redis!",
        "status": "cached",
    }

    # Try to write to cache
    try:
        cache.set("test_key", test_data, 60)  # 60 seconds
        cached_value = cache.get("test_key")

        # Get cache info without using protected members
        cache_info = {
            "backend": cache.__class__.__name__,
            "location": "redis://127.0.0.1:6379/1",
        }

        return Response(
            {
                "redis_working": cached_value is not None,
                "cached_data": cached_value,
                "cache_info": cache_info,
                "status": "SUCCESS" if cached_value else "FAILED",
            }
        )
    except Exception as e:
        return Response(
            {"redis_working": False, "error": str(e), "status": "ERROR"}, status=500
        )


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def clear_categories_cache(request, animal_type_slug):
    """Clear categories cache (Admin only)"""
    # CategoryTreeService.clear_cache(animal_type_slug)
    # return Response({"status": "cache cleared"})
    return JsonResponse({"status": "Cache clearing disabled temporarily"})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def category_stats(request, animal_type_slug):
    """Get category statistics"""
    try:
        total_categories = Category.objects.filter(
            animal_type__slug=animal_type_slug, is_active=True
        ).count()

        leaf_categories = CategoryTreeService.get_leaf_categories(
            animal_type_slug
        ).count()

        return Response(
            {
                "total_categories": total_categories,
                "leaf_categories": leaf_categories,
                "animal_type": animal_type_slug,
            }
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def api_slugs_info(request):
    """Повертає інформацію про доступні slug для тестування"""
    animal_types = AnimalType.objects.filter(is_active=True)

    data = {
        "animal_types": [],
        "testing_examples": [
            "/api/categories/dogs/food/subcategories/",
            "/api/categories/dogs/care-hygiene/subcategories/",
            "/api/categories/cats/food/subcategories/",
            "/api/categories/cats/care-hygiene/subcategories/",
        ],
    }

    for animal in animal_types:
        animal_data = {"name": animal.name, "slug": animal.slug, "categories": []}

        categories = Category.objects.filter(
            animal_type=animal, parent__isnull=True
        ).select_related("animal_type")

        for category in categories:
            category_data = {
                "name": category.name,
                "slug": category.slug,
                "subcategories": list(
                    Category.objects.filter(parent=category).values("name", "slug")
                ),
            }
            animal_data["categories"].append(category_data)

        data["animal_types"].append(animal_data)

    return Response(data)
