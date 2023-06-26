"""
URL configuration for vscode_sites project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include, register_converter

from .api import urls as api
from .converters import SemVerConverter
from . import views

register_converter(SemVerConverter, 'semver')

urlpatterns = [
    path("items", views.items, name='items'),
    path('assets/extensions/<str:publisher>/<str:extension>/<semver:version>/<str:asset>', views.assets_extensions),
    path("_apis/", include(api))
]


#https://ms-python.gallerycdn.vsassets.io/extensions/ms-python/python/2023.11.11741005/1687514914699/Microsoft.VisualStudio.Code.Manifest