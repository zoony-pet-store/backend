from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Product
from ..serializers import ProductReviewCreateSerializer, ProductReviewItemSerializer


def update_product_review_stats(product):
    stats = product.reviews.filter(is_active=True).aggregate(
        avg_rating=Avg("rating"),
        review_count=Count("id"),
    )

    product.rating = stats["avg_rating"] or 0
    product.review_count = stats["review_count"] or 0
    product.save(update_fields=["rating", "review_count"])


class ProductReviewCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create product review",
        request_body=ProductReviewCreateSerializer,
        responses={
            201: ProductReviewItemSerializer,
            400: "Bad Request",
            401: "Unauthorized",
            404: "Product not found",
        },
    )
    def post(self, request, product_id):
        product = get_object_or_404(
            Product,
            id=product_id,
            is_active=True,
        )

        serializer = ProductReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review = serializer.save(
            product=product,
            user=request.user,
            is_active=True,
            is_verified=False,
        )

        update_product_review_stats(product)

        response_serializer = ProductReviewItemSerializer(
            review,
            context={"request": request},
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )
