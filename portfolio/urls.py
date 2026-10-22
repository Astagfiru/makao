from django.urls import path

from portfolio import views

app_name = "portfolio"

urlpatterns = [
    path("portfolio/", views.case_list, name="list"),
    path("portfolio/<slug:slug>/", views.case_detail, name="case"),
    path("primery/<slug:slug>/", views.example, name="demo"),
    path("primery/<slug:slug>/zapis/", views.book, name="book"),
    path("primery/<slug:slug>/zakaz/", views.order, name="order"),
    path("primery/<slug:slug>/gotovo/<str:kind>/<int:number>/", views.done, name="done"),
    path("primery/<slug:slug>/oplata/<str:kind>/<int:number>/", views.pay, name="pay"),
    path("primery/<slug:slug>/status/", views.track, name="track"),
    path("primery/<slug:slug>/kabinet/", views.cabinet, name="cabinet"),
    path("demo/<slug:slug>/", views.old_demo_url),  # старые ссылки
]
