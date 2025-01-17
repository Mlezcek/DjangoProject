
from decimal import Decimal
from random import sample

from django.contrib.auth.decorators import user_passes_test
from django.db.models.functions import TruncDay
from django.shortcuts import render, redirect
from django.contrib import messages
import json  # Dodaj tę linię

from django.utils import timezone
from django.utils.timezone import now
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .forms import OfertaSpersonalizowanaForm, GrupaForm, GrupaWithConditionForm, KreatorOfertaForm, \
    CampaignCreationForm
from .models import *
from django.db.models import Sum, Avg, Count, Q, F
from .models import get_random_items
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password
from django.db import connection, transaction
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.urls import reverse

import numpy as np
from sklearn.preprocessing import MinMaxScaler

from .stats import SystemStatystyk
from .system_grup import SystemGrup
from .system_kampani import SystemKampanii
from .system_predykcji import SystemPredykcji





def register(request):
    if request.method == 'POST':
        login = request.POST['username']
        haslo = request.POST['password']
        potwierdzenie_hasla = request.POST['confirm_password']
        email = request.POST['email']
        imie = request.POST['first_name']
        nazwisko = request.POST['last_name']
        #adres = request.POST['adres']
        nrTelefonu = request.POST['phone']

        if haslo != potwierdzenie_hasla:
            messages.error(request, "Hasła nie są takie same!")
            return redirect('register')

        # Tworzymy nowego użytkownika
        uzytkownik = Uzytkownik.objects.create(
            login=login,
            haslo=make_password(haslo),
            email=email
        )

        # Tworzymy klienta
        Klient.objects.create(
            uzytkownik=uzytkownik,
            imie=imie,
            nazwisko=nazwisko,
            adres='NULL',
            nrTelefonu=nrTelefonu
        )

        messages.success(request, "Rejestracja zakończona sukcesem!")
        return redirect('login')

    return render(request, 'register.html')


def login(request):
    if request.method == 'POST':
        login = request.POST['username']
        haslo = request.POST['password']
        try:
            uzytkownik = Uzytkownik.objects.get(login=login)
            if check_password(haslo, uzytkownik.haslo):
                request.session['username'] = uzytkownik.login
                return redirect('home')
            else:
                messages.error(request, "Nieprawidłowe hasło!")
        except Uzytkownik.DoesNotExist:
            messages.error(request, "Nieprawidłowy login!")

    return render(request, 'login.html')


def logout(request):
    # Usunięcie danych sesji
    if 'username' in request.session:
        del request.session['username']
    messages.success(request, "Wylogowano pomyślnie!")
    return redirect('login')

def home(request):
    username = request.session.get('username', None)

    # Pobieramy produkty, które mają aktywną ofertę (lub ofertę spersonalizowaną)
    produkty_z_ofertami = Produkt.objects.filter(
        id__in=Oferta.objects.filter(
            data_rozpoczecia__lte=datetime.now(),
            data_zakonczenia__gte=datetime.now()
        ).values('idPrzedmiotu')
    ) | Produkt.objects.filter(
        id__in=OfertaSpersonalizowana.objects.filter(
            data_rozpoczecia__lte=datetime.now(),
            data_zakonczenia__gte=datetime.now()
        ).values('idPrzedmiotu')
    )

    # Jeśli mamy więcej niż 5 produktów z ofertą, losujemy 5
    if produkty_z_ofertami.count() > 5:
        produkty_z_ofertami = sample(list(produkty_z_ofertami), 5)

    # Pobieramy wszystkie aktywne oferty i oferty spersonalizowane
    aktywne_oferty = Oferta.objects.filter(
        data_rozpoczecia__lte=datetime.now(),
        data_zakonczenia__gte=datetime.now()
    )

    uzytkownik = Uzytkownik.objects.get(login=username)
    klient = Klient.objects.get(uzytkownik=uzytkownik)

    aktywne_oferty_spersonalizowane = OfertaSpersonalizowana.objects.filter(
        data_rozpoczecia__lte=datetime.now(),
        data_zakonczenia__gte=datetime.now(),
        idKlienta = klient.id
    )

    # Lista, do której dopiszemy produkty z przypisanymi polami oferta/cena_promocyjna
    produkty_do_wyswietlenia = []

    for produkt in produkty_z_ofertami:
        # Sprawdź, czy istnieje oferta spersonalizowana
        oferta_spersonalizowana = aktywne_oferty_spersonalizowane.filter(
            idPrzedmiotu=produkt.id
        ).first()

        # Albo „zwykła” oferta
        oferta = aktywne_oferty.filter(
            idPrzedmiotu=produkt.id
        ).first()

        # Dodaj atrybuty do obiektu produkt:
        if oferta_spersonalizowana:
            produkt.cena_promocyjna = oferta_spersonalizowana.cena
            produkt.oferta = oferta_spersonalizowana
        elif oferta:
            produkt.cena_promocyjna = oferta.cena
            produkt.oferta = oferta
        else:
            produkt.cena_promocyjna = None
            produkt.oferta = None

        produkty_do_wyswietlenia.append(produkt)

    context = {
        'username': username,
        'produkty': produkty_do_wyswietlenia,
    }

    return render(request, 'home.html', context)


def account(request):
    # Sprawdzamy, czy użytkownik jest zalogowany
    username = request.session.get('username', None)
    if not username:
        return redirect('login')


    try:
        user = Uzytkownik.objects.get(login=username)
    except Uzytkownik.DoesNotExist:
        messages.error(request, "Użytkownik nie istnieje.")
        return redirect('login')

    if request.method == 'POST':
        old_password = request.POST['old_password']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']


        if not check_password(old_password, user.haslo):
            messages.error(request, "Stare hasło jest niepoprawne!")

        elif new_password != confirm_password:
            messages.error(request, "Nowe hasło i potwierdzenie nie są takie same!")

        else:
            user.haslo = make_password(new_password)  # Szyfrujemy nowe hasło
            user.save()

            # Zaktualizowanie sesji, aby użytkownik był zalogowany po zmianie hasła
            update_session_auth_hash(request, user)

            messages.success(request, "Hasło zostało zmienione!")
            return redirect('home')  # Przekierowanie na stronę główną po zmianie hasła

    return render(request, 'account.html', {'username': username})


def search_results(request):
    query = request.GET.get('query', '')
    produkty = []

    # Pobierz aktywne oferty
    aktywne_oferty = Oferta.objects.filter(
        data_rozpoczecia__lte=datetime.now(),
        data_zakonczenia__gte=datetime.now()
    )

    username = request.session.get('username', None)
    uzytkownik = Uzytkownik.objects.get(login=username)
    klient = Klient.objects.get(uzytkownik=uzytkownik)

    aktywne_oferty_spersonalizowane = OfertaSpersonalizowana.objects.filter(
        data_rozpoczecia__lte=datetime.now(),
        data_zakonczenia__gte=datetime.now(),
        idKlienta=klient.id
    )

    with connection.cursor() as cursor:
        if query:
            cursor.execute("SELECT * FROM DjangoProject_produkt WHERE nazwa LIKE %s", ['%' + query + '%'])
        else:
            cursor.execute("SELECT * FROM DjangoProject_produkt")

        rows = cursor.fetchall()

        for row in rows:
            produkt = Produkt(
                id=row[5],
                nazwa=row[0],
                cena=row[1],  # Cena oryginalna
                opis=row[2],
                producent=row[3],
                sciezka_do_zdjecia=row[4]
            )

            # Sprawdzamy oferty i oferty spersonalizowane
            oferta = aktywne_oferty.filter(idPrzedmiotu=produkt.id).first()
            oferta_spersonalizowana = aktywne_oferty_spersonalizowane.filter(idPrzedmiotu=produkt.id).first()

            if oferta_spersonalizowana:
                produkt.cena_promocyjna = oferta_spersonalizowana.cena  # Cena promocyjna
                produkt.oferta = oferta_spersonalizowana
            elif oferta:
                produkt.cena_promocyjna = oferta.cena  # Cena promocyjna
                produkt.oferta = oferta
            else:
                produkt.cena_promocyjna = None  # Brak oferty

            produkty.append(produkt)

    return render(request, 'search_results.html', {'produkty': produkty})


def add_to_cart(request, product_id):
    if request.method == 'POST':
        username = request.session.get('username')
        if not username:
            return JsonResponse({'status': 'error', 'message': 'Musisz być zalogowany, aby dodać produkt do koszyka.'})

        produkt = get_object_or_404(Produkt, id=product_id)
        uzytkownik = get_object_or_404(Uzytkownik, login=username)

        # Pobierz lub utwórz koszyk dla użytkownika
        koszyk, created = Koszyk.objects.get_or_create(uzytkownik=uzytkownik)

        # Sprawdz, czy produkt juz jest w koszyku
        pozycja_koszyka, created = PozycjaKoszyka.objects.get_or_create(koszyk=koszyk, produkt=produkt)

        if not created:
            pozycja_koszyka.ilosc += 1
            pozycja_koszyka.save()

        return JsonResponse({'status': 'success', 'message': f'Dodano "{produkt.nazwa}" do koszyka!'})

    return JsonResponse({'status': 'error', 'message': 'Nieprawidłowe żądanie'})


def view_cart(request):
    username = request.session.get('username')
    if not username:
        messages.error(request, 'Musisz być zalogowany, aby zobaczyć koszyk.')
        return redirect('login')

    uzytkownik = get_object_or_404(Uzytkownik, login=username)
    try:
        koszyk = Koszyk.objects.get(uzytkownik=uzytkownik)
        pozycje_koszyka = PozycjaKoszyka.objects.filter(koszyk=koszyk)
    except Koszyk.DoesNotExist:
        pozycje_koszyka = []

    aktywne_oferty = Oferta.objects.filter(
        data_rozpoczecia__lte=datetime.now(),
        data_zakonczenia__gte=datetime.now()
    )

    aktywne_oferty_spersonalizowane = OfertaSpersonalizowana.objects.filter(
        idKlienta=uzytkownik.klient,
        data_rozpoczecia__lte=datetime.now(),
        data_zakonczenia__gte=datetime.now()
    )

    total_sum = 0  # Initialize the total sum

    for pozycja in pozycje_koszyka:
        oferta_spersonalizowana = aktywne_oferty_spersonalizowane.filter(idPrzedmiotu=pozycja.produkt).first()
        oferta = aktywne_oferty.filter(idPrzedmiotu=pozycja.produkt).first()

        if oferta_spersonalizowana:
            pozycja.cena_oferty = oferta_spersonalizowana.cena
        elif oferta:
            pozycja.cena_oferty = oferta.cena
        else:
            pozycja.cena_oferty = None

        # Add the item price to the total sum
        total_sum += pozycja.cena_oferty * pozycja.ilosc if pozycja.cena_oferty else pozycja.produkt.cena * pozycja.ilosc

    return render(request, 'cart.html', {
        'pozycje_koszyka': pozycje_koszyka,
        'total_sum': total_sum,  # Pass total sum to the template
    })


def remove_from_cart(request, item_id):
    item = get_object_or_404(PozycjaKoszyka, id=item_id)
    item.delete()
    messages.success(request, "Produkt usunięty z koszyka!")
    return redirect('view_cart')

def update_quantity(request, item_id):
   if request.method == 'POST':
        try:
            item = get_object_or_404(PozycjaKoszyka, id=item_id)
            data = json.loads(request.body)
            new_quantity = data.get('quantity')
            if new_quantity and new_quantity > 0:
                  item.ilosc = new_quantity
                  item.save()
                  return JsonResponse({'status': 'success', 'message': 'Ilość zaktualizowana!'})
            else:
              return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa ilość!'})
        except PozycjaKoszyka.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Nie znaleziono produktu w koszyku!'})
   return JsonResponse({'status': 'error', 'message': 'Nieprawidłowe żądanie'})

def create_order(request):
    if request.method == 'POST':
        username = request.session.get('username')
        if not username:
            return JsonResponse({'status': 'error', 'message': 'Musisz być zalogowany, aby złożyć zamówienie.'})

        uzytkownik = get_object_or_404(Uzytkownik, login=username)
        try:
            koszyk = Koszyk.objects.get(uzytkownik=uzytkownik)
            pozycje_koszyka = PozycjaKoszyka.objects.filter(koszyk=koszyk)

            if not pozycje_koszyka:
                return JsonResponse({'status': 'error', 'message': 'Twój koszyk jest pusty.'})

            zamowienie = Zamowienie.objects.create(uzytkownik=uzytkownik)

            aktywne_oferty = Oferta.objects.filter(
                data_rozpoczecia__lte=datetime.now(),
                data_zakonczenia__gte=datetime.now()
            )

            aktywne_oferty_spersonalizowane = OfertaSpersonalizowana.objects.filter(
                idKlienta=uzytkownik.klient,
                data_rozpoczecia__lte=datetime.now(),
                data_zakonczenia__gte=datetime.now()
            )

            for pozycja in pozycje_koszyka:
                oferta_spersonalizowana = aktywne_oferty_spersonalizowane.filter(idPrzedmiotu=pozycja.produkt).first()
                oferta = aktywne_oferty.filter(idPrzedmiotu=pozycja.produkt).first()

                if oferta_spersonalizowana:
                    cena = oferta_spersonalizowana.cena
                elif oferta:
                    cena = oferta.cena
                else:
                    cena = pozycja.produkt.cena

                PozycjaZamowienia.objects.create(
                    zamowienie=zamowienie,
                    produkt=pozycja.produkt,
                    ilosc=pozycja.ilosc,
                    cena=cena
                )

            pozycje_koszyka.delete()
            return JsonResponse({'status': 'success', 'message': 'Zamówienie zostało utworzone pomyślnie!'})

        except Koszyk.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Nie znaleziono koszyka.'})

    return JsonResponse({'status': 'error', 'message': 'Nieprawidłowe żądanie.'})



def user_orders(request):
    username = request.session.get('username')
    if not username:
        messages.error(request, "Musisz być zalogowany, aby przeglądać swoje zamówienia.")
        return redirect('login')

    uzytkownik = Uzytkownik.objects.get(login=username)
    zamowienia = Zamowienie.objects.filter(uzytkownik=uzytkownik).order_by('-data_utworzenia')

    context = {
        'zamowienia': zamowienia,
    }
    return render(request, 'orders.html', context)

def all_products(request):
    produkty = list(Produkt.objects.all())

    aktywne_oferty = Oferta.objects.filter(
        data_rozpoczecia__lte=datetime.now(),
        data_zakonczenia__gte=datetime.now()
    )
    username = request.session.get('username', None)
    aktywne_oferty_spersonalizowane = []
    if username:
        try:
            uzytkownik = Uzytkownik.objects.get(login=username)
            aktywne_oferty_spersonalizowane = OfertaSpersonalizowana.objects.filter(
                idKlienta=uzytkownik.klient,
                data_rozpoczecia__lte=datetime.now(),
                data_zakonczenia__gte=datetime.now()
            )
        except (Uzytkownik.DoesNotExist, Klient.DoesNotExist):
            pass

    # Nadajmy każdemu produktowi informację o ewentualnej cenie promocyjnej:
    for produkt in produkty:
        produkt.cena_promocyjna = None
        produkt.oferta = None

        # Sprawdzamy czy istnieje oferta spersonalizowana na dany produkt
        oferta_spersonalizowana = aktywne_oferty_spersonalizowane.filter(idPrzedmiotu=produkt).first()
        if oferta_spersonalizowana:
            produkt.cena_promocyjna = oferta_spersonalizowana.cena
            produkt.oferta = oferta_spersonalizowana
            continue

        # Jeśli nie ma spersonalizowanej, sprawdzamy zwykłą
        oferta = aktywne_oferty.filter(idPrzedmiotu=produkt).first()
        if oferta:
            produkt.cena_promocyjna = oferta.cena
            produkt.oferta = oferta

    context = {
        'produkty': produkty,
        'username': username,
    }
    return render(request, 'all_products.html', context)

######################################################################################################################
def dashboard(request):
    now = timezone.now()
    last_7_days = now - timedelta(days=7)
    last_24h = now - timedelta(hours=24)

    sales_last_24h = (
        PozycjaZamowienia.objects
        .filter(zamowienie__data_utworzenia__gte=last_24h)
        .aggregate(total_sales=Sum('cena'))
        .get('total_sales') or 0
    )

    new_customers_last_24h = Klient.objects.filter(dataRejestracji__gte=last_24h).count()

    total_value = PozycjaZamowienia.objects.aggregate(total=Sum('cena')).get('total') or 0
    total_orders = Zamowienie.objects.count()
    average_order_value = round(total_value / total_orders, 2) if total_orders else 0

    customer_retention = 101

    last_7_days_sales = (
        PozycjaZamowienia.objects
        .filter(zamowienie__data_utworzenia__gte=last_7_days)
        .annotate(day=TruncDay('zamowienie__data_utworzenia'))
        .values('day')
        .annotate(total=Sum('cena'))
        .order_by('day')
    )


    labels_7days = []
    data_7days = []

    daily_sales = {
        entry['day'].date(): entry['total'] for entry in last_7_days_sales
    }

    for i in range(7):
        day = (now - timedelta(days=i)).date()
        labels_7days.insert(0, day.strftime("%Y-%m-%d"))  # Wstawiamy na początek listy
        data_7days.insert(0, float(daily_sales.get(day, 0)))

    context = {
        # Kafelki
        'sales_last_24h': sales_last_24h,
        'new_customers_last_24h': new_customers_last_24h,
        'average_order_value': average_order_value,
        'customer_retention': customer_retention,

        # Dane do wykresu 7 dni
        'sales_chart_7days_labels': labels_7days,
        'sales_chart_7days_data': data_7days,
    }

    return render(request, 'test.html', context)



