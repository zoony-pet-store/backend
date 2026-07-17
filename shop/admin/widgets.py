from django import forms
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
