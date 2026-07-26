from ..models import ProductAttribute, translated_field


def format_decimal_for_api(value):
    if value is None:
        return None

    normalized_value = value.normalize()
    display_value = format(normalized_value, "f")

    if "." in display_value:
        display_value = display_value.rstrip("0").rstrip(".")

    return display_value


def serialize_numeric_attribute_value(item):
    return {
        "type": ProductAttribute.AttributeType.NUMERIC,
        "display_value": item.display_value,
        "value": float(item.value_numeric) if item.value_numeric is not None else None,
        "value_decimal": (
            str(item.value_numeric) if item.value_numeric is not None else None
        ),
        "unit": item.unit or None,
    }


def serialize_select_attribute_value(item):
    return {
        "type": ProductAttribute.AttributeType.SELECT,
        "display_value": translated_field(item.value, "value") if item.value_id else "",
        "value_id": str(item.value_id) if item.value_id else None,
        "value": translated_field(item.value, "value") if item.value_id else None,
        "slug": item.value.slug if item.value_id else None,
    }


def serialize_variant_attribute_raw(item):
    attribute = item.attribute

    if attribute.type == ProductAttribute.AttributeType.NUMERIC:
        return serialize_numeric_attribute_value(item)

    return serialize_select_attribute_value(item)
