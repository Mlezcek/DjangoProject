# Generated by Django 5.1.3 on 2025-01-14 16:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DjangoProject', '0010_delete_customgroup'),
    ]

    operations = [
        migrations.AddField(
            model_name='grupa',
            name='is_predefined',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='grupa',
            name='nazwa',
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.CreateModel(
            name='GrupaCondition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('condition_type', models.CharField(choices=[('purchase_item', 'Klienci kupili przedmiot'), ('spend_last_days', 'Klienci wydali kwotę w ostatnich X dniach'), ('spend_total', 'Klienci całkowicie wydali kwotę'), ('account_age', 'Konto istnieje X dni')], max_length=20)),
                ('min_ilosc', models.PositiveIntegerField(blank=True, null=True)),
                ('max_ilosc', models.PositiveIntegerField(blank=True, null=True)),
                ('min_wydano', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('max_wydano', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('days_last', models.PositiveIntegerField(blank=True, null=True)),
                ('min_wydano_total', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('max_wydano_total', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('min_dni', models.PositiveIntegerField(blank=True, null=True)),
                ('max_dni', models.PositiveIntegerField(blank=True, null=True)),
                ('grupa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conditions', to='DjangoProject.grupa')),
                ('produkt', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='DjangoProject.produkt')),
            ],
        ),
    ]
