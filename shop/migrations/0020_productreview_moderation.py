from django.db import migrations, models


def migrate_existing_reviews(apps, schema_editor):
    ProductReview = apps.get_model(
        "shop",
        "ProductReview",
    )

    for review in ProductReview.objects.all().only(
        "id",
        "rating_score",
        "reviewer_name",
        "title",
    ):
        review.rating_score = review.rating_score * 2

        if not review.reviewer_name and review.title:
            review.reviewer_name = review.title.strip()[:120]

        review.save(
            update_fields=[
                "rating_score",
                "reviewer_name",
            ]
        )


def reverse_existing_reviews(apps, schema_editor):
    ProductReview = apps.get_model("shop", "ProductReview")

    for review in ProductReview.objects.all().only(
        "id",
        "rating_score",
        "reviewer_name",
        "title",
    ):
        review.rating_score = max(1, min(5, round(review.rating_score / 2)))

        if not review.title and review.reviewer_name:
            review.title = review.reviewer_name[:200]

        review.save(update_fields=["rating_score", "title"])


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0019_productreviewimage"),
    ]

    operations = [
        migrations.AddField(
            model_name="productreview",
            name="moderation_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                default="approved",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="productreview",
            name="rejection_reason",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="productreview",
            name="reviewer_name",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="productreview",
            name="reviewer_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.RenameField(
            model_name="productreview",
            old_name="rating",
            new_name="rating_score",
        ),
        migrations.RunPython(migrate_existing_reviews, reverse_existing_reviews),
        migrations.AlterField(
            model_name="productreview",
            name="rating_score",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, 1),
                    (2, 2),
                    (3, 3),
                    (4, 4),
                    (5, 5),
                    (6, 6),
                    (7, 7),
                    (8, 8),
                    (9, 9),
                    (10, 10),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="productreview",
            name="title",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name="productreview",
            name="moderation_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                max_length=10,
            ),
        ),
        migrations.AddIndex(
            model_name="productreview",
            index=models.Index(
                fields=["product", "moderation_status"],
                name="product_rev_product_f98a5e_idx",
            ),
        ),
    ]
