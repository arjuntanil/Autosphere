# Generated by Django 4.2.18 on 2025-03-28 15:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0010_vehiclefine_violation_image'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='vehiclefine',
            name='violation_image',
        ),
        migrations.AddField(
            model_name='vehiclefine',
            name='violation_document',
            field=models.FileField(blank=True, help_text='Upload a PDF document related to the violation (optional)', null=True, upload_to='violation_documents/'),
        ),
    ]
