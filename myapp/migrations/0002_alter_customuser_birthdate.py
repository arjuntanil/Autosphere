# Generated by Django 5.1.7 on 2025-03-09 15:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='birthdate',
            field=models.DateField(blank=True, null=True),
        ),
    ]
