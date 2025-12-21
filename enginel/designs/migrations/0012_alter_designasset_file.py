# Generated manually for storage parameter change

import designs.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('designs', '0011_add_notification_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='designasset',
            name='file',
            field=models.FileField(
                blank=True,
                help_text='Actual CAD file (STEP/IGES)',
                max_length=512,
                null=True,
                storage=designs.models.DesignAsset.get_file_storage,
                upload_to=designs.models.DesignAsset.upload_to_path
            ),
        ),
    ]
