import numpy as np
from sklearn.linear_model import LinearRegression
from django.core.cache import cache
from datetime import timedelta
from django.utils.timezone import now
from .models import Klient, PozycjaZamowienia, Produkt
from django.db.models import Sum, F
from django.db.models.functions import TruncWeek


class SystemPredykcji:
    CACHE_KEY = 'system_predykcji_data'
    CACHE_TIMEOUT = 360

    def __init__(self):
        self.data = cache.get(self.CACHE_KEY)
        if not self.data:
            self.update_data()

    def update_data(self):

        now_date = now()
        one_year_ago = now_date - timedelta(days=365)

        # Klienci, którzy dokonali zakupu w ostatnim roku
        active_clients = (
            Klient.objects.filter(
                uzytkownik__zamowienie__data_utworzenia__gte=one_year_ago
            )
            .distinct()
            .count()
        )

        churn_rates = []
        for month in range(1, 13):
            month_end = one_year_ago + timedelta(days=30 * month)
            remaining_clients = Klient.objects.filter(
                uzytkownik__zamowienie__data_utworzenia__range=(one_year_ago, month_end)
            ).distinct().count()
            churn_rate = 1 - (remaining_clients / active_clients)
            churn_rates.append(round(churn_rate * 100, 2))

        self.data = {'churn_rates': churn_rates, 'last_updated': now_date}
        cache.set(self.CACHE_KEY, self.data, self.CACHE_TIMEOUT)

    def przekazDane(self):

        return self.data

    def prognozuj_sprzedaz_produktu(self, produkt_id):

        try:
            produkt = Produkt.objects.get(id=produkt_id)
        except Produkt.DoesNotExist:
            return None

        end_date = now()
        start_date = end_date - timedelta(days=365)

        sprzedaz_tygodniowa = (
            PozycjaZamowienia.objects.filter(
                produkt=produkt,
                zamowienie__data_utworzenia__range=(start_date, end_date)
            )
            .annotate(tydzien=TruncWeek('zamowienie__data_utworzenia'))
            .values('tydzien')
            .annotate(sprzedane_sztuki=Sum('ilosc'))
            .order_by('tydzien')
        )

        # Dane do modelu regresji liniowej
        tygodnie = []
        sprzedaz = []
        for idx, item in enumerate(sprzedaz_tygodniowa):
            tygodnie.append(idx + 1)  # Zamieniamy tygodnie na indeksy
            sprzedaz.append(item['sprzedane_sztuki'])

        if len(tygodnie) < 2:
            # Za mało danych do prognozowania
            return {
                'labels': [],
                'forecast': [],
                'history': sprzedaz,
            }

        # Dopasowanie modelu regresji liniowej
        X = np.array(tygodnie).reshape(-1, 1)
        y = np.array(sprzedaz)
        model = LinearRegression()
        model.fit(X, y)


        przyszle_tygodnie = np.array(range(len(tygodnie) + 1, len(tygodnie) + 13)).reshape(-1, 1)
        prognoza = model.predict(przyszle_tygodnie)

        labels = [f"Tydzień {i}" for i in range(1, len(tygodnie) + 13)]
        history = sprzedaz
        forecast = [max(0, round(val, 2)) for val in prognoza]  # Prognoza z zaokrągleniem i ograniczeniem do 0

        return {
            'labels': labels,
            'history': history,
            'forecast': forecast,
        }
