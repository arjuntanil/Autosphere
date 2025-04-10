# Generated by Django 5.1.7 on 2025-03-30 15:56

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0016_rename_is_verified_passwordresetverification_is_used_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehiclefine',
            name='payment_receipt_number',
            field=models.CharField(blank=True, max_length=50, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='vehiclefine',
            name='razorpay_order_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='vehiclefine',
            name='razorpay_payment_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='vehiclefine',
            name='razorpay_signature',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='vehiclefine',
            name='payment_status',
            field=models.CharField(choices=[('Unpaid', 'Unpaid'), ('Paid', 'Paid'), ('Contested', 'Contested'), ('Waived', 'Waived'), ('Processing', 'Processing')], default='Unpaid', max_length=20),
        ),
        migrations.CreateModel(
            name='FinePayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='INR', max_length=3)),
                ('status', models.CharField(choices=[('created', 'Created'), ('authorized', 'Authorized'), ('captured', 'Captured'), ('refunded', 'Refunded'), ('failed', 'Failed')], default='created', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('razorpay_order_id', models.CharField(blank=True, max_length=100, null=True)),
                ('razorpay_payment_id', models.CharField(blank=True, max_length=100, null=True)),
                ('razorpay_signature', models.CharField(blank=True, max_length=255, null=True)),
                ('receipt', models.CharField(blank=True, max_length=100, null=True)),
                ('failure_reason', models.TextField(blank=True, null=True)),
                ('fine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='myapp.vehiclefine')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fine_payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Fine Payment',
                'verbose_name_plural': 'Fine Payments',
                'ordering': ['-created_at'],
            },
        ),
    ]
