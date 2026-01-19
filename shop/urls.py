from django.urls import path, include
from . import views

app_name = "shop"

urlpatterns = [
    path("auth/", include("shop.auth_urls")),
    # ========== DASHBOARD ==========
    path("dashboard", views.DashboardView.as_view(), name="dashboard"),
    # ========== PRODUCTS ==========
    # Product collections
    path("products", views.ProductListView.as_view(), name="product-list"),
    path(
        "products/featured",
        views.FeaturedProductsView.as_view(),
        name="featured-products",
    ),
    path("products/search", views.ProductSearchView.as_view(), name="product-search"),
    # Specific product operations
    path(
        "products/<uuid:product_id>",
        views.ProductDetailView.as_view(),
        name="product-detail",
    ),
    path(
        "products/<uuid:product_id>/related",
        views.RelatedProductsView.as_view(),
        name="related-products",
    ),
    # ========== BRANDS ==========
    path("brands", views.BrandListView.as_view(), name="brand-list"),
    path(
        "brands/<slug:brand_slug>",
        views.BrandDetailView.as_view(),
        name="brand-detail",
    ),
    # ========== ANIMAL TYPES & CATEGORIES ==========
    # GET /api/cats/food/products/ - products in category
    path(
        "<slug:animal_type_slug>/<path:category_path>/products",
        views.CategoryProductsView.as_view(),
        name="category-products",
    ),
    # GET /api/cats/food/ - specific category with subcategories
    # GET /api/cats/food/dry-food/ - deeper category
    path(
        "<slug:animal_type_slug>/<path:category_path>",
        views.CategoryDetailView.as_view(),
        name="category-detail",
    ),
    # GET /api/cats/ - all categories for cats
    path(
        "<slug:animal_type_slug>",
        views.AnimalTypeCategoriesView.as_view(),
        name="animal-type-categories",
    ),
]