def clients_crm(request):
    stats = SystemStatystyk()
    sort_param = request.GET.get('sort', 'default')

    # Pobranie danych klientów
    clients_data = stats.przekazDaneCLV()

    # Pobierz identyfikatory klientów
    klient_ids = [client_data['client'].id for client_data in clients_data]

    # Pobierz wszystkie GrupaKlient dla tych klientów
    grupy_map = GrupaKlient.objects.filter(klient_id__in=klient_ids).select_related('grupa')

    # Tworzymy słownik mapujący klienta na listę grup
    from collections import defaultdict
    grupy_dict = defaultdict(list)
    for entry in grupy_map:
        grupy_dict[entry.klient_id].append(entry.grupa)

    # Dodajemy listę grup do każdego klienta
    for client_data in clients_data:
        client = client_data['client']
        client_data['grupy'] = grupy_dict.get(client.id, [])

    # Sortowanie danych w zależności od parametru
    if sort_param == 'nazwa':
        clients_data = sorted(clients_data, key=lambda x: (x['client'].nazwisko.lower(), x['client'].imie.lower()))
    elif sort_param == 'zakupy':
        clients_data = sorted(clients_data, key=lambda x: x['orders_count'], reverse=True)

    context = {
        'clients_data': clients_data,
        'sort_param': sort_param,
    }
    return render(request, 'clients_crm.html', context)


def products_stats(request):
    stats = SystemStatystyk()

    # Pobierz parametr sortowania
    sort_param = request.GET.get('sort', 'default')

    # Posortuj dane w zależności od sort_param
    if sort_param == 'najczesciej':
        products_data = sorted(stats.przekazDaneProdukty(), key=lambda x: x['total_sold_all_time'], reverse=True)
    elif sort_param == 'cena':
        products_data = sorted(stats.przekazDaneProdukty(), key=lambda x: x['product'].cena)
    elif sort_param == 'nazwa':
        products_data = sorted(stats.przekazDaneProdukty(), key=lambda x: x['product'].nazwa.lower())
    else:
        products_data = stats.przekazDaneProdukty()

    context = {
        'products_data': products_data,
        'sort_param': sort_param
    }
    return render(request, 'products_stats.html', context)

##############################3

def groups_stats(request):
    sort_param = request.GET.get('sort', 'nazwa')  # Domyślnie sortuj po nazwie
    stats_system = SystemGrup()
    group_stats = stats_system.przekazDaneGrupy()

    # Pobranie wszystkich grup
    grupy = Grupa.objects.all()

    # Przygotowanie danych do szablonu
    groups_data = []
    for grupa in grupy:
        stats = group_stats.get(grupa.nazwa, {})
        klienci = stats_system.przekazDaneKlientow(grupa.nazwa)
        groups_data.append({
            'grupa': grupa,
            'stats': stats,
            'klienci': klienci,
        })

    # Sortowanie danych na podstawie sort_param
    if sort_param == 'nazwa':
        groups_data.sort(key=lambda x: x['grupa'].nazwa.lower())
    elif sort_param == 'liczba_czlonkow':
        groups_data.sort(key=lambda x: x['stats'].get('liczba_czlonkow', 0), reverse=True)
    elif sort_param == 'srednia_kwota':
        groups_data.sort(key=lambda x: x['stats'].get('srednia_kwota', 0), reverse=True)

    context = {
        'groups_data': groups_data,
        'grupa_form': GrupaWithConditionForm(),
        'oferta_form': OfertaSpersonalizowanaForm(),
        'current_sort': sort_param,  # Przekazanie aktualnego sortowania do szablonu
    }
    return render(request, 'group_stats.html', context)

@csrf_exempt
def create_group(request):
    if request.method == 'POST':
        form = GrupaWithConditionForm(request.POST)
        if form.is_valid():
            grupa = form.save()
            # Tworzenie warunku dla grupy
            condition_type = form.cleaned_data['condition_type']
            produkt = form.cleaned_data.get('produkt')
            min_ilosc = form.cleaned_data.get('min_ilosc')
            max_ilosc = form.cleaned_data.get('max_ilosc')
            days_last = form.cleaned_data.get('days_last')
            min_wydano = form.cleaned_data.get('min_wydano')
            max_wydano = form.cleaned_data.get('max_wydano')
            min_wydano_total = form.cleaned_data.get('min_wydano_total')
            max_wydano_total = form.cleaned_data.get('max_wydano_total')
            min_dni = form.cleaned_data.get('min_dni')
            max_dni = form.cleaned_data.get('max_dni')

            GrupaCondition.objects.create(
                grupa=grupa,
                condition_type=condition_type,
                produkt=produkt,
                min_ilosc=min_ilosc,
                max_ilosc=max_ilosc,
                days_last=days_last,
                min_wydano=min_wydano,
                max_wydano=max_wydano,
                min_wydano_total=min_wydano_total,
                max_wydano_total=max_wydano_total,
                min_dni=min_dni,
                max_dni=max_dni,
            )

            # Przygotowanie danych grupy do zwrócenia w JSON
            group_data = {
                'id': grupa.id,
                'nazwa': grupa.nazwa,
                'opis': grupa.opis,
                'color': grupa.color,
                'is_predefined': grupa.is_predefined,
                'condition': {
                    'id': grupa.conditions.first().id,
                    'condition_type': grupa.conditions.first().get_condition_type_display(),
                    'produkt': grupa.conditions.first().produkt.nazwa if grupa.conditions.first().produkt else '',
                    'min_ilosc': grupa.conditions.first().min_ilosc,
                    'max_ilosc': grupa.conditions.first().max_ilosc,
                    'days_last': grupa.conditions.first().days_last,
                    'min_wydano': str(grupa.conditions.first().min_wydano),
                    'max_wydano': str(grupa.conditions.first().max_wydano),
                    'min_wydano_total': str(grupa.conditions.first().min_wydano_total),
                    'max_wydano_total': str(grupa.conditions.first().max_wydano_total),
                    'min_dni': grupa.conditions.first().min_dni,
                    'max_dni': grupa.conditions.first().max_dni,
                },
            }

            return JsonResponse({'success': True, 'group': group_data})
        else:
            # Zwrócenie błędów formularza
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)

####################################

