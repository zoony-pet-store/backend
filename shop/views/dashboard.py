from datetime import timedelta

from django.db.models import Avg, Count, F, Q
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers import ProductCardSerializer
from .product import get_product_base_queryset


def get_dashboard_product_queryset():
    approved_reviews_filter = Q(
        reviews__is_active=True,
        reviews__moderation_status="approved",
    )

    return get_product_base_queryset().annotate(
        dashboard_rating_score=Avg("reviews__rating_score", filter=approved_reviews_filter),
        dashboard_review_count=Count(
            "reviews",
            filter=approved_reviews_filter,
            distinct=True,
        ),
    )


class DashboardView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        thirty_days_ago = timezone.now() - timedelta(days=30)

        base_queryset = get_dashboard_product_queryset()

        new_arrivals = base_queryset.filter(
            created_at__gte=thirty_days_ago,
        ).order_by(
            "-created_at"
        )[:20]

        best_sellers = (
            base_queryset.filter(
                Q(
                    badges__is_active=True,
                    badges__slug__in=["best_seller", "bestseller"],
                )
                | Q(dashboard_rating_score__gte=9, dashboard_review_count__gte=10)
            )
            .distinct()
            .order_by("-dashboard_rating_score", "-dashboard_review_count")[:20]
        )

        discounted_products = (
            base_queryset.filter(
                variants__is_active=True,
                variants__stock__gt=0,
                variants__old_price__isnull=False,
                variants__old_price__gt=F("variants__price"),
            )
            .distinct()
            .order_by("-created_at")[:20]
        )

        context = {"request": request}

        data = {
            "new_arrivals": ProductCardSerializer(
                new_arrivals,
                many=True,
                context=context,
            ).data,
            "best_sellers": ProductCardSerializer(
                best_sellers,
                many=True,
                context=context,
            ).data,
            "discounted_products": ProductCardSerializer(
                discounted_products,
                many=True,
                context=context,
            ).data,
        }

        return Response(data)
