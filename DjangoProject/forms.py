
from django import forms
from django.forms import inlineformset_factory
from .models import Produkt, GrupaCondition, Oferta, Klient, Kampania
from django import forms
from .models import Grupa
from django import forms
from .models import Grupa, GrupaCondition, Produkt

class OfertaSpersonalizowanaForm(forms.Form):
    produkt = forms.ModelChoiceField(
        queryset=Produkt.objects.all(),
        label="Przedmiot"
    )
    data_rozpoczecia = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Data rozpoczęcia"
    )
    data_zakonczenia = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Data zakończenia"
    )
    cena = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Kwota"
    )
    powod = forms.CharField(
        max_length=255,
        label="Powód"
    )


class GrupaForm(forms.ModelForm):
    class Meta:
        model = Grupa
        fields = ['nazwa', 'opis', 'color', 'is_predefined']
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
            'opis': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'nazwa': 'Nazwa Grupy',
            'opis': 'Opis Grupy',
            'color': 'Kolor Grupy',
            'is_predefined': 'Grupa Predefiniowana',
        }

    def clean_nazwa(self):
        nazwa = self.cleaned_data.get('nazwa')
        if Grupa.objects.filter(nazwa__iexact=nazwa).exists():
            raise forms.ValidationError("Grupa o tej nazwie już istnieje.")
        return nazwa


class GrupaWithConditionForm(forms.ModelForm):
    class Meta:
        model = Grupa
        fields = ['nazwa', 'opis', 'color', 'is_predefined']
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
            'opis': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'nazwa': 'Nazwa Grupy',
            'opis': 'Opis Grupy',
            'color': 'Kolor Grupy',
            'is_predefined': 'Grupa Predefiniowana',
        }

    condition_type = forms.ChoiceField(
        choices=GrupaCondition.CONDITION_TYPE_CHOICES,
        label="Typ Warunku",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    produkt = forms.ModelChoiceField(
        queryset=Produkt.objects.all(),
        required=False,
        label="Produkt",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    min_ilosc = forms.IntegerField(
        required=False,
        label="Minimalna Ilość",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    max_ilosc = forms.IntegerField(
        required=False,
        label="Maksymalna Ilość",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    days_last = forms.IntegerField(
        required=False,
        label="Liczba Dni",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    min_wydano = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Minimalna Kwota Wydana",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    max_wydano = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Maksymalna Kwota Wydana",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    min_wydano_total = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Minimalna Całkowita Kwota Wydana",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    max_wydano_total = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Maksymalna Całkowita Kwota Wydana",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    min_dni = forms.IntegerField(
        required=False,
        label="Minimalny Wiek Konta (dni)",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    max_dni = forms.IntegerField(
        required=False,
        label="Maksymalny Wiek Konta (dni)",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        condition_type = cleaned_data.get('condition_type')

        if condition_type == 'purchase_item':
            if not cleaned_data.get('produkt'):
                self.add_error('produkt', 'To pole jest wymagane dla tego typu warunku.')
            if cleaned_data.get('min_ilosc') is None:
                self.add_error('min_ilosc', 'To pole jest wymagane dla tego typu warunku.')
        elif condition_type == 'spend_last_days':
            if cleaned_data.get('days_last') is None:
                self.add_error('days_last', 'To pole jest wymagane dla tego typu warunku.')
            if cleaned_data.get('min_wydano') is None:
                self.add_error('min_wydano', 'To pole jest wymagane dla tego typu warunku.')
        elif condition_type == 'spend_total':
            if cleaned_data.get('min_wydano_total') is None:
                self.add_error('min_wydano_total', 'To pole jest wymagane dla tego typu warunku.')
        elif condition_type == 'account_age':
            if cleaned_data.get('min_dni') is None:
                self.add_error('min_dni', 'To pole jest wymagane dla tego typu warunku.')
        return cleaned_data


class KreatorOfertaForm(forms.ModelForm):
    klienci = forms.ModelMultipleChoiceField(
        queryset=Klient.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Klienci"
    )
    grupy = forms.ModelMultipleChoiceField(
        queryset=Grupa.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Grupy"
    )
    powod = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
        label="Powód Oferty (dla ofert spersonalizowanych)"
    )

    class Meta:
        model = Oferta
        fields = ['idPrzedmiotu', 'cena', 'data_rozpoczecia', 'data_zakonczenia']
        widgets = {
            'data_rozpoczecia': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'data_zakonczenia': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class CampaignCreationForm(forms.Form):
    # Opcje rozpoczęcia kampanii
    START_NOW = 'now'
    START_CONDITION = 'condition'
    START_DAYS = 'days'

    START_CHOICES = [
        (START_NOW, 'Brak warunku (Teraz)'),
        (START_CONDITION, 'Kiedy zostanie spełniony warunek'),
        (START_DAYS, 'Upłynie x dni'),
    ]

    # Typy w
    CONDITION_CHOICES = [
        ('sprzedaz_przedmiotu', 'Sprzedaż przedmiotu przekroczy'),
        ('liczba_osob_w_grupie', 'Liczba osób w grupie przekroczy'),
        ('liczba_klientow', 'Liczba klientów przekroczy'),
        ('liczba_zakupow', 'Liczba zakupów przekroczy'),
    ]

    # Kiedy kampania ma się rozpocząć
    start_time = forms.ChoiceField(
        choices=START_CHOICES,
        widget=forms.RadioSelect,
        label='Kiedy kampania ma się rozpocząć'
    )

    # Warunki dla kampanii
    condition_type = forms.ChoiceField(
        choices=CONDITION_CHOICES,
        required=False,
        label='Typ warunku'
    )
    produkt = forms.ModelChoiceField(
        queryset=Produkt.objects.all(),
        required=False,
        label='Produkt'
    )
    min_sprzedaz = forms.IntegerField(
        required=False,
        label='Minimalna ilość sprzedaży'
    )
    grupa = forms.ModelChoiceField(
        queryset=Grupa.objects.all(),
        required=False,
        label='Grupa'
    )
    min_osob_grupy = forms.IntegerField(
        required=False,
        label='Minimalna liczba osób w grupie'
    )
    min_klientow = forms.IntegerField(
        required=False,
        label='Minimalna liczba klientów'
    )
    min_zakupow = forms.IntegerField(
        required=False,
        label='Minimalna liczba zakupów'
    )

    # Rozpoczęcie kampanii za ile dni
    start_days = forms.IntegerField(
        required=False,
        label='Za ile dni',
        min_value=1
    )

    # Grupy docelowe
    target_groups = forms.ModelMultipleChoiceField(
        queryset=Grupa.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label='Wybierz grupy docelowe'
    )

    # Produkty objęte kampanią
    products = forms.ModelMultipleChoiceField(
        queryset=Produkt.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label='Wybierz produkty'
    )

    # Czas trwania kampanii
    duration = forms.IntegerField(
        label='Czas trwania kampanii (liczba dni)',
        min_value=1
    )
