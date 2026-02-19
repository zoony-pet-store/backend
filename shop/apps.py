from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class ShopConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shop"


class EcommerceAdminConfig(AdminConfig):
    default_site = "shop.admin.EcommerceAdminSite"

    def ready(self):
        pass
