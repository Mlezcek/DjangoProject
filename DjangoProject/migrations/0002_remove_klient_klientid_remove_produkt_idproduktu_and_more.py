# Generated by Django 5.1.3 on 2024-12-12 17:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DjangoProject', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='klient',
            name='klientid',
        ),
        migrations.RemoveField(
            model_name='produkt',
            name='idproduktu',
        ),
        migrations.RemoveField(
            model_name='uzytkownik',
            name='uzytkownikid',
        ),
        migrations.AddField(
            model_name='klient',
            name='id',
            field=models.AutoField(default=0, primary_key=True, serialize=False),
        ),
        migrations.AddField(
            model_name='produkt',
            name='id',
            field=models.AutoField(default=0, primary_key=True, serialize=False),
        ),
        migrations.AddField(
            model_name='uzytkownik',
            name='id',
            field=models.AutoField(default=0, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='klient',
            name='adres',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='klient',
            name='imie',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='klient',
            name='nazwisko',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='klient',
            name='nrTelefonu',
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name='produkt',
            name='nazwa',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='produkt',
            name='producent',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='uzytkownik',
            name='email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='uzytkownik',
            name='haslo',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='uzytkownik',
            name='login',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
