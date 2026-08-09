from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0004_rename_featured_and_remove_dimensions"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="product",
            name="show_on_dashboard",
        ),
    ]
