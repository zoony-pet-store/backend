from django import forms
from django.utils.html import format_html, json_script
from unfold.widgets import UnfoldAdminSelect2Widget


class AttributeSelectWidget(forms.Select):
    def __init__(self, *args, **kwargs):
        self.attribute_map = {}
        super().__init__(*args, **kwargs)

    def create_option(
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None,
    ):
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex=subindex,
            attrs=attrs,
        )

        if not value:
            return option

        attribute = getattr(value, "instance", None)

        if attribute is None:
            attribute = self.attribute_map.get(str(value))

        if attribute is None:
            return option

        option["attrs"]["data-attribute-type"] = attribute.type
        option["attrs"]["data-available-units"] = ",".join(
            attribute.available_units or []
        )

        return option


class AttributeValueSelectWidget(forms.Select):
    def __init__(self, *args, **kwargs):
        self.value_map = {}
        super().__init__(*args, **kwargs)

    def create_option(
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None,
    ):
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex=subindex,
            attrs=attrs,
        )

        if not value:
            return option

        attribute_value = getattr(value, "instance", None)

        if attribute_value is None:
            attribute_value = self.value_map.get(str(value))

        if attribute_value is None:
            return option

        option["attrs"]["data-attribute-id"] = str(attribute_value.attribute_id)

        return option


class MediaAssetSelectWidget(UnfoldAdminSelect2Widget):
    class Media:
        js = ("shop/admin/js/media_asset_select.js",)
        css = {
            "all": ("shop/admin/css/media_asset_select.css",),
        }

    def __init__(self, attrs=None):
        attrs = attrs or {}
        current_classes = attrs.get("class", "")
        attrs["class"] = f"{current_classes} media-asset-select".strip()
        super().__init__(attrs)

    def create_option(
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None,
    ):
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex=subindex,
            attrs=attrs,
        )

        media_asset = getattr(value, "instance", None)

        if media_asset is not None:
            option["attrs"]["data-image-url"] = media_asset.image_url
            option["attrs"]["data-source"] = media_asset.source

        return option


class CategoryTreeSelectWidget(forms.Widget):
    class Media:
        js = ("shop/admin/js/category_tree_select.js",)
        css = {
            "all": ("shop/admin/css/category_tree_select.css",),
        }

    def __init__(
        self,
        attrs=None,
        select_leaf_only=True,
        select_groups=False,
        animal_type_input_id="",
        category_queryset=None,
        animal_type_queryset=None,
    ):
        self.select_leaf_only = select_leaf_only
        self.select_groups = select_groups
        self.animal_type_input_id = animal_type_input_id
        self.category_queryset = category_queryset
        self.animal_type_queryset = animal_type_queryset
        self.selected_animal_type = ""
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        attrs = self.build_attrs(self.attrs, attrs)
        input_id = attrs.get("id") or f"id_{name}"
        selected_value = str(value or "")
        tree, selected_label = self.get_tree(selected_value)
        tree_script_id = f"{input_id}_tree_data"
        selected_label = selected_label or "Select category"

        return format_html(
            '{}{}<div class="category-tree-select" data-input-id="{}" '
            'data-placeholder="Select category" data-selected-label="{}" '
            'data-tree-script-id="{}" data-select-leaf-only="{}" '
            'data-select-groups="{}" data-animal-type-input-id="{}">'
            '<button type="button" class="category-tree-select__button" '
            'aria-expanded="false">'
            '<span class="category-tree-select__value">{}</span>'
            '<span class="category-tree-select__chevron">▾</span>'
            "</button>"
            '<div class="category-tree-select__panel" hidden>'
            '<div class="category-tree-select__groups"></div>'
            "</div>"
            "</div>",
            self.render_hidden_input(name, selected_value, input_id, attrs),
            json_script(tree, tree_script_id),
            input_id,
            selected_label,
            tree_script_id,
            str(self.select_leaf_only).lower(),
            str(self.select_groups).lower(),
            self.animal_type_input_id,
            selected_label,
        )

    def render_hidden_input(self, name, value, input_id, attrs):
        return forms.HiddenInput().render(name, value, {**attrs, "id": input_id})

    def value_from_datadict(self, data, files, name):
        return data.get(name)

    def get_tree(self, selected_value):
        from shop.models import AnimalType, Category

        category_queryset = (
            self.category_queryset
            if self.category_queryset is not None
            else Category.objects.all()
        )

        animal_type_queryset = (
            self.animal_type_queryset
            if self.animal_type_queryset is not None
            else AnimalType.objects.all()
        )

        categories = list(
            category_queryset.select_related("animal_type")
            .only(
                "id",
                "name",
                "sort_order",
                "parent_id",
                "animal_type_id",
                "is_active",
                "animal_type__id",
                "animal_type__name",
            )
            .order_by(
                "animal_type__name",
                "sort_order",
                "name",
            )
        )
        categories_by_animal = {
            animal_type.id: animal_type
            for animal_type in animal_type_queryset.only("id", "name").order_by("name")
        }
        children_by_parent = {}

        for category in categories:
            categories_by_animal.setdefault(
                category.animal_type_id, category.animal_type
            )
            children_by_parent.setdefault(category.parent_id, []).append(category)

        for children in children_by_parent.values():
            children.sort(key=lambda item: (item.sort_order, item.name.lower()))

        selected_label = ""
        groups = []
        animal_types = sorted(
            categories_by_animal.values(),
            key=lambda item: item.name.lower(),
        )

        for animal_type in animal_types:
            group_selected = (
                self.select_groups
                and not selected_value
                and str(animal_type.id) == self.selected_animal_type
            )
            roots = [
                category
                for category in children_by_parent.get(None, [])
                if category.animal_type_id == animal_type.id
            ]
            nodes = []

            for root in roots:
                node, node_selected_label = self.build_node(
                    category=root,
                    children_by_parent=children_by_parent,
                    selected_value=selected_value,
                    path=[root.name],
                )
                nodes.append(node)

                if node_selected_label:
                    selected_label = f"{animal_type.name} / {node_selected_label}"

            if group_selected:
                selected_label = animal_type.name

            if nodes or self.select_groups:
                groups.append(
                    {
                        "id": str(animal_type.id),
                        "name": animal_type.name,
                        "selected": group_selected,
                        "expanded": group_selected
                        or any(node["expanded"] for node in nodes),
                        "children": nodes,
                    }
                )

        return groups, selected_label

    def build_node(self, category, children_by_parent, selected_value, path):
        node_selected_label = ""
        category_id = str(category.id)
        selected = category_id == selected_value
        children = []

        for child in children_by_parent.get(category.id, []):
            child_node, child_selected_label = self.build_node(
                category=child,
                children_by_parent=children_by_parent,
                selected_value=selected_value,
                path=[*path, child.name],
            )
            children.append(child_node)

            if child_selected_label:
                node_selected_label = child_selected_label

        if selected:
            node_selected_label = " / ".join(path)

        expanded = selected or bool(node_selected_label)

        has_active_children = any(
            child.is_active for child in children_by_parent.get(category.id, [])
        )

        selectable = (
            category.is_active and not has_active_children
            if self.select_leaf_only
            else True
        )

        return {
            "id": category_id,
            "animal_type_id": str(category.animal_type_id),
            "name": category.name,
            "path": " / ".join(path),
            "selected": selected,
            "expanded": expanded,
            "active": category.is_active,
            "selectable": selectable,
            "children": children,
        }, node_selected_label
