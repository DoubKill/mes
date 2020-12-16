import datetime

from django.shortcuts import render

# Create your views here.
from django.utils.decorators import method_decorator
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from mes.derorators import api_recorder
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from spareparts.filters import MaterialLocationBindingFilter, SpareInventoryLogFilter, SpareInventoryFilter
from spareparts.models import SpareInventory, MaterialLocationBinding, SpareInventoryLog
from spareparts.serializers import SpareInventorySerializer, MaterialLocationBindingSerializer, \
    SpareInventoryLogSerializer
from rest_framework import status
from rest_framework.response import Response
from django.db.models import Sum


@method_decorator([api_recorder], name="dispatch")
class MaterialLocationBindingViewSet(ModelViewSet):
    """位置点和物料绑定"""
    queryset = MaterialLocationBinding.objects.filter(delete_flag=False).all()
    serializer_class = MaterialLocationBindingSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialLocationBindingFilter

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        si_obj = instance.location.si_location.all().filter(qty__gt=0).first()
        if si_obj:
            raise ValidationError('此库位点已经有物料了,不允许删除')
        instance.delete_flag = True
        instance.last_updated_user = request.user
        instance.save()
        SpareInventory.objects.filter(material=instance.material, location=instance.location).update(delete_flag=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'location', 'material', 'location__name')
            for data_dict in data:
                data_dict.update({'name': data_dict.pop("location__name")})
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class SpareInventoryViewSet(ModelViewSet):
    """备品备件库"""
    queryset = SpareInventory.objects.filter(delete_flag=False).all().order_by('created_date')
    serializer_class = SpareInventorySerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = SpareInventoryFilter

    @action(methods=['post'], detail=True, permission_classes=[IsAuthenticated], url_path='put_storage',
            url_name='put_storage')
    def put_storage(self, request, pk=None):
        """入库"""
        si_obj = self.get_object()
        qty = request.data.get('qty', 0)
        befor_qty = si_obj.qty
        qty_add = befor_qty + qty
        si_obj.qty = qty_add
        si_obj.save()
        SpareInventoryLog.objects.create(warehouse_no=si_obj.warehouse_info.no,
                                         warehouse_name=si_obj.warehouse_info.name,
                                         location=si_obj.location.name,
                                         qty=+qty, quality_status=si_obj.quality_status,
                                         material_no=si_obj.material.material_no,
                                         material_name=si_obj.material.material_name, fin_time=datetime.date.today(),
                                         type='入库',
                                         src_qty=befor_qty, dst_qty=si_obj.qty, created_user=request.user)
        return Response('入库成功')

    @action(methods=['post'], detail=True, permission_classes=[IsAuthenticated], url_path='out_storage',
            url_name='out_storage')
    def out_storage(self, request, pk=None):
        """出库"""
        si_obj = self.get_object()
        qty = request.data.get('qty', 0)
        receive_user = request.data.get('receive_user', None)  # 领用人
        purpose = request.data.get('purpose', None)  # 用途
        reason = request.data.get('reason', None)  # 出库原因
        befor_qty = si_obj.qty
        if befor_qty < qty:
            raise ValidationError('超过可取出数量')
        qty_subtract = befor_qty - qty
        si_obj.qty = qty_subtract
        si_obj.save()
        SpareInventoryLog.objects.create(warehouse_no=si_obj.warehouse_info.no,
                                         warehouse_name=si_obj.warehouse_info.name,
                                         location=si_obj.location.name,
                                         qty=-qty, quality_status=si_obj.quality_status,
                                         material_no=si_obj.material.material_no,
                                         material_name=si_obj.material.material_name, fin_time=datetime.date.today(),
                                         type='出库',
                                         src_qty=befor_qty, dst_qty=si_obj.qty, receive_user=receive_user,
                                         purpose=purpose, reason=reason, created_user=request.user
                                         )
        return Response('出库成功')

    @action(methods=['post'], detail=True, permission_classes=[IsAuthenticated], url_path='check_storage',
            url_name='check_storage')
    def check_storage(self, request, pk=None):
        """盘点"""
        si_obj = self.get_object()
        qty = request.data.get('qty', 0)
        reason = request.data.get('reason', None)  # 原因
        befor_qty = si_obj.qty
        si_obj.qty = qty
        si_obj.save()
        SpareInventoryLog.objects.create(warehouse_no=si_obj.warehouse_info.no,
                                         warehouse_name=si_obj.warehouse_info.name,
                                         location=si_obj.location.name,
                                         qty=qty, quality_status=si_obj.quality_status,
                                         material_no=si_obj.material.material_no,
                                         material_name=si_obj.material.material_name, fin_time=datetime.date.today(),
                                         type='数量变更',
                                         src_qty=befor_qty, dst_qty=si_obj.qty, reason=reason, created_user=request.user
                                         )
        return Response('盘点成功')

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated], url_path='count_spare_inventory',
            url_name='count_spare_inventory')
    def count_spare_inventory(self, request, pk=None):
        """统计"""
        query_params = self.request.query_params
        material_no = query_params.get('material_no', None)
        material_name = query_params.get('material_name', None)
        page = query_params.get("page", 1)
        page_size = query_params.get("page_size", 10)
        try:
            st = (int(page) - 1) * int(page_size)
            et = int(page) * int(page_size)
        except:
            raise ValidationError("page/page_size异常，请修正后重试")
        else:
            if st not in range(0, 99999):
                raise ValidationError("page/page_size值异常")
            if et not in range(0, 99999):
                raise ValidationError("page/page_size值异常")
        filter_dict = {'delete_flag': False}
        if material_no:
            filter_dict.update(material__material_no=material_no)
        if material_name:
            filter_dict.update(material__material_name=material_name)
        si_set = SpareInventory.objects.filter(**filter_dict).values('material__material_name',
                                                                     'material__material_no').annotate(
            sum_qty=Sum('qty'))
        count = len(si_set)
        result = si_set[st:et]
        return Response({'results': result, "count": count})


@method_decorator([api_recorder], name="dispatch")
class SpareInventoryLogViewSet(ModelViewSet):
    """履历"""
    queryset = SpareInventoryLog.objects.filter(delete_flag=False).all().order_by('created_date')
    serializer_class = SpareInventoryLogSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = SpareInventoryLogFilter
