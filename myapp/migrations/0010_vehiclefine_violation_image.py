# Generated by Django 4.2.18 on 2025-03-27 09:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0009_vehiclemodificationrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehiclefine',
            name='violation_image',
            field=models.ImageField(blank=True, help_text='Upload an image of the violation', null=True, upload_to='violation_images/'),
        ),
    ]
