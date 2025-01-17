from datetime import timedelta
from django.utils.timezone import now
from django.db import transaction
from django.core.cache import cache
from django.db.models import Sum, Count, Avg, F, Q
from decimal import Decimal
from .models import Klient, Grupa, GrupaKlient, Zamowienie, PozycjaZamowienia, Produkt

class SystemGrup:

    CACHE_KEY = 'system_grup_data'
    CACHE_TIMEOUT = 20

    def __init__(self):
        # Pobranie wszystkich grup
        self.grupy = Grupa.objects.all()

        # Próba pobrania danych z cache
        self.data = cache.get(self.CACHE_KEY)
        if not self.data:
            self.update_data()
        else:
            # Sprawdzenie, czy dane nie są przestarzałe
            last_updated = self.data.get('last_updated')
            if not last_updated or now() - last_updated > timedelta(seconds=self.CACHE_TIMEOUT):
                self.update_data()

    def aktualizuj_grupy(self):
        with transaction.atomic():
            for grupa in self.grupy:
                conditions = grupa.conditions.all()

                if not conditions.exists():
                    continue

                klienci_qs = Klient.objects.all()

                q_conditions = Q()

                for condition in conditions:
                    if condition.condition_type == 'purchase_item':
                        if not condition.produkt or condition.min_ilosc is None:
                            continue
                        q_purchase = Q(
                            uzytkownik__zamowienie__pozycjazamowienia__produkt=condition.produkt,
                            uzytkownik__zamowienie__pozycjazamowienia__ilosc__gte=condition.min_ilosc
                        )
                        if condition.max_ilosc is not None:
                            q_purchase &= Q(uzytkownik__zamowienie__pozycjazamowienia__ilosc__lte=condition.max_ilosc)
                        q_conditions &= q_purchase

                    elif condition.condition_type == 'spend_last_days':
                        if condition.days_last is None or condition.min_wydano is None:
                            continue
                        q_spend_last = Q(
                            uzytkownik__zamowienie__data_utworzenia__gte=now() - timedelta(days=condition.days_last)
                        )
                        q_spend_last &= Q(
                            uzytkownik__zamowienie__pozycjazamowienia__cena__isnull=False
                        )
                        klienci_qs = klienci_qs.annotate(
                            total_spend_last=Sum(
                                F('uzytkownik__zamowienie__pozycjazamowienia__cena') *
                                F('uzytkownik__zamowienie__pozycjazamowienia__ilosc'),
                                filter=Q(uzytkownik__zamowienie__data_utworzenia__gte=now() - timedelta(days=condition.days_last))
                            )
                        ).filter(
                            total_spend_last__gte=condition.min_wydano
                        )
                        if condition.max_wydano is not None:
                            klienci_qs = klienci_qs.filter(
                                total_spend_last__lte=condition.max_wydano
                            )
                        continue

                    elif condition.condition_type == 'spend_total':
                        if condition.min_wydano_total is None:
                            continue
                        klienci_qs = klienci_qs.annotate(
                            total_spent=Sum(
                                F('uzytkownik__zamowienie__pozycjazamowienia__cena') *
                                F('uzytkownik__zamowienie__pozycjazamowienia__ilosc')
                            )
                        ).filter(
                            total_spent__gte=condition.min_wydano_total
                        )
                        if condition.max_wydano_total is not None:
                            klienci_qs = klienci_qs.filter(
                                total_spent__lte=condition.max_wydano_total
                            )
                        continue

                    elif condition.condition_type == 'account_age':
                        if condition.min_dni is None:
                            continue
                        q_account_age = Q(
                            dataRejestracji__lte=now() - timedelta(days=condition.min_dni)
                        )
                        if condition.max_dni is not None:
                            q_account_age &= Q(
                                dataRejestracji__gte=now() - timedelta(days=condition.max_dni)
                            )
                        q_conditions &= q_account_age

                if q_conditions:
                    klienci_qs = klienci_qs.filter(q_conditions).distinct()

                GrupaKlient.objects.filter(grupa=grupa).exclude(klient__in=klienci_qs).delete()

                existing_klienci = GrupaKlient.objects.filter(grupa=grupa).values_list('klient_id', flat=True)

                new_klienci = klienci_qs.exclude(id__in=existing_klienci)

                grupa_klient_entries = [GrupaKlient(grupa=grupa, klient=klient) for klient in new_klienci]
                GrupaKlient.objects.bulk_create(grupa_klient_entries)

    def update_data(self):
        self.aktualizuj_grupy()
        clients_data = self.generate_clients_data()
        group_stats = self.generate_group_statistics()

        self.data = {
            'last_updated': now(),
            'clients_data': clients_data,
            'group_stats': group_stats,
        }

        cache.set(self.CACHE_KEY, self.data, self.CACHE_TIMEOUT)

    def generate_clients_data(self):
        """
        Generuje listę klientów z przypisanymi grupami oraz kolorami grup.
        """
        clients_qs = Klient.objects.all().select_related('uzytkownik').prefetch_related('grupy__grupa')
        clients_data = []

        for klient in clients_qs:
            grupy = klient.grupy.select_related('grupa').all()
            grupy_info = [{'nazwa': grupa.grupa.nazwa, 'color': grupa.grupa.color} for grupa in grupy]
            clients_data.append({
                'klient': klient,
                'grupy': grupy_info,
            })

        return clients_data

    def generate_group_statistics(self):
        """
        Generuje statystyki dla każdej grupy.
        """
        grupy = Grupa.objects.all()
        group_stats = {}

        for grupa in grupy:
            # Pobranie klientów w grupie
            klienci_grupy = Klient.objects.filter(grupy__grupa=grupa)

            # Liczba członków
            liczba_czlonkow = klienci_grupy.count()

            # Liczba zakupów
            liczba_zakupow = Zamowienie.objects.filter(uzytkownik__klient__in=klienci_grupy).count()

            # Średnia kwota zakupów
            srednia_kwota = Zamowienie.objects.filter(uzytkownik__klient__in=klienci_grupy).aggregate(
                srednia=Avg(F('pozycjazamowienia__cena') * F('pozycjazamowienia__ilosc'))
            )['srednia'] or Decimal('0.00')
            srednia_kwota = round(float(srednia_kwota), 2)

            # Ulubione produkty (top 5)
            ulubione_produkty_qs = (
                PozycjaZamowienia.objects
                .filter(zamowienie__uzytkownik__klient__in=klienci_grupy)
                .values('produkt__nazwa')
                .annotate(liczba_zakupow=Sum('ilosc'))
                .order_by('-liczba_zakupow')[:5]
            )
            ulubione_produkty = list(ulubione_produkty_qs)

            # Ile procentowo osób należy do grupy
            total_clients = Klient.objects.count()
            procent_grupy = round((liczba_czlonkow / total_clients) * 100, 2) if total_clients > 0 else 0.0

            # Wykres liczby członków w czasie (365 dni)
            wykres_liczby_czlonkow = self.get_members_over_time(grupa, days=365)

            # Wykres kołowy zakupów względem innych grup
            wykres_zakupow_rel_other_groups = self.get_purchases_pie_chart(grupa)

            # Wykres liczby zakupów w ostatnich (7/14/31) dniach
            wykres_zakupow_ostatnie_dni = self.get_purchases_last_days(grupa)

            group_stats[grupa.nazwa] = {
                'nazwa': grupa.nazwa,
                'color': grupa.color,  # Dodanie koloru grupy
                'liczba_czlonkow': liczba_czlonkow,
                'liczba_zakupow': liczba_zakupow,
                'srednia_kwota': srednia_kwota,
                'ulubione_produkty': ulubione_produkty,
                'procent_grupy': procent_grupy,
                'wykres_liczby_czlonkow': wykres_liczby_czlonkow,
                'wykres_zakupow_rel_other_groups': wykres_zakupow_rel_other_groups,
                'wykres_zakupow_ostatnie_dni': wykres_zakupow_ostatnie_dni,
            }

        return group_stats

    def get_members_over_time(self, grupa, days=365):
        now_time = now()

        # Przygotowanie zakresu dat od najstarszej do najnowszej
        date_range = [now_time - timedelta(days=i) for i in reversed(range(days))]
        labels = [date.strftime('%Y-%m-%d') for date in date_range]

        # Pobranie klientów w grupie z uwzględnieniem daty dodania
        klienci = GrupaKlient.objects.filter(grupa=grupa).order_by('data_dodania')

        # Dynamiczne obliczanie liczby członków dla każdego dnia
        current_index = 0
        count = 0
        cumulative_counts = []

        for day in date_range:
            # Zliczaj klientów, których `data_dodania` jest mniejsza lub równa bieżącej dacie
            while current_index < len(klienci) and klienci[current_index].data_dodania.date() <= day.date():
                count += 1
                current_index += 1
            cumulative_counts.append(count)

        return {
            'labels': labels,
            'data': cumulative_counts
        }

    def get_purchases_pie_chart(self, grupa):
        """
        Generuje dane do wykresu kołowego pokazującego zakupy grupy względem innych grup.
        """
        zakupy_grupy = Zamowienie.objects.filter(uzytkownik__klient__grupy__grupa=grupa).count()
        zakupy_innych = Zamowienie.objects.exclude(uzytkownik__klient__grupy__grupa=grupa).count()

        return {
            'labels': ['Zakupy Grupy', 'Zakupy Innych Grup'],
            'data': [zakupy_grupy, zakupy_innych]
        }

    def get_purchases_last_days(self, grupa, days_options=[7, 14, 31]):
        """
        Generuje dane do wykresów pokazujących liczbę zakupów klientów grupy w ostatnich X dniach.
        """
        wykresy = {}
        for days in days_options:
            count = Zamowienie.objects.filter(
                uzytkownik__klient__grupy__grupa=grupa,
                data_utworzenia__gte=now() - timedelta(days=days)
            ).count()
            wykresy[f'dni_{days}'] = count
        return wykresy

    def calculate_clv(self, aov, purchase_frequency, lifespan_years):
        """
        Oblicza CLV na podstawie:
        CLV = AOV * Purchase Frequency * Customer Lifespan
        """
        return aov * Decimal(str(purchase_frequency)) * Decimal(str(lifespan_years))

    def przekazDaneGrupy(self):
        """
        Metoda do przekazywania danych statystycznych grup.
        """
        return self.data.get('group_stats', {})

    def przekazDaneKlientow(self, grupa_nazwa):
        """
        Metoda do przekazywania listy klientów należących do danej grupy.
        """
        return [
            client for client in self.data.get('clients_data', [])
            if any(g['nazwa'] == grupa_nazwa for g in client['grupy'])
        ]
