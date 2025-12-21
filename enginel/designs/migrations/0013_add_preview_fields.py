# Generated manually for preview file support

import designs.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('designs', '0012_alter_designasset_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='designasset',
            name='preview_file',
            field=models.FileField(
                blank=True,
                help_text='Web-optimized preview file (GLB/GLTF) for Three.js viewing',
                max_length=512,
                null=True,
                storage=designs.models.DesignAsset.get_file_storage,
                upload_to=designs.models.DesignAsset.upload_to_path
            ),
        ),
        migrations.AddField(
            model_name='designasset',
            name='preview_s3_key',
            field=models.CharField(
                blank=True,
                help_text='S3 key for preview file',
                max_length=512,
                null=True
            ),
        ),
    ]
