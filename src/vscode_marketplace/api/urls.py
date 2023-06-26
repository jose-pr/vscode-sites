from django.urls import path
from . import views

urlpatterns = [path("public/gallery/extensionquery", views.extensionquery, name="")]