def create_group_offer(request):
    if request.method == 'POST':
        form = OfertaSpersonalizowanaForm(request.POST)
        grupa_id = request.POST.get('grupa_id')
        grupa = get_object_or_404(Grupa, id=grupa_id)

        if form.is_valid():
            produkt = form.cleaned_data['produkt']
            data_rozpoczecia = form.cleaned_data['data_rozpoczecia']
            data_zakonczenia = form.cleaned_data['data_zakonczenia']
            cena = form.cleaned_data['cena']
            powod = form.cleaned_data['powod']

            # Pobranie wszystkich klientów w grupie
            klienci = Klient.objects.filter(grupy__grupa=grupa)

            # Tworzenie ofert dla każdego klienta
            oferta_entries = []
            for klient in klienci:
                oferta = OfertaSpersonalizowana(
                    idPrzedmiotu=produkt,
                    data_rozpoczecia=data_rozpoczecia,
                    data_zakonczenia=data_zakonczenia,
                    cena=cena,
                    idKlienta=klient,
                    powod=powod
                )
                oferta_entries.append(oferta)
            OfertaSpersonalizowana.objects.bulk_create(oferta_entries)

            # Tworzenie wpisu w historii ofert grupowych
            HistoriaOfertGrupowych.objects.create(
                przedmiot=produkt,
                data_rozpoczecia=data_rozpoczecia,
                data_zakonczenia=data_zakonczenia,
                kwota=cena,
                grupa=grupa
            )

            # Przygotowanie danych oferty do zwrócenia w JSON
            offer_data = {
                'id': grupa.id,
                'grupa': grupa.nazwa,
                'produkt': produkt.nazwa,
                'data_rozpoczecia': data_rozpoczecia.strftime('%Y-%m-%d %H:%M'),
                'data_zakonczenia': data_zakonczenia.strftime('%Y-%m-%d %H:%M'),
                'cena': str(cena),
                'powod': powod,
                'liczba_ofert': klienci.count(),
            }

            return JsonResponse({'success': True, 'offer': offer_data})
        else:
            # Zwrócenie błędów formularza
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)

#######################################33
def predykcje(request):
    system_predykcji = SystemPredykcji()
    data = system_predykcji.przekazDane()

    context = {
        'churn_labels': [f'Miesiąc {i + 1}' for i in range(len(data['churn_rates']))],
        'churn_data': data['churn_rates'],
        'produkty': Produkt.objects.all(),
    }
    return render(request, 'predykcje.html', context)

@require_GET
def prognoza_sprzedazy(request, produkt_id):
    system_predykcji = SystemPredykcji()
    dane_prognozy = system_predykcji.prognozuj_sprzedaz_produktu(produkt_id)

    if not dane_prognozy:
        return JsonResponse({'error': 'Produkt nie istnieje lub brak danych do prognozy.'}, status=404)

    return JsonResponse(dane_prognozy)
##########################

def oferty(request):

    # Pobranie wszystkich ofert standardowych
    oferty_standardowe = Oferta.objects.select_related('idPrzedmiotu').all()

    # Pobranie wszystkich ofert spersonalizowanych
    oferty_personalizowane = OfertaSpersonalizowana.objects.select_related('idPrzedmiotu', 'idKlienta__uzytkownik').all()

    # Pobranie wszystkich ofert grupowych
    oferty_grupowe = HistoriaOfertGrupowych.objects.select_related('przedmiot', 'grupa').all()

    # Połączenie wszystkich ofert w jedną listę z typem
    wszystkie_oferty = []

    for oferta in oferty_standardowe:
        wszystkie_oferty.append({
            'typ': 'Oferta Standardowa',
            'id': oferta.id,
            'produkt': oferta.idPrzedmiotu,
            'cena': oferta.cena,
            'data_rozpoczecia': oferta.data_rozpoczecia,
            'data_zakonczenia': oferta.data_zakonczenia,
            'powod': 'Standardowa oferta',
            'additional_info': None,
            'model_instance': oferta,
        })

    for oferta in oferty_personalizowane:
        wszystkie_oferty.append({
            'typ': 'Oferta Spersonalizowana',
            'id': oferta.id,
            'produkt': oferta.idPrzedmiotu,
            'cena': oferta.cena,
            'data_rozpoczecia': oferta.data_rozpoczecia,
            'data_zakonczenia': oferta.data_zakonczenia,
            'powod': oferta.powod,
            'additional_info': oferta.idKlienta,
            'model_instance': oferta,
        })

    for oferta in oferty_grupowe:
        wszystkie_oferty.append({
            'typ': 'Oferta Grupowa',
            'id': oferta.id,
            'produkt': oferta.przedmiot,
            'cena': oferta.kwota,
            'data_rozpoczecia': oferta.data_rozpoczecia,
            'data_zakonczenia': oferta.data_zakonczenia,
            'powod': f'Oferta dla grupy: {oferta.grupa.nazwa}',
            'additional_info': oferta.grupa,
            'model_instance': oferta,
        })

    # Przygotowanie danych dla każdej oferty
    for oferta in wszystkie_oferty:
        # Filtracja zamówień na podstawie typu oferty
        if oferta['typ'] == 'Oferta Spersonalizowana':
            klient = oferta['additional_info']
            uzytkownik = klient.uzytkownik
            zakup_filter = Q(zamowienie__uzytkownik=uzytkownik)
        else:
            # Dla ofert standardowych i grupowych, nie filtrujemy na podstawie klienta
            zakup_filter = Q()

        # Liczba sprzedanych sztuk dokonanych z tą ofertą
        liczba_sztuk = PozycjaZamowienia.objects.filter(
            zakup_filter,
            produkt=oferta['produkt'],
            zamowienie__data_utworzenia__range=(oferta['data_rozpoczecia'], oferta['data_zakonczenia'])
        ).aggregate(total_sztuk=Sum('ilosc'))['total_sztuk'] or 0
        oferta['liczba_zakupow'] = liczba_sztuk

        start_date = (oferta['data_rozpoczecia'] - timedelta(days=7)).date()
        end_date = oferta['data_zakonczenia'].date()
        delta = end_date - start_date
        days = delta.days + 1  # uwzględniamy dzień zakończenia

        # Generowanie listy dni
        dni = [start_date + timedelta(days=i) for i in range(days)]

        # Sprzedaż przedmiotu w każdym dniu (sumowanie 'ilosc')
        sprzedaz_dzienna = []
        for day in dni:
            sprzedaz = PozycjaZamowienia.objects.filter(
                zakup_filter,
                produkt=oferta['produkt'],
                zamowienie__data_utworzenia__date=day
            ).aggregate(total_sztuk=Sum('ilosc'))['total_sztuk'] or 0
            sprzedaz_dzienna.append(sprzedaz)

        oferta['labels'] = [day.strftime('%Y-%m-%d') for day in dni]
        oferta['sprzedaz'] = sprzedaz_dzienna

    # Sortowanie ofert, jeśli przesłano parametr sortowania
    sort_type = request.GET.get('sort', 'all')  # 'all', 'Oferta Standardowa', 'Oferta Spersonalizowana', 'Oferta Grupowa'
    if sort_type != 'all':
        wszystkie_oferty = [o for o in wszystkie_oferty if o['typ'] == sort_type]

    # Przekazanie listy ofert do szablonu
    context = {
        'oferty': wszystkie_oferty,
        'sort_type': sort_type,
    }

    return render(request, 'oferty.html', context)


