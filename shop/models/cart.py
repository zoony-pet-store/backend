from django.core.exceptions import ValidationError
from django.db import models

from .customer import Customer
from .product_variant import ProductVariant
class Cart(models.Model):
    """User shopping cart."""

    user = models.OneToOneField(Customer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.select_related("variant"))

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    def __str__(self):
        return f"Cart for {self.user.email}"


class CartItem(models.Model):
    """
    Cart item.

    Important:
    CartItem references ProductVariant, not Product.
    User adds exact selected variant to cart.
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "variant"],
                name="unique_variant_per_cart",
            )
        ]

    def clean(self):
        if self.variant_id:
            if not self.variant.is_active or not self.variant.product.is_active:
                raise ValidationError({"variant": "Selected variant is not available."})

            if self.quantity > self.variant.stock:
                raise ValidationError(
                    {"quantity": "Requested quantity is greater than available stock."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        return self.variant.price * self.quantity

    def __str__(self):
        return f"{self.variant.product.name} - {self.variant.sku} x {self.quantity}"
