from rest_framework import serializers

from ..models import Badge


class BadgeSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        fields = ["id", "name", "slug", "label", "color", "background_color"]

    def get_id(self, obj):
        return str(obj.id)
