from django.urls import path
from . import views
from .views import RegisterView, LoginView, GoogleAuthView, CustomTokenRefreshView

app_name = "shop"

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("google-auth/", GoogleAuthView.as_view(), name="google_auth"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    # Animal Types CRUD
    path(
        "animal-types/", views.AnimalTypeListView.as_view(), name="animal-type-list"
    ),
    path(
        "animal-types/create/",
        views.AnimalTypeCreateView.as_view(),
        name="animal-type-create",
    ),
    path(
        "animal-types/<slug:slug>/",
        views.AnimalTypeDetailView.as_view(),
        name="animal-type-detail",
    ),
    path(
        "animal-types/<slug:slug>/update/",
        views.AnimalTypeUpdateView.as_view(),
        name="animal-type-update",
    ),
    path(
        "animal-types/<slug:slug>/delete/",
        views.AnimalTypeDeleteView.as_view(),
        name="animal-type-delete",
    ),
    # Categories CRUD
    path(
        "categories/<str:animal_type_slug>/tree/",
        views.CategoryTreeView.as_view(),
        name="category-tree",
    ),
    path(
        "categories/<str:animal_type_slug>/create/",
        views.CategoryCreateView.as_view(),
        name="category-create",
    ),
    path(
        "categories/<str:animal_type_slug>/<slug:slug>/",
        views.CategoryDetailView.as_view(),
        name="category-detail",
    ),
    path(
        "categories/<str:animal_type_slug>/<slug:slug>/update/",
        views.CategoryUpdateView.as_view(),
        name="category-update",
    ),
    path(
        "categories/<str:animal_type_slug>/<slug:slug>/delete/",
        views.CategoryDeleteView.as_view(),
        name="category-delete",
    ),
    # Additional endpoints
    path(
        "categories/<str:animal_type_slug>/<slug:category_slug>/subcategories/",
        views.SubcategoriesListView.as_view(),
        name="subcategories",
    ),
    path(
        "categories/<str:animal_type_slug>/leaves/",
        views.LeafCategoriesView.as_view(),
        name="leaf-categories",
    ),
    path(
        "categories/<str:animal_type_slug>/search/",
        views.CategorySearchView.as_view(),
        name="category-search",
    ),
    path(
        "categories/<str:animal_type_slug>/stats/",
        views.category_stats,
        name="category-stats",
    ),
    path("slugs-info/", views.api_slugs_info, name="slugs-info"),
    # Cache testing
    path("cache-test/", views.cache_test, name="cache-test"),
    # Admin utilities
    path(
        "admin/clear-cache/<str:animal_type_slug>/",
        views.clear_categories_cache,
        name="clear-cache",
    ),
]