@require_POST
def przedluz_oferte(request, typ, offer_id):

    print('cosdziala')
    dni = int(request.POST.get('dni', 0))
    if dni <= 0:
        messages.error(request, 'Liczba dni musi być większa od 0.')
        return redirect(reverse('oferty'))
    if typ == 'Oferta Standardowa':
        oferta = get_object_or_404(Oferta, id=offer_id)
        print(oferta)
    elif typ == 'Oferta Spersonalizowana':
        oferta = get_object_or_404(OfertaSpersonalizowana, id=offer_id)
    elif typ == 'Oferta Grupowa':
        oferta = get_object_or_404(HistoriaOfertGrupowych, id=offer_id)
    else:
        return redirect(reverse('oferty'))

    # Przedłużenie daty zakończenia
    oferta.data_zakonczenia += timedelta(days=dni)
    oferta.save()


    return redirect(reverse('oferty'))


@require_POST
def zakoncz_oferte(request, typ, offer_id):

    print('cosdziala')
    if typ == 'Oferta Standardowa':
        oferta = get_object_or_404(Oferta, id=offer_id)
    elif typ == 'Oferta Spersonalizowana':
        print(typ)
        oferta = get_object_or_404(OfertaSpersonalizowana, id=offer_id)
    elif typ == 'Oferta Grupowa':
        oferta = get_object_or_404(HistoriaOfertGrupowych, id=offer_id)
    else:

        return redirect(reverse('oferty'))

    # Ustawienie daty zakończenia na bieżący czas
    oferta.data_zakonczenia = timezone.now()

    # Usuń ofertę z bazy danych
    oferta.delete()

    return redirect(reverse('oferty'))

############
def kreator_ofert(request):
    # Krok 1: Statystyki top 3 najlepiej sprzedających się produktów
    top_best_sellers = PozycjaZamowienia.objects.values('produkt__nazwa') \
                           .annotate(total_sztuk=Sum('ilosc')) \
                           .order_by('-total_sztuk')[:3]

    # Krok 2: Statystyki top 3 najgorzej sprzedających się produktów
    top_worst_sellers = PozycjaZamowienia.objects.values('produkt__nazwa') \
                            .annotate(total_sztuk=Sum('ilosc')) \
                            .order_by('total_sztuk')[:3]

    # Krok 3: Formularz do tworzenia oferty
    if request.method == 'POST':
        form = KreatorOfertaForm(request.POST)
        if form.is_valid():
            # Proces tworzenia oferty
            oferta = form.save(commit=False)
            oferta.save()

            # Dodanie relacji z klientami/grupami
            for klient in form.cleaned_data['klienci']:
                oferta_spersonalizowana = OfertaSpersonalizowana(
                    idPrzedmiotu=oferta.idPrzedmiotu,
                    data_rozpoczecia=oferta.data_rozpoczecia,
                    data_zakonczenia=oferta.data_zakonczenia,
                    cena=oferta.cena,
                    idKlienta=klient,
                    powod=form.cleaned_data['powod']
                )
                oferta_spersonalizowana.save()

            for grupa in form.cleaned_data['grupy']:
                historia_ofert_grupowych = HistoriaOfertGrupowych(
                    przedmiot=oferta.idPrzedmiotu,
                    data_rozpoczecia=oferta.data_rozpoczecia,
                    data_zakonczenia=oferta.data_zakonczenia,
                    kwota=oferta.cena,
                    grupa=grupa
                )
                historia_ofert_grupowych.save()

            return redirect('oferty')  # Przekierowanie po utworzeniu oferty
    else:
        form = KreatorOfertaForm()

    context = {
        'top_best_sellers': top_best_sellers,
        'top_worst_sellers': top_worst_sellers,
        'form': form,
    }

    return render(request, 'kreator_ofert.html', context)


