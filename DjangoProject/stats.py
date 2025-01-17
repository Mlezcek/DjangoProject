from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Klient, Produkt, Zamowienie, PozycjaZamowienia, Oferta, PozycjaKoszyka
from django.db.models import Sum, Count, F, Avg
import numpy as np
from sklearn.preprocessing import MinMaxScaler

class SystemStatystyk:

    CACHE_KEY = 'system_statystyk_data'
    CACHE_TIMEOUT = 180  #

    def __init__(self):
        self.data = cache.get(self.CACHE_KEY)
        if not self.data:
            self.update_data()
        else:
            last_updated = self.data.get('last_updated')
            if not last_updated or timezone.now() - last_updated > timedelta(seconds=self.CACHE_TIMEOUT):
                self.update_data()


    def update_data(self):

        clients_data = self.generate_clients_data()
        products_data = self.generate_products_data()

        self.data = {
            'last_updated': timezone.now(),
            'clients_data': clients_data,
            'products_data': products_data,
        }

        cache.set(self.CACHE_KEY, self.data, self.CACHE_TIMEOUT)

    def generate_clients_data(self):

        clients_qs = Klient.objects.all().select_related('uzytkownik')
        clients_data = []
        now = timezone.now()
        all_products = list(Produkt.objects.all())

        for client in clients_qs:
            user_orders = Zamowienie.objects.filter(uzytkownik=client.uzytkownik)
            orders_count = user_orders.count()

            total_products_qs = PozycjaZamowienia.objects.filter(zamowienie__in=user_orders)
            total_products_bought = total_products_qs.aggregate(sum_qty=Sum('ilosc'))['sum_qty'] or 0

            average_order_value = user_orders.aggregate(
                avg_order=Avg(F('pozycjazamowienia__cena') * F('pozycjazamowienia__ilosc'))
            )['avg_order'] or Decimal('0.00')

            one_year_ago = now - timedelta(days=365)
            active_orders = user_orders.filter(data_utworzenia__gte=one_year_ago)
            purchase_frequency = active_orders.count() / 1  # Zamówienia na rok

            first_order = user_orders.order_by('data_utworzenia').first()
            if first_order:
                customer_lifespan_days = (now - first_order.data_utworzenia).days
                customer_lifespan_years = customer_lifespan_days / 365
            else:
                customer_lifespan_years = 0

            clv = self.calculate_clv(average_order_value, purchase_frequency, customer_lifespan_years)

            most_ordered_qs = (
                total_products_qs
                .values('produkt', 'produkt__nazwa')
                .annotate(total_qty=Sum('ilosc'))
                .order_by('-total_qty')[:5]
            )

            main_product = None
            if most_ordered_qs:
                main_product_id = most_ordered_qs[0]['produkt']
                main_product = next((p for p in all_products if p.id == main_product_id), None)

            client_bought_products_ids = set(
                total_products_qs.values_list('produkt', flat=True)
            )

            if main_product:
                compatibility_ranking = self.compute_compatibility_scores(main_product, all_products)
                compatibility_ranking = [
                    x for x in compatibility_ranking
                    if x['other_product'].id not in client_bought_products_ids
                ]
            else:
                compatibility_ranking = []

            purchase_diagrams = {
                'period7': self.get_client_purchase_data(user_orders, days=7),
                'period31': self.get_client_purchase_data(user_orders, days=31),
                'period365': self.get_client_purchase_data(user_orders, days=365, monthly=True),
            }

            single_count = 0
            multi_count = 0
            for z in user_orders:
                distinct_prods = z.pozycjazamowienia_set.values('produkt').distinct().count()
                if distinct_prods == 1:
                    single_count += 1
                else:
                    multi_count += 1


            TotalSpendSum = 0

            normal_price_count = 0
            offer_price_count = 0
            all_positions = PozycjaZamowienia.objects.filter(zamowienie__in=user_orders).select_related('produkt')
            for pos in all_positions:
                if pos.cena < pos.produkt.cena:
                    offer_price_count += 1
                    TotalSpendSum += pos.cena
                else:
                    normal_price_count += 1
                    TotalSpendSum += pos.cena

            clients_data.append({
                'client': client,
                'orders_count': orders_count,
                'total_products_bought': total_products_bought,
                'average_order_value': round(float(average_order_value), 2),
                'purchase_frequency': round(purchase_frequency, 2),
                'customer_lifespan_years': round(customer_lifespan_years, 2),
                'clv': round(clv, 2),
                'TotalSpendSum': TotalSpendSum,

                'most_ordered_qs': most_ordered_qs,  # top 5
                'main_product': main_product,
                'compatibility_ranking': compatibility_ranking[:5],  # top 5 dopasowań
                'purchase_diagrams': purchase_diagrams,
                'single_multi': {
                    'single_count': single_count,
                    'multi_count': multi_count,
                },
                'price_type': {
                    'normal_price_count': normal_price_count,
                    'offer_price_count': offer_price_count,
                },
            })

        return clients_data

    def generate_products_data(self):
        products_qs = Produkt.objects.all()
        products_data = []
        now = timezone.now()

        for product in products_qs:
            total_sold_all_time = PozycjaZamowienia.objects.filter(produkt=product).aggregate(
                suma=Sum('ilosc')
            )['suma'] or 0

            better_count = (
                Produkt.objects
                .annotate(sum_ilosc=Sum('pozycjazamowienia__ilosc'))
                .filter(sum_ilosc__gt=total_sold_all_time)
                .count()
            )
            ranking_position = better_count + 1

            orders_count = (
                Zamowienie.objects
                .filter(pozycjazamowienia__produkt=product)
                .distinct()
                .count()
            )

            in_carts_count = PozycjaKoszyka.objects.filter(produkt=product).count()

            current_offers = Oferta.objects.filter(
                idPrzedmiotu=product,
                data_rozpoczecia__lte=now,
                data_zakonczenia__gte=now
            )

            sales_7days = self.get_sales_for_period(product, days=7)
            sales_14days = self.get_sales_for_period(product, days=14)
            sales_31days = self.get_sales_for_period(product, days=31)

            orders_with_product = Zamowienie.objects.filter(pozycjazamowienia__produkt=product).distinct()
            solely_count = 0
            in_package_count = 0
            for order in orders_with_product:
                product_count_in_order = order.pozycjazamowienia_set.values('produkt').distinct().count()
                if product_count_in_order == 1:
                    solely_count += 1
                else:
                    in_package_count += 1

            customers_with_any_purchase = Zamowienie.objects.filter(pozycjazamowienia__produkt=product).values_list('uzytkownik', flat=True).distinct()
            total_customers_count = customers_with_any_purchase.count()

            repeat_customers_qs = (
                PozycjaZamowienia.objects
                .filter(produkt=product, zamowienie__uzytkownik__in=customers_with_any_purchase)
                .values('zamowienie__uzytkownik')
                .annotate(total_qty=Sum('ilosc'))
                .filter(total_qty__gte=2)
            )
            repeat_customers_count = repeat_customers_qs.count()

            if total_customers_count > 0:
                repeat_purchase_percent = round((repeat_customers_count / total_customers_count) * 100, 2)
            else:
                repeat_purchase_percent = 0.0

            compatibility_ranking = self.compute_compatibility_scores(product, all_products=products_qs)

            products_data.append({
                'product': product,
                'total_sold_all_time': total_sold_all_time,
                'ranking_position': ranking_position,
                'orders_count': orders_count,
                'in_carts_count': in_carts_count,
                'current_offers': current_offers,

                'sales_7days': sales_7days,
                'sales_14days': sales_14days,
                'sales_31days': sales_31days,

                'solely_count': solely_count,
                'in_package_count': in_package_count,

                'repeat_purchase_percent': repeat_purchase_percent,

                'compatibility_ranking': compatibility_ranking,
            })

        return products_data


    def calculate_clv(self, aov, purchase_frequency, lifespan_years):
        """
         CLV = AOV * Purchase Frequency * Customer Lifespan
        """
        return aov * Decimal(str(purchase_frequency)) * Decimal(str(lifespan_years))

    def compute_compatibility_scores(self, product, all_products):
        users_product = set(
            Zamowienie.objects
            .filter(pozycjazamowienia__produkt=product)
            .values_list('uzytkownik', flat=True)
        )
        orders_product = set(
            Zamowienie.objects
            .filter(pozycjazamowienia__produkt=product)
            .values_list('id', flat=True)
        )

        results = []
        raw_data = []
        temp_map = []

        for p2 in all_products:
            if p2.id == product.id:
                continue

            users_p2 = set(
                Zamowienie.objects
                .filter(pozycjazamowienia__produkt=p2)
                .values_list('uzytkownik', flat=True)
            )
            orders_p2 = set(
                Zamowienie.objects
                .filter(pozycjazamowienia__produkt=p2)
                .values_list('id', flat=True)
            )

            user_factor = len(users_product.intersection(users_p2))
            order_factor = len(orders_product.intersection(orders_p2))

            raw_data.append([user_factor, order_factor])
            temp_map.append(p2)

        if not raw_data:
            return []

        X = np.array(raw_data, dtype=float)
        scaler = MinMaxScaler(feature_range=(0, 100))
        X_scaled = scaler.fit_transform(X)

        final_scores = []
        for row in X_scaled:
            final_score = 0.5 * row[0] + 0.5 * row[1]
            final_scores.append(final_score)

        results = []
        for i, score in enumerate(final_scores):
            results.append({
                'other_product': temp_map[i],
                'score': round(score, 2)
            })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results

    def get_client_purchase_data(self, user_orders, days=7, monthly=False):
        from django.db.models.functions import TruncDay, TruncMonth

        now = timezone.now()
        start_date = now - timedelta(days=days)
        relevant_orders = user_orders.filter(data_utworzenia__gte=start_date)

        if monthly:
            qs = (
                PozycjaZamowienia.objects
                .filter(zamowienie__in=relevant_orders)
                .annotate(period=TruncMonth('zamowienie__data_utworzenia'))
                .values('period')
                .annotate(
                    total_amount=Sum(F('cena') * F('ilosc')),
                    total_qty=Sum('ilosc')
                )
                .order_by('period')
            )
            data_map = {}
            for row in qs:
                lbl = row['period'].strftime('%Y-%m')
                data_map[lbl] = {
                    'amount': float(row['total_amount']),
                    'qty': int(row['total_qty'])
                }

            labels = []
            amounts = []
            quantities = []

            current_date = start_date
            while current_date <= now:
                label = current_date.strftime('%Y-%m')
                if label in data_map:
                    amounts.append(data_map[label]['amount'])
                    quantities.append(data_map[label]['qty'])
                else:
                    amounts.append(0)
                    quantities.append(0)
                labels.append(label)

                # Następny miesiąc
                year = current_date.year
                month = current_date.month
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1
                current_date = current_date.replace(year=year, month=month, day=1)

            return {
                'labels': labels,
                'amounts': amounts,
                'quantities': quantities
            }
        else:
            qs = (
                PozycjaZamowienia.objects
                .filter(zamowienie__in=relevant_orders)
                .annotate(period=TruncDay('zamowienie__data_utworzenia'))
                .values('period')
                .annotate(
                    total_amount=Sum(F('cena') * F('ilosc')),
                    total_qty=Sum('ilosc')
                )
                .order_by('period')
            )
            data_map = {}
            for row in qs:
                lbl = row['period'].strftime('%Y-%m-%d')
                data_map[lbl] = {
                    'amount': float(row['total_amount']),
                    'qty': int(row['total_qty'])
                }

            labels = []
            amounts = []
            quantities = []
            for i in range(days):
                day_date = (start_date + timedelta(days=i)).date()
                lbl = day_date.strftime('%Y-%m-%d')
                if lbl in data_map:
                    amounts.append(data_map[lbl]['amount'])
                    quantities.append(data_map[lbl]['qty'])
                else:
                    amounts.append(0)
                    quantities.append(0)
                labels.append(lbl)

            return {
                'labels': labels,
                'amounts': amounts,
                'quantities': quantities
            }

    def get_sales_for_period(self, product, days=7):

        now = timezone.now()
        start_date = now - timedelta(days=days)

        from django.db.models.functions import TruncDay
        qs = (
            PozycjaZamowienia.objects
            .filter(produkt=product, zamowienie__data_utworzenia__gte=start_date)
            .annotate(day=TruncDay('zamowienie__data_utworzenia'))
            .values('day')
            .annotate(sum_for_day=Sum(F('cena') * F('ilosc')))
            .order_by('day')
        )

        daily_data = {row['day'].strftime('%Y-%m-%d'): float(row['sum_for_day']) for row in qs if row['day']}

        labels = []
        data = []

        for i in range(days):
            day_date = (start_date + timedelta(days=i)).date()
            lbl = day_date.strftime('%Y-%m-%d')
            labels.append(lbl)
            data.append(daily_data.get(lbl, 0))

        return {
            'labels': labels,
            'data': data
        }

    def przekazDaneCLV(self):
        return self.data.get('clients_data', [])

    def przekazDaneProdukty(self):
        return self.data.get('products_data', [])


