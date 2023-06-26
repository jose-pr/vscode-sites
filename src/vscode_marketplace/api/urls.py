from django.urls import path, include
from rest_framework import routers

from . import views


router = routers.DefaultRouter()
router.register(r"extension", views.GalleryExtensionViewSet)

urlpatterns = [
    path("public/gallery/extensionquery", views.extensionquery, name=""),
    path("test/", include(router.urls)),
]