@require_GET
def prod_info(request, produkt_id):
    try:
        # Pobierz produkt
        produkt = Produkt.objects.get(id=produkt_id)
    except Produkt.DoesNotExist:
        return JsonResponse({'error': 'Produkt nie istnieje'}, status=404)

    # Zakres czasowy: ostatnie 31 dni
    end_date = now()
    start_date = end_date - timedelta(days=31)

    # Pobierz wszystkie pozycje zamówień dla tego produktu w ostatnich 31 dniach
    pozycje = PozycjaZamowienia.objects.filter(
        produkt=produkt,
        zamowienie__data_utworzenia__range=(start_date, end_date)
    )

    # Oblicz liczbę sprzedanych sztuk i zarobki
    sprzedane_sztuki = pozycje.aggregate(suma_sztuk=Sum('ilosc'))['suma_sztuk'] or 0
    zarobki = pozycje.aggregate(
        suma_zarobkow=Sum(F('ilosc') * F('cena'))
    )['suma_zarobkow'] or 0

    # Przygotowanie danych do wykresu
    # Grupowanie sprzedaży po dniach
    from django.db.models.functions import TruncDay
    sprzedaz_dzienna = pozycje.annotate(
        dzien=TruncDay('zamowienie__data_utworzenia')
    ).values('dzien').annotate(
        suma_sztuk=Sum('ilosc')
    ).order_by('dzien')

    # Przygotowanie danych do wykresu
    labels = []
    sprzedaz = []

    current_date = start_date
    while current_date <= end_date:
        labels.append(current_date.strftime('%Y-%m-%d'))
        sprzedaz_na_dzien = next(
            (item['suma_sztuk'] for item in sprzedaz_dzienna if item['dzien'].date() == current_date.date()), 0
        )
        sprzedaz.append(sprzedaz_na_dzien)
        current_date += timedelta(days=1)

    return JsonResponse({
        'produkt': produkt.nazwa,
        'cena': str(produkt.cena),  # Bazowa cena produktu
        'sprzedane_sztuki': sprzedane_sztuki,
        'zarobki': round(zarobki, 2),
        'labels': labels,
        'sprzedaz': sprzedaz,
    })

