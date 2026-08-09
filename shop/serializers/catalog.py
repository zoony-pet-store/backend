from django.db.models import Prefetch
from rest_framework import serializers

from ..models import AnimalType, Brand, Category, translated_field


class AnimalTypeSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = AnimalType
        fields = ["id", "name", "slug", "icon", "is_active"]
        read_only_fields = ["id"]

    def get_name(self, obj):
        return translated_field(obj, "name")


class AnimalTypeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalType
        fields = ["name", "slug", "icon", "is_active"]


class CategoryDetailSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    animal_type = AnimalTypeSerializer(read_only=True)
    parent = serializers.SerializerMethodField()
    breadcrumbs = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image_url",
            "animal_type",
            "parent",
            "level",
            "sort_order",
            "breadcrumbs",
            "children_count",
            "url",
            "created_at",
        ]

    def get_parent(self, obj):
        if not obj.parent:
            return None

        return {
            "id": str(obj.parent.id),
            "name": translated_field(obj.parent, "name"),
            "slug": obj.parent.slug,
        }

    def get_name(self, obj):
        return translated_field(obj, "name")

    def get_description(self, obj):
        return translated_field(obj, "description")

    def get_breadcrumbs(self, obj):
        breadcrumbs = []
        current = obj

        while current:
            breadcrumbs.append(
                {
                    "id": str(current.id),
                    "name": translated_field(current, "name"),
                    "slug": current.slug,
                }
            )
            current = current.parent

        return list(reversed(breadcrumbs))

    def get_children_count(self, obj):
        return obj.children.filter(is_active=True).count()

    def get_url(self, obj):
        return f"/{obj.animal_type.slug}/{obj.slug}/"


class CategoryCreateUpdateSerializer(serializers.ModelSerializer):
    animal_type = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=AnimalType.objects.all(),
    )
    parent = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Category
        fields = [
            "name",
            "slug",
            "description",
            "parent",
            "animal_type",
            "image_url",
            "is_active",
            "sort_order",
        ]
        extra_kwargs = {"slug": {"required": False}}


class CategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["name", "slug", "image_url"]

    def get_name(self, obj):
        return translated_field(obj, "name")


class CategoryTreeSerializer(CategorySerializer):
    subcategories = serializers.SerializerMethodField()

    class Meta(CategorySerializer.Meta):
        fields = ["name", "slug", "image_url", "subcategories"]

    def get_subcategories(self, obj):
        if hasattr(obj, "prefetched_children"):
            children = obj.prefetched_children
        elif hasattr(obj, "children"):
            children = obj.children.filter(is_active=True)
        else:
            children = Category.objects.filter(parent=obj, is_active=True)

        max_depth = self.context.get("max_depth", 3)
        current_depth = self.context.get("current_depth", 0)

        if current_depth >= max_depth:
            return []

        child_context = self.context.copy()
        child_context["current_depth"] = current_depth + 1

        return CategoryTreeSerializer(
            children,
            many=True,
            context=child_context,
        ).data

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if instance.parent is None:
            representation.pop("image_url", None)

        return representation


class CategoryWithChildrenSerializer(CategorySerializer):
    subcategories = serializers.SerializerMethodField()

    class Meta(CategorySerializer.Meta):
        fields = ["name", "slug", "image_url", "subcategories"]

    def get_subcategories(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True).data


class AnimalTypeWithCategoriesSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    icon = serializers.CharField(read_only=True)

    class Meta:
        model = AnimalType
        fields = ["name", "slug", "icon", "image_url", "categories"]

    def get_name(self, obj):
        return translated_field(obj, "name")

    def get_categories(self, obj):
        root_categories = obj.categories.filter(
            parent__isnull=True,
            is_active=True,
        ).prefetch_related(
            "translations",
            Prefetch(
                "children",
                queryset=Category.objects.filter(is_active=True).prefetch_related(
                    "translations",
                    Prefetch(
                        "children",
                        queryset=Category.objects.filter(
                            is_active=True
                        ).prefetch_related("translations"),
                    ),
                ),
            ),
        )

        max_depth = self.context.get("max_depth", 2)

        return CategoryTreeSerializer(
            root_categories,
            many=True,
            context={"max_depth": max_depth, "current_depth": 0},
        ).data


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "description", "logo_url", "is_active"]


class BrandMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "logo_url"]
