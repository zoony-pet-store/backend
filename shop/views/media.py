import cloudinary.uploader
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Product, ProductImage, ProductVariant


class ProductImageUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Upload product or variant image to Cloudinary",
        manual_parameters=[
            openapi.Parameter(
                name="product_id",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                required=True,
                description="Product UUID",
            ),
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                required=False,
                description=(
                    "Variant UUID. Optional. If provided, image belongs to variant."
                ),
            ),
            openapi.Parameter(
                name="image",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="Image file, max 5MB",
            ),
            openapi.Parameter(
                name="alt_text",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                required=False,
                description="Image alt text",
            ),
            openapi.Parameter(
                name="is_main",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description="Set image as main image",
            ),
            openapi.Parameter(
                name="display_order",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="Display order",
            ),
        ],
        responses={
            201: openapi.Response(
                description="Uploaded",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING),
                        "url": openapi.Schema(type=openapi.TYPE_STRING),
                        "public_id": openapi.Schema(type=openapi.TYPE_STRING),
                        "product_id": openapi.Schema(type=openapi.TYPE_STRING),
                        "variant_id": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_main": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "display_order": openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
            ),
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found",
        },
    )
    def post(self, request):
        if "image" not in request.FILES:
            return Response(
                {"error": "No image provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["image"]

        if file.size > 5 * 1024 * 1024:
            return Response(
                {"error": "Image too large (max 5MB)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product_id = request.data.get("product_id")

        if not product_id:
            return Response(
                {"error": "product_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = get_object_or_404(Product, id=product_id)
        variant_id = request.data.get("variant_id")

        variant = None

        if variant_id:
            variant = get_object_or_404(
                ProductVariant,
                id=variant_id,
                product=product,
            )

        alt_text = request.data.get("alt_text", "")

        is_main_raw = request.data.get("is_main", "false")
        is_main = str(is_main_raw).lower() in ["true", "1", "yes", "on"]

        display_order_raw = request.data.get("display_order", 0)

        try:
            display_order = int(display_order_raw)
        except (TypeError, ValueError):
            return Response(
                {"error": "display_order must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = cloudinary.uploader.upload(
            file,
            folder="products",
            resource_type="image",
        )

        if is_main:
            if variant:
                ProductImage.objects.filter(
                    product=product,
                    variant=variant,
                    is_main=True,
                ).update(is_main=False)
            else:
                ProductImage.objects.filter(
                    product=product,
                    variant__isnull=True,
                    is_main=True,
                ).update(is_main=False)

        image = ProductImage.objects.create(
            product=product,
            variant=variant,
            image_url=result["secure_url"],
            alt_text=alt_text,
            is_main=is_main,
            display_order=display_order,
            cloudinary_public_id=result["public_id"],
        )

        return Response(
            {
                "id": str(image.id),
                "url": image.image_url,
                "public_id": image.cloudinary_public_id,
                "product_id": str(product.id),
                "variant_id": str(variant.id) if variant else None,
                "is_main": image.is_main,
                "display_order": image.display_order,
            },
            status=status.HTTP_201_CREATED,
        )
