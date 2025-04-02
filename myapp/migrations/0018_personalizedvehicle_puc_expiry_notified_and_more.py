# Generated by Django 5.1.7 on 2025-04-02 16:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0017_vehiclefine_payment_receipt_number_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='personalizedvehicle',
            name='puc_expiry_notified',
            field=models.BooleanField(default=False, help_text='Indicates if notification has been sent for PUC expiry'),
        ),
        migrations.AddField(
            model_name='personalizedvehicle',
            name='registration_expiry_notified',
            field=models.BooleanField(default=False, help_text='Indicates if notification has been sent for registration expiry'),
        ),
    ]