@csrf_exempt
@require_POST
def grupa_info_post(request):
    try:
        data = json.loads(request.body)
        klienci_ids = data.get('klienci', [])
        grupy_ids = data.get('grupy', [])
        produkt_id = data.get('produkt_id', None)

        if produkt_id is None:
            return JsonResponse({'error': 'Nie został wybrany produkt.'}, status=400)

        # Pobierz produkt
        try:
            produkt = Produkt.objects.get(id=produkt_id)
        except Produkt.DoesNotExist:
            return JsonResponse({'error': 'Wybrany produkt nie istnieje.'}, status=404)

        # Definicja zakresu czasowego
        end_date = timezone.now()
        start_date = end_date - timedelta(days=31)

        # Obliczenia dla klientów
        klienci_info = []
        if klienci_ids:
            klienci = Klient.objects.filter(id__in=klienci_ids).select_related('uzytkownik')
            # Filtrujemy PozycjaZamowienia dla wybranego produktu, klientów i okresu
            pozycje_klientow = PozycjaZamowienia.objects.filter(
                produkt=produkt,
                zamowienie__uzytkownik__in=klienci.values('uzytkownik'),
                zamowienie__data_utworzenia__range=(start_date, end_date)
            ).annotate(zarobek=F('ilosc') * F('cena'))

            # Grupowanie po kliencie
            pozycje_klientow = pozycje_klientow.values(
                'zamowienie__uzytkownik__klient__imie',
                'zamowienie__uzytkownik__klient__nazwisko'
            ).annotate(
                sprzedane_sztuki=Sum('ilosc'),
                zarobki=Sum('zarobek')
            )

            for pozycja in pozycje_klientow:
                klienci_info.append({
                    'imie': pozycja['zamowienie__uzytkownik__klient__imie'],
                    'nazwisko': pozycja['zamowienie__uzytkownik__klient__nazwisko'],
                    'sprzedane_sztuki': pozycja['sprzedane_sztuki'],
                    'zarobki': pozycja['zarobki'],
                })

        # Obliczenia dla grup
        grupy_info = []
        if grupy_ids:
            # Pobranie obiektów Grupa
            grupy = Grupa.objects.filter(id__in=grupy_ids)

            # Pobierz wszystkich klientów w wybranych grupach
            klienci_w_grupie = Klient.objects.filter(grupy__grupa__in=grupy).distinct()

            # Pobranie zamówień dla klientów w grupach
            zamowienia_grup = Zamowienie.objects.filter(
                uzytkownik__klient__in=klienci_w_grupie
            )

            # Pozycje zamówień dla wybranego produktu i klientów w grupach
            pozycje_grup = PozycjaZamowienia.objects.filter(
                produkt=produkt,
                zamowienie__in=zamowienia_grup,
                zamowienie__data_utworzenia__range=(start_date, end_date)
            ).annotate(zarobek=F('ilosc') * F('cena'))

            # Grupowanie wyników po nazwie grupy
            pozycje_grup = pozycje_grup.values(
                'zamowienie__uzytkownik__klient__grupy__grupa__nazwa'
            ).annotate(
                sprzedane_sztuki=Sum('ilosc'),
                zarobki=Sum('zarobek')
            )

            # Dodanie statystyk dla każdej grupy
            for grupa in grupy:
                # Filtrowanie wyników dla danej grupy
                statystyki_grupy = next(
                    (p for p in pozycje_grup if
                     p['zamowienie__uzytkownik__klient__grupy__grupa__nazwa'] == grupa.nazwa),
                    None
                )
                if statystyki_grupy:
                    grupy_info.append({
                        'nazwa': grupa.nazwa,
                        'sprzedane_sztuki': statystyki_grupy['sprzedane_sztuki'],
                        'zarobki': statystyki_grupy['zarobki'],
                    })
                else:
                    # Brak danych dla grupy
                    grupy_info.append({
                        'nazwa': grupa.nazwa,
                        'sprzedane_sztuki': 0,
                        'zarobki': 0,
                    })

        return JsonResponse({
            'klienci': klienci_info,
            'grupy': grupy_info,
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Niepoprawny format JSON.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
def delete_group(request):
    """
    Usuwa grupę, jeśli użytkownik potwierdzi nazwę grupy.
    """
    grupa_id = request.POST.get('grupa_id')
    confirmation_name = request.POST.get('confirmation_name')

    # Pobranie grupy
    grupa = get_object_or_404(Grupa, id=grupa_id)

    print(grupa.nazwa)
    print(confirmation_name)
    # Sprawdzenie poprawności wpisanej nazwy
    if grupa.nazwa != confirmation_name:
        return JsonResponse({'success': False, 'message': 'Nazwa grupy nie jest poprawna.'}, status=400)

    # Usunięcie grupy
    grupa.delete()
    return JsonResponse({'success': True, 'message': f'Grupa {grupa.nazwa} została usunięta.'})


####################################
def create_campaign(request):
    if request.method == 'POST':
        form = CampaignCreationForm(request.POST)
        if form.is_valid():
            # Pobranie danych z formularza
            start_time = form.cleaned_data['start_time']
            warunek = {}
            data_rozpoczecia = None

            if start_time == 'now':
                data_rozpoczecia = now()
            elif start_time == 'condition':
                condition_type = form.cleaned_data['condition_type']
                if condition_type == 'sprzedaz_przedmiotu':
                    warunek = {
                        'typ': 'sprzedaz_przedmiotu',
                        'produkt_id': form.cleaned_data['produkt'].id,
                        'wartosc': form.cleaned_data['min_sprzedaz']
                    }
                elif condition_type == 'liczba_osob_w_grupie':
                    warunek = {
                        'typ': 'liczba_osob_w_grupie',
                        'grupa_id': form.cleaned_data['grupa'].id,
                        'wartosc': form.cleaned_data['min_osob_grupy']
                    }
                elif condition_type == 'liczba_klientow':
                    warunek = {
                        'typ': 'liczba_klientow',
                        'wartosc': form.cleaned_data['min_klientow']
                    }
                elif condition_type == 'liczba_zakupow':
                    warunek = {
                        'typ': 'liczba_zakupow',
                        'wartosc': form.cleaned_data['min_zakupow']
                    }
            elif start_time == 'days':
                days = form.cleaned_data['start_days']
                data_rozpoczecia = now() + timedelta(days=days)

            # Grupy docelowe
            grupy = form.cleaned_data['target_groups']

            # Produkty i ceny
            produkty = form.cleaned_data['products']
            ceny = []
            for produkt in produkty:
                cena_field = f'cena_{produkt.id}'
                cena = request.POST.get(f'cena_{produkt.id}')
                try:
                    cena = float(cena)
                    ceny.append(cena)
                except (TypeError, ValueError):
                    form.add_error(None, f'Nieprawidłowa cena dla produktu {produkt.nazwa}.')
                    return render(request, 'create_campaign.html', {'form': form})

            # Czas trwania kampanii
            czas_trwania = form.cleaned_data['duration']

            # Utworzenie kampanii
            system_kampanii = SystemKampanii()
            system_kampanii.utworz_kampanie(data_rozpoczecia, warunek, grupy, produkty, ceny, czas_trwania)

            # Redirect do strony sukcesu
            return redirect(reverse('campaign_success'))
    else:
        form = CampaignCreationForm()

    return render(request, 'kreator_kampanii.html', {'form': form})

def campaign_success(request):
    return kampanie(request)
def kampanie(request):
    # Pobieranie kampanii
    teraz = now()
    kampanie_trwajace = Kampania.objects.filter(
        aktywowana=True,
        data_rozpoczecia__lte=teraz,
        data_rozpoczecia__gte=teraz - timedelta(days=1)  # Rozpoczęcie wczoraj lub dziś
    )

    kampanie_zaplanowane = Kampania.objects.filter(
        aktywowana=False
    )
    kampanie_przeszle = Kampania.objects.filter(
        aktywowana=True,
        data_rozpoczecia__lt=teraz - timedelta(days=1)
    )


    context = {
        'kampanie_trwajace': kampanie_trwajace,
        'kampanie_zaplanowane': kampanie_zaplanowane,
        'kampanie_przeszle': kampanie_przeszle,
    }
    return render(request, 'kampanie_podglad.html', context)

def kampania_statystyki(request, kampania_id):
    kampania = Kampania.objects.get(id=kampania_id)
    system_kampani = SystemKampanii()
    statystyki = system_kampani.pobierz_statystyki_kampanii(kampania)

    # Pobieranie ofert związanych z kampanią
    oferty = KampaniaProdukt.objects.filter(kampania=kampania).select_related('produkt')
    oferty_html = ''.join([
        f"<p>{oferta.produkt.nazwa}: {oferta.cena} PLN</p>" for oferta in oferty
    ])

    # Pobieranie grup związanych z kampanią
    grupy = kampania.grupy.all()
    grupy_html = ''.join([
        f"<p>{grupa.nazwa}</p>" for grupa in grupy
    ])

    data = {
        'statsHtml': ''.join([
            f"<p>{stat['produkt']}: {stat['liczba_sprzedanych']} sprzedane, {stat['przychod']} PLN przychodu</p>"
            for stat in statystyki
        ]),
        'labels': statystyki[0]['dni'] if statystyki else [],
        'sprzedaz': [sum(stat['sprzedaz_dzienna']) for stat in statystyki],
        'przychod': [stat['przychod'] for stat in statystyki],
        'ofertyHtml': oferty_html,
        'grupyHtml': grupy_html,
    }
    return JsonResponse(data)



@csrf_exempt
def notatki(request):
    if request.method == "POST":
        action = request.POST.get('action')

        if action == "dodaj":
            tytul = request.POST.get('tytul', 'Nowa Notatka')
            tresc = request.POST.get('tresc', '')
            kolor = request.POST.get('kolor', '#ffffff')
            notatka = Notatka.objects.create(tytul=tytul, tresc=tresc, kolor=kolor)
            return JsonResponse({'id': notatka.id, 'tytul': notatka.tytul, 'kolor': notatka.kolor})

        elif action == "edytuj":
            notatka_id = request.POST.get('id')
            notatka = get_object_or_404(Notatka, id=notatka_id)
            notatka.tytul = request.POST.get('tytul', notatka.tytul)
            notatka.tresc = request.POST.get('tresc', notatka.tresc)
            notatka.kolor = request.POST.get('kolor', notatka.kolor)
            notatka.save()
            return JsonResponse({'success': True})

    notatki = Notatka.objects.all().order_by('-data_aktualizacji')
    return render(request, 'notatki.html', {'notatki': notatki})


def notatka_szczegoly(request, notatka_id):
    notatka = get_object_or_404(Notatka, id=notatka_id)
    return JsonResponse({
        'id': notatka.id,
        'tytul': notatka.tytul,
        'tresc': notatka.tresc,
        'kolor': notatka.kolor
    })
