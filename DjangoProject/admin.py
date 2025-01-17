from django.contrib import admin
from .models import Uzytkownik, Klient, Produkt, Koszyk, PozycjaKoszyka, Zamowienie, PozycjaZamowienia, Oferta, \
    OfertaSpersonalizowana, GrupaKlient, Grupa, GrupaCondition, KampaniaProdukt, Kampania

admin.site.register(Uzytkownik)
admin.site.register(Klient)
admin.site.register(Produkt)
admin.site.register(Koszyk)
admin.site.register(PozycjaKoszyka)
admin.site.register(Zamowienie)
admin.site.register(PozycjaZamowienia)
admin.site.register(Oferta)
admin.site.register(OfertaSpersonalizowana)
admin.site.register(GrupaKlient)
admin.site.register(Grupa)
admin.site.register(GrupaCondition)
admin.site.register(Kampania)
admin.site.register(KampaniaProdukt)