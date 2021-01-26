from django.shortcuts import render
from django.utils.decorators import method_decorator
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from equipment.filters import EquipDownTypeFilter, EquipDownReasonFilter
from equipment.models import EquipDownType, EquipDownReason, EquipCurrentStatus
from equipment.serializers import *
from mes.derorators import api_recorder
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.response import Response
from django.db.transaction import atomic


# Create your views here.
@method_decorator([api_recorder], name="dispatch")
class EquipDownTypeViewSet(ModelViewSet):
    """设备停机类型"""
    queryset = EquipDownType.objects.filter(delete_flag=False).all()
    serializer_class = EquipDownTypeSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipDownTypeFilter

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_flag = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'no', 'name')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class EquipDownReasonViewSet(ModelViewSet):
    """设备停机原因"""
    queryset = EquipDownReason.objects.filter(delete_flag=False).all()
    serializer_class = EquipDownReasonSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipDownReasonFilter

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_flag = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class EquipCurrentStatusList(APIView):
    """设备现况汇总"""

    def get(self, request):
        data_dict = {}
        ecs_set = EquipCurrentStatus.objects.filter(delete_flag=False).all()
        for ecs_obj in ecs_set:
            name = data_dict.get(ecs_obj.equip.category.equip_type.global_name, None)
            if not name:
                data_dict[ecs_obj.equip.category.equip_type.global_name] = [{'equip_name': ecs_obj.equip.equip_name,
                                                                             'equip_no': ecs_obj.equip.equip_no,
                                                                             'status': ecs_obj.status,
                                                                             'user': ecs_obj.user}]
            else:

                data_dict[ecs_obj.equip.category.equip_type.global_name].append({'equip_name': ecs_obj.equip.equip_name,
                                                                                 'equip_no': ecs_obj.equip.equip_no,
                                                                                 'status': ecs_obj.status,
                                                                                 'user': ecs_obj.user})
        return Response({'results': data_dict})
