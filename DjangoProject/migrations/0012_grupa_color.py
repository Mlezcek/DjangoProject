# Generated by Django 5.1.3 on 2025-01-14 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DjangoProject', '0011_grupa_is_predefined_alter_grupa_nazwa_grupacondition'),
    ]

    operations = [
        migrations.AddField(
            model_name='grupa',
            name='color',
            field=models.CharField(default='#007bff', help_text='Wprowadź kolor w formacie HEX, np. #FF5733', max_length=7),
        ),
    ]
