# Generated migration to remove units field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('designs', '0013_add_preview_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='designasset',
            name='units',
        ),
    ]
