from django.core.cache import cache
from ..models import Category


class CategoryTreeService:

    @staticmethod
    def get_full_tree(animal_type_slug: str, max_depth: int = 3):
        # cache_key = f"full_category_tree_{animal_type_slug}_depth{max_depth}"
        # cached = cache.get(cache_key)
        # if cached:
        #     return cached

        try:
            all_categories = (
                Category.objects.filter(
                    animal_type__slug=animal_type_slug,
                    animal_type__is_active=True,
                    is_active=True,
                    level__lte=max_depth,
                )
                .select_related("animal_type")
                .order_by("level", "sort_order", "name")
            )

            tree = CategoryTreeService._build_tree_structure(all_categories)
            # cache.set(cache_key, tree, timeout=3600)
            return tree
        except Exception:
            return []

    @staticmethod
    def _build_tree_structure(categories):
        category_dict = {}
        root_categories = []

        for category in categories:
            category_dict[category.id] = {"category": category, "children": []}

        for category in categories:
            node = category_dict[category.id]
            if category.parent_id and category.parent_id in category_dict:
                category_dict[category.parent_id]["children"].append(node)
            else:
                root_categories.append(node)

        return root_categories

    @staticmethod
    def get_breadcrumbs(category_slug: str, animal_type_slug: str):
        try:
            category = Category.objects.select_related("animal_type", "parent").get(
                slug=category_slug, animal_type__slug=animal_type_slug, is_active=True
            )

            breadcrumbs = []
            current = category
            while current:
                breadcrumbs.insert(
                    0,
                    {
                        "name": current.name,
                        "slug": current.slug,
                        "level": current.level,
                        "url": f"/{current.animal_type.slug}/{current.slug}/",
                    },
                )
                current = current.parent

            breadcrumbs.insert(
                0,
                {
                    "name": category.animal_type.name,
                    "slug": category.animal_type.slug,
                    "level": 0,
                    "url": f"/{category.animal_type.slug}/",
                },
            )

            return breadcrumbs
        except Category.DoesNotExist:
            return []

    @staticmethod
    def get_leaf_categories(animal_type_slug: str):
        return (
            Category.objects.filter(animal_type__slug=animal_type_slug, is_active=True)
            .exclude(children__isnull=False)
            .order_by("sort_order", "name")
        )

    @staticmethod
    def clear_cache(animal_type_slug: str):
        # cache_keys = [
        #     f"full_category_tree_{animal_type_slug}_depth1",
        #     f"full_category_tree_{animal_type_slug}_depth2",
        #     f"full_category_tree_{animal_type_slug}_depth3",
        # ]
        # for key in cache_keys:
        #     cache.delete(key)
        pass
