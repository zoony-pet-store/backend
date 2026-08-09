from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0003_productimage_cloudinary_public_id"),
    ]

    operations = [
        migrations.RenameField(
            model_name="product",
            old_name="is_featured",
            new_name="show_on_dashboard",
        ),
        migrations.RemoveField(
            model_name="productvariant",
            name="dimensions",
        ),
    ]
