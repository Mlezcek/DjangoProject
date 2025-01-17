import os
from datetime import datetime, timedelta
import random

from django.core.mail import send_mail
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now

FILE_PATH = os.path.join(os.path.dirname(__file__), 'users.txt')
ITEMS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'items.txt')

class Uzytkownik(models.Model):
    login = models.CharField(max_length=100, unique=True)
    haslo = models.CharField(max_length=100)
    email = models.EmailField()
    rola = models.IntegerField(default=0)
    id = models.AutoField(primary_key=True)

    def __str__(self):
        return self.login


class Klient(models.Model):
    id = models.AutoField(primary_key=True)
    uzytkownik = models.OneToOneField(Uzytkownik, on_delete=models.CASCADE)
    adres = models.CharField(max_length=255)
    nrTelefonu = models.CharField(max_length=20)
    dataRejestracji = models.DateTimeField(auto_now_add=True)
    imie = models.CharField(max_length=100)
    nazwisko = models.CharField(max_length=100)
    punkty_lojalnosciowe = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.imie} {self.nazwisko}"


class Produkt(models.Model):
    id = models.AutoField(primary_key=True)
    nazwa = models.CharField(max_length=255)
    cena = models.DecimalField(max_digits=10, decimal_places=2)
    opis = models.TextField()
    producent = models.CharField(max_length=255)
    sciezka_do_zdjecia = models.CharField(max_length=255)

    def __str__(self):
        return self.nazwa


class Koszyk(models.Model):
    id = models.AutoField(primary_key=True)
    uzytkownik = models.ForeignKey(Uzytkownik, on_delete=models.CASCADE)

    def __str__(self):
        return f"Koszyk uzytkownika {self.uzytkownik.login}"


class PozycjaKoszyka(models.Model):
    id = models.AutoField(primary_key=True)
    koszyk = models.ForeignKey(Koszyk, on_delete=models.CASCADE)
    produkt = models.ForeignKey(Produkt, on_delete=models.CASCADE)
    ilosc = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.produkt.nazwa} ({self.ilosc})"


class Zamowienie(models.Model):
    id = models.AutoField(primary_key=True)
    uzytkownik = models.ForeignKey(Uzytkownik, on_delete=models.CASCADE)
    data_utworzenia = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default='OCZEKUJĄCE')

    def __str__(self):
        return f"Zamówienie #{self.id} ({self.status})"


class PozycjaZamowienia(models.Model):
    id = models.AutoField(primary_key=True)
    zamowienie = models.ForeignKey(Zamowienie, on_delete=models.CASCADE)
    produkt = models.ForeignKey(Produkt, on_delete=models.CASCADE)
    ilosc = models.PositiveIntegerField(default=1)
    cena = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.produkt.nazwa} x {self.ilosc}"

class Oferta(models.Model):
    id = models.AutoField(primary_key=True)
    idPrzedmiotu = models.ForeignKey(Produkt, on_delete=models.CASCADE)
    data_rozpoczecia = models.DateTimeField()
    data_zakonczenia = models.DateTimeField()
    cena = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'Oferta {self.id} - {self.idPrzedmiotu.nazwa}'


class OfertaSpersonalizowana(models.Model):
    id = models.AutoField(primary_key=True)
    idPrzedmiotu = models.ForeignKey(Produkt, on_delete=models.CASCADE)
    data_rozpoczecia = models.DateTimeField()
    data_zakonczenia = models.DateTimeField()
    cena = models.DecimalField(max_digits=10, decimal_places=2)
    idKlienta = models.ForeignKey('Klient', on_delete=models.CASCADE)
    powod = models.CharField(max_length=255)

    def __str__(self):
        return f'Oferta Spersonalizowana {self.id} - {self.idPrzedmiotu.nazwa} dla {self.idKlienta.imie} {self.idKlienta.nazwisko}'



def get_items():
    items = []
    if os.path.exists(ITEMS_FILE_PATH):
        with open(ITEMS_FILE_PATH, 'r') as file:
            for line in file:
                name, category, price, image = line.strip().split(';')
                items.append({
                    'name': name,
                    'category': category,
                    'price': price,
                    'image': image,
                })
    return items

def get_random_items(count=5):
    items = get_items()
    return random.sample(items, min(count, len(items)))

#########################################

class Grupa(models.Model):
    NAZWA_GRUPY_PREDEFINED = [
        ('nowi_klienci', 'Nowi Klienci'),  # Konta młodsze niż 31 dni
        ('starzy_klienci', 'Starzy Klienci'),  # Konta starsze niż 31 dni
        ('nieaktywni', 'Nieaktywni'),  # Brak zakupów w ostatnich 31 dniach
    ]

    nazwa = models.CharField(max_length=50, unique=True)
    opis = models.TextField(blank=True, null=True)
    is_predefined = models.BooleanField(default=False)
    color = models.CharField(
        max_length=7,
        default='#007bff',  # Domyślny kolor (niebieski)
        help_text='Wprowadź kolor w formacie HEX, np. #FF5733',
    )

    def __str__(self):
        return self.get_nazwa_display() if self.is_predefined else self.nazwa

class GrupaCondition(models.Model):
    CONDITION_TYPE_CHOICES = [
        ('purchase_item', 'Klienci kupili przedmiot'),
        ('spend_last_days', 'Klienci wydali kwotę w ostatnich X dniach'),
        ('spend_total', 'Klienci całkowicie wydali kwotę'),
        ('account_age', 'Konto istnieje X dni'),
    ]

    grupa = models.ForeignKey(Grupa, related_name='conditions', on_delete=models.CASCADE)
    condition_type = models.CharField(max_length=20, choices=CONDITION_TYPE_CHOICES)

    produkt = models.ForeignKey(Produkt, null=True, blank=True, on_delete=models.SET_NULL)
    min_ilosc = models.PositiveIntegerField(null=True, blank=True)
    max_ilosc = models.PositiveIntegerField(null=True, blank=True)

    min_wydano = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_wydano = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    days_last = models.PositiveIntegerField(null=True, blank=True)

    min_wydano_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_wydano_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    min_dni = models.PositiveIntegerField(null=True, blank=True)
    max_dni = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.grupa} - {self.get_condition_type_display()}"

class GrupaKlient(models.Model):
    klient = models.ForeignKey(Klient, on_delete=models.CASCADE, related_name='grupy')
    grupa = models.ForeignKey(Grupa, on_delete=models.CASCADE, related_name='klienci')
    data_dodania = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('klient', 'grupa')

    def __str__(self):
        return f"{self.klient} - {self.grupa}"

#########################################################
class HistoriaOfertGrupowych(models.Model):
    id = models.AutoField(primary_key=True)
    przedmiot = models.ForeignKey('Produkt', on_delete=models.CASCADE)
    data_rozpoczecia = models.DateTimeField()
    data_zakonczenia = models.DateTimeField()
    kwota = models.DecimalField(max_digits=10, decimal_places=2)
    grupa = models.ForeignKey('Grupa', on_delete=models.CASCADE)

    def __str__(self):
        return f"Oferta dla {self.grupa.nazwa} - {self.przedmiot.nazwa}"

    def delete(self, *args, **kwargs):
        powiazane_oferty_personalizowane = OfertaSpersonalizowana.objects.filter(
            idPrzedmiotu=self.przedmiot,
            cena=self.kwota
        )

        powiazane_oferty_personalizowane.delete()

        super().delete(*args, **kwargs)
######################################

class Kampania(models.Model):
    data_rozpoczecia = models.DateTimeField(null=True, blank=True)
    warunek = models.JSONField(null=True, blank=True)
    czas_trwania = models.PositiveIntegerField()
    aktywowana = models.BooleanField(default=False)
    grupy = models.ManyToManyField(Grupa)

    def aktywuj(self):
        self.aktywowana = True
        print("AKTYWACJA")
        self.save()
        self.utworz_oferty()

    def utworz_oferty(self):
        koniec_kampanii = now() + timedelta(days=self.czas_trwania)

        for grupa in self.grupy.all():
            klienci = Klient.objects.filter(grupy__grupa=grupa)
            produkty = KampaniaProdukt.objects.filter(kampania=self)

            for klient in klienci:
                for produkt in produkty:
                    OfertaSpersonalizowana.objects.create(
                        idPrzedmiotu=produkt.produkt,
                        idKlienta=klient,
                        data_rozpoczecia=now(),
                        data_zakonczenia=koniec_kampanii,
                        cena=produkt.cena,
                        powod="Kampania promocyjna"
                    )
            for produkt in produkty:
                HistoriaOfertGrupowych.objects.create(
                    przedmiot=produkt.produkt,
                    data_rozpoczecia=now(),
                    data_zakonczenia=koniec_kampanii,
                    kwota=produkt.cena,
                    grupa=grupa
                )


class KampaniaProdukt(models.Model):
    kampania = models.ForeignKey(Kampania, on_delete=models.CASCADE)
    produkt = models.ForeignKey(Produkt, on_delete=models.CASCADE)
    cena = models.DecimalField(max_digits=10, decimal_places=2)


class Notatka(models.Model):
    tytul = models.CharField(max_length=100)
    tresc = models.TextField()
    kolor = models.CharField(max_length=7, default="#ffffff")  # HEX koloru
    data_utworzenia = models.DateTimeField(auto_now_add=True)
    data_aktualizacji = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.tytul



class NazwaKampanii(models.Model):
    kampania = models.OneToOneField(Kampania, on_delete=models.CASCADE, related_name="nazwa")
    nazwa = models.CharField(max_length=255, default="")

    def __str__(self):
        return self.nazwa