from django.contrib.admin.apps import AdminConfig


class EcommerceAdminConfig(AdminConfig):
    default_site = "shop.admin_site.EcommerceAdminSite"
