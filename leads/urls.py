from django.urls import path

from leads import views

app_name = "leads"

urlpatterns = [
    path("zayavka/", views.lead_create, name="create"),
    path("spasibo/", views.thanks, name="thanks"),
]
