from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0012_auto_20250330_1059'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='location',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ] 