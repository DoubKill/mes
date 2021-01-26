from django.shortcuts import render

# Create your views here.
from rest_framework.viewsets import ModelViewSet

from basics.models import Equip
from equipment.serializers import EquipRealtimeSerializer


class EquipRealtimeViewSet(ModelViewSet):

    queryset = Equip.objects.filter(delete_flag=False).\
        select_related('category__equip_type__global_name').\
        prefetch_related('equip_current_status_equip__status', 'equip_current_status_equip__user')
    pagination_class = None
    serializer_class = EquipRealtimeSerializer
