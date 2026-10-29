import apps.detection.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('detection', '0003_detection_verification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='detection',
            name='image',
            field=models.ImageField(upload_to=apps.detection.models.detection_photo_path),
        ),
    ]
