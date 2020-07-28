from django.shortcuts import render

# Create your views here.
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

from basics.views import CommonDeleteMixin
from mes.derorators import api_recorder
from recipe.filters import MaterialFilter
from recipe.models import Material
from recipe.serializers import MaterialSerializer


@method_decorator([api_recorder], name="dispatch")
class MaterialViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        原材料列表
    create:
        原材料设备
    update:
        修改原材料
    destroy:
        删除原材料
    """
    queryset = Material.objects.filter(delete_flag=False)
    serializer_class = MaterialSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialFilter



