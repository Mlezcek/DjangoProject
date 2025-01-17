from datetime import datetime, timedelta
from django.db import models, transaction
from django.utils.timezone import now
from django.core.cache import cache
from .models import Klient, Produkt, OfertaSpersonalizowana, Grupa, Kampania, KampaniaProdukt, PozycjaZamowienia, \
    Zamowienie
from django.db.models import Sum, Count, Q


class SystemKampanii:


    CACHE_KEY = 'kampanie_cache'
    CACHE_TIMEOUT = 360

    def __init__(self):
        self.czas_sprawdzania = timedelta(hours=1)
        self.kampanie = cache.get(self.CACHE_KEY)
        if not self.kampanie:
            self.odswiez_cache()
        self.sprawdz_warunki()

    def odswiez_cache(self):

        self.kampanie = Kampania.objects.filter(aktywowana=False)
        cache.set(self.CACHE_KEY, self.kampanie, self.CACHE_TIMEOUT)

    def utworz_kampanie(self, data_rozpoczecia, warunek, grupy, produkty, ceny, czas_trwania):
        kampania = Kampania(
            data_rozpoczecia=data_rozpoczecia,
            warunek=warunek,
            czas_trwania=czas_trwania,
        )
        kampania.save()

        kampania.grupy.set(grupy)

        for produkt, cena in zip(produkty, ceny):
            KampaniaProdukt.objects.create(
                kampania=kampania,
                produkt=produkt,
                cena=cena
            )

        self.odswiez_cache()

    def sprawdz_warunki(self):

        teraz = now()

        print('SPRAWDZAM')

        for kampania in self.kampanie:
            if kampania.data_rozpoczecia and kampania.data_rozpoczecia <= teraz:
                kampania.aktywuj()

            elif kampania.warunek:
                if self.ocen_warunek(kampania.warunek):
                    kampania.aktywuj()

        self.odswiez_cache()

    @staticmethod
    def ocen_warunek(warunek):

        typ = warunek.get("typ")
        wartosc = warunek.get("wartosc")

        if typ == "sprzedaz_przedmiotu":
            produkt_id = warunek.get("produkt_id")
            suma_sprzedazy = PozycjaZamowienia.objects.filter(
                produkt_id=produkt_id
            ).aggregate(Sum("ilosc"))["ilosc__sum"] or 0
            return suma_sprzedazy >= wartosc

        elif typ == "liczba_osob_w_grupie":
            grupa_id = warunek.get("grupa_id")
            liczba_osob = Klient.objects.filter(grupy__id=grupa_id).count()
            return liczba_osob >= wartosc

        elif typ == "liczba_klientow":
            liczba_klientow = Klient.objects.count()
            return liczba_klientow >= wartosc

        elif typ == "liczba_zakupow":
            liczba_zakupow = Zamowienie.objects.count()
            return liczba_zakupow >= wartosc

        return False

    def pobierz_statystyki_kampanii(self,kampania):

        statystyki = []
        produkty = KampaniaProdukt.objects.filter(kampania=kampania)
        teraz = now()

        for produkt in produkty:
            liczba_sprzedanych = PozycjaZamowienia.objects.filter(
                produkt=produkt.produkt,
                zamowienie__data_utworzenia__gte=kampania.data_rozpoczecia,
                zamowienie__data_utworzenia__lte=kampania.data_rozpoczecia + timedelta(days=kampania.czas_trwania)
            ).aggregate(Sum('ilosc'))['ilosc__sum'] or 0

            przychod = liczba_sprzedanych * produkt.cena

            # Sprzedaż dzienna
            sprzedaz_dzienna = []
            dni = []
            start_date = kampania.data_rozpoczecia.date()
            end_date = (kampania.data_rozpoczecia + timedelta(days=kampania.czas_trwania)).date()
            delta = (end_date - start_date).days

            for i in range(delta + 1):
                dzien = start_date + timedelta(days=i)
                dni.append(dzien)
                sprzedaz = PozycjaZamowienia.objects.filter(
                    produkt=produkt.produkt,
                    zamowienie__data_utworzenia__date=dzien
                ).aggregate(Sum('ilosc'))['ilosc__sum'] or 0
                sprzedaz_dzienna.append(sprzedaz)

            statystyki.append({
                'produkt': produkt.produkt.nazwa,
                'liczba_sprzedanych': liczba_sprzedanych,
                'przychod': przychod,
                'dni': dni,
                'sprzedaz_dzienna': sprzedaz_dzienna
            })

        return statystyki