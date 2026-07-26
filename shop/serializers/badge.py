from rest_framework import serializers

from ..models import Badge, translated_field


class BadgeSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        fields = ["id", "name", "slug", "label", "color", "background_color"]

    def get_id(self, obj):
        return str(obj.id)

    def get_label(self, obj):
        return translated_field(obj, "label")
