from django.urls import path

from . import views

app_name = "website"

urlpatterns = [
    path("orders/submit/", views.submit_order, name="submit_order"),
    path("", views.home, name="home"),
    path("catalog/", views.catalog, name="catalog"),
    path("news/", views.news, name="news"),
]
