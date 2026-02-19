from django.contrib.admin import AdminSite


class EcommerceAdminSite(AdminSite):
    site_header = "E-commerce Admin"
    site_title = "E-commerce"
    index_title = "Administration"
