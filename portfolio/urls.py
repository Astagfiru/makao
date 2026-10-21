from django.urls import path

from portfolio import views

app_name = "portfolio"

urlpatterns = [
    path("portfolio/", views.case_list, name="list"),
    path("portfolio/<slug:slug>/", views.case_detail, name="case"),
    path("demo/<slug:slug>/", views.demo, name="demo"),
]
