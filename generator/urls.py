# generator/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('features/', views.features, name='features'),
    path('pricing/', views.pricing, name='pricing'),
    path('documentation/', views.documentation, name='documentation'),
    path('help-center/', views.help_center, name='help_center'),
    path('contact/', views.contact, name='contact'),
    path('api/', views.api, name='api'),
    path('edit/', views.edit_readme, name='edit_readme'),
    path('edit/save/', views.save_readme, name='save_readme'),
    path('result/', views.result, name='result'),
]