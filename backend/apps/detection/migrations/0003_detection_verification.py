from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('detection', '0002_detection_crop_and_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='detection',
            name='verification',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
