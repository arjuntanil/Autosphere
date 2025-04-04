# Generated by Django 4.2.18 on 2025-04-04 04:21

from django.db import migrations, models
import myapp.models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0019_alter_personalizedvehicle_puc_expiry_notified_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vehiclefine',
            name='violation_document',
            field=models.FileField(blank=True, help_text='Upload a PDF document or image (JPG, JPEG, PNG) related to the violation (optional)', null=True, upload_to=myapp.models.VehicleFine.get_violation_document_path),
        ),
    ]
