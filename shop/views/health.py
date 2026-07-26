from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.translation import gettext as _
from django.shortcuts import render

from ..models import Category, Customer, Product


def health_check(request):
    return JsonResponse({"status": "ok", "message": _("Service is healthy")})


def index(request: HttpRequest) -> HttpResponse:
    num_products = Product.objects.count()
    count_users = Customer.objects.count()
    count_categories = Category.objects.count()

    context = {
        "num_products": num_products,
        "count_users": count_users,
        "count_categories": count_categories,
    }

    return render(request, "home_page.html", context)
