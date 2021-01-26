"""mes URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
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
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.documentation import include_docs_urls

# 修改后
# 配置swgger
from plan.views import IndexView
from system.views import index

schema_view = get_schema_view(
    openapi.Info(
        title="MES-API",
        default_version='v1.0',
        description="MES接口文档",
        terms_of_service="#",
        contact=openapi.Contact(email="demo"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/basics/', include('basics.urls')),
    path('api/v1/system/', include('system.urls')),
    path('api/v1/recipe/', include('recipe.urls')),
    path('api/v1/plan/', include('plan.urls')),
    path('api/v1/production/', include('production.urls')),
    path('api/v1/inventory/', include('inventory.urls')),
    path('api/v1/quality/', include('quality.urls')),
    path('api/v1/spareparts/', include('spareparts.urls')),
    path('api/v1/terminal/', include('terminal.urls')),
    path('api/v1/equipment/', include('equipment.urls')),
    path('favicon.ico', RedirectView.as_view(url='static/m.ico')),
    path('api/v1/index/', IndexView.as_view()),  # 首页展示
]

if settings.DEBUG:
    urlpatterns += [
        path('docs/', include_docs_urls(title="Mes系统文档", description="Mes系统文档")),
        path('api-auth/', include('rest_framework.urls')),
        path('api/v1/docs/', include('docs.urls')),
        path('', index, name='index')
    ]
