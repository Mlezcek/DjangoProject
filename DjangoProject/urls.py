
from django.urls import path
from . import views
from django.contrib import admin

from .views import clients_crm, products_stats

urlpatterns = [

path('admin/', admin.site.urls),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),

    path('account/', views.account, name='account'),
    path('', views.home, name='home'),

    path('search_results/', views.search_results, name='search_results'),

    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
     path('cart/', views.view_cart, name='view_cart'),
    path('remove_from_cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update_quantity/<int:item_id>/', views.update_quantity, name='update_quantity'),
    path('create_order/', views.create_order, name='create_order'),

path('produkty/', views.all_products, name='all_products'),

path('orders/', views.user_orders, name='user_orders'),
path('dashboard/', views.dashboard, name='dashboard'),
path('klienci/', clients_crm, name='clients_crm'),
path('products_stats/', products_stats, name='products_stats'),

path('grupy/', views.groups_stats, name='groups_stats'),
path('grupy/oferta/', views.create_group_offer, name='create_group_offer'),

path('grupy/create/', views.create_group, name='create_group'),

path('predykcje/', views.predykcje, name='predykcje'),
    path('oferty/', views.oferty, name='oferty'),
path('kreator_ofert/', views.kreator_ofert, name='kreator_ofert'),
    path('api/prod_info/<int:produkt_id>/', views.prod_info, name='prod_info'),
    path('api/grupa_info/', views.grupa_info_post, name='grupa_info_post'),
path('prognoza_sprzedazy/<int:produkt_id>/', views.prognoza_sprzedazy, name='prognoza_sprzedazy'),
    path('delete_group/', views.delete_group, name='delete_group'),
path('create_campaign/', views.create_campaign, name='create_campaign'),
    path('campaign_success/', views.campaign_success, name='campaign_success'),
    path('oferta/<str:typ>/<int:offer_id>/przedluz/', views.przedluz_oferte, name='przedluz_oferte'),
    path('oferta/<str:typ>/<int:offer_id>/zakoncz/', views.zakoncz_oferte, name='zakoncz_oferte'),

path('kampanie/', views.kampanie, name='kampanie'),
path('kampania/<int:kampania_id>/statystyki/', views.kampania_statystyki, name='kampania_statystyki'),
path('notatki/', views.notatki, name='notatki_lista'),
path('notatki/<int:notatka_id>/', views.notatka_szczegoly, name='notatka_szczegoly'),
]
