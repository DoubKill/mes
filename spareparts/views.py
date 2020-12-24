import datetime

from django.shortcuts import render

# Create your views here.
from django.utils.decorators import method_decorator
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from mes.derorators import api_recorder
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from recipe.models import Material, MaterialAttribute
from spareparts.filters import MaterialLocationBindingFilter, SpareInventoryLogFilter, SpareInventoryFilter, \
    SpareLocationFilter, SpareTypeFilter, SpareFilter
from spareparts.models import SpareInventory, SpareLocationBinding, SpareInventoryLog, Spare, SpareLocation, SpareType
from spareparts.serializers import SpareInventorySerializer, MaterialLocationBindingSerializer, \
    SpareInventoryLogSerializer, SpareLocationSerializer, SpareTypeSerializer, SpareSerializer
from rest_framework import status
from rest_framework.response import Response
from django.db.models import Sum
from django.db.transaction import atomic

from spareparts.tasks import spare_template, spare_upload, spare_inventory_template


@method_decorator([api_recorder], name="dispatch")
class SpareLocationBindingViewSet(ModelViewSet):
    """位置点和物料绑定"""
    queryset = SpareLocationBinding.objects.filter(delete_flag=False).all()
    serializer_class = MaterialLocationBindingSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialLocationBindingFilter

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        si_obj = instance.location.si_spare_location.all().filter(qty__gt=0).first()
        if si_obj:
            raise ValidationError('此库存位已经有物料了,不允许删除')
        instance.delete_flag = True
        instance.last_updated_user = request.user
        instance.save()
        SpareInventory.objects.filter(spare=instance.spare, location=instance.location).update(delete_flag=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'location', 'spare', 'location__name')
            for data_dict in data:
                data_dict.update({'name': data_dict.pop("location__name")})
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class SpareInventoryViewSet(ModelViewSet):
    """备品备件库"""
    queryset = SpareInventory.objects.filter(delete_flag=False).all().order_by('location__name')
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

        befor_total_count = si_obj.total_count
        total_count_add = befor_total_count + qty * si_obj.spare.cost
        si_obj.total_count = total_count_add

        si_obj.save()
        SpareInventoryLog.objects.create(warehouse_no=si_obj.warehouse_info.no,
                                         warehouse_name=si_obj.warehouse_info.name,
                                         location=si_obj.location.no,
                                         qty=+qty, quality_status=si_obj.quality_status,
                                         spare_no=si_obj.spare.no,
                                         spare_name=si_obj.spare.name,
                                         spare_type=si_obj.spare.type.name if si_obj.spare.type else '',
                                         cost=qty * si_obj.spare.cost,
                                         unit_count=si_obj.spare.cost, fin_time=datetime.date.today(),
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

        befor_total_count = si_obj.total_count
        total_count_subtract = befor_total_count - qty * si_obj.spare.cost
        si_obj.total_count = total_count_subtract

        si_obj.save()
        SpareInventoryLog.objects.create(warehouse_no=si_obj.warehouse_info.no,
                                         warehouse_name=si_obj.warehouse_info.name,
                                         location=si_obj.location.no,
                                         qty=-qty, quality_status=si_obj.quality_status,
                                         spare_no=si_obj.spare.no,
                                         spare_name=si_obj.spare.name,
                                         spare_type=si_obj.spare.type.name if si_obj.spare.type else '',
                                         cost=qty * si_obj.spare.cost,
                                         unit_count=si_obj.spare.cost, fin_time=datetime.date.today(),
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

        total_count_subtract = qty * si_obj.spare.cost
        si_obj.total_count = total_count_subtract

        si_obj.save()

        SpareInventoryLog.objects.create(warehouse_no=si_obj.warehouse_info.no,
                                         warehouse_name=si_obj.warehouse_info.name,
                                         location=si_obj.location.no,
                                         qty=qty, quality_status=si_obj.quality_status,
                                         spare_no=si_obj.spare.no,
                                         spare_name=si_obj.spare.name,
                                         spare_type=si_obj.spare.type.name if si_obj.spare.type else '',
                                         cost=qty * si_obj.spare.cost,
                                         unit_count=si_obj.spare.cost, fin_time=datetime.date.today(),
                                         type='数量变更',
                                         src_qty=befor_qty, dst_qty=si_obj.qty, reason=reason, created_user=request.user
                                         )
        return Response('盘点成功')

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated], url_path='count_spare_inventory',
            url_name='count_spare_inventory')
    def count_spare_inventory(self, request, pk=None):
        """统计"""
        query_params = self.request.query_params
        spare_no = query_params.get('spare_no', None)
        spare_name = query_params.get('spare_name', None)
        type_name = query_params.get('type_name', None)
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
        if spare_no:
            filter_dict.update(spare__no=spare_no)
        if spare_name:
            filter_dict.update(spare__name=spare_name)
        if type_name:
            filter_dict.update(spare__type__name=type_name)
        si_set = SpareInventory.objects.filter(**filter_dict).values('spare__name',
                                                                     'spare__no').annotate(
            sum_qty=Sum('qty'), total_count=Sum('total_count'))
        for si_obj in si_set:
            m_obj = Spare.objects.filter(no=si_obj['spare__no'],
                                         name=si_obj['spare__name'], delete_flag=False).first()

            si_obj['unit_count'] = m_obj.cost
            si_obj['type_name'] = m_obj.type.name
            si_obj['unit'] = m_obj.unit

            if si_obj['sum_qty'] < m_obj.lower:
                bound = '-'
            elif si_obj['sum_qty'] > m_obj.upper:
                bound = '+'

            else:
                bound = None

            si_obj['bound'] = bound
        count = len(si_set)
        result = si_set[st:et]
        return Response({'results': result, "count": count})


@method_decorator([api_recorder], name="dispatch")
class SpareInventoryLogViewSet(ModelViewSet):
    """履历"""
    queryset = SpareInventoryLog.objects.filter(delete_flag=False).all().order_by('location')
    serializer_class = SpareInventoryLogSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = SpareInventoryLogFilter

    @action(methods=['patch'], detail=True, permission_classes=[IsAuthenticated], url_path='revocation_log',
            url_name='revocation_log')
    def revocation_log(self, request, pk=None):
        """出库撤销"""
        sil_obj = self.get_object()
        if sil_obj.type == '出库':
            sil_obj.status = 2
            sil_obj.save()
            sl_obj = SpareLocation.objects.get(no=sil_obj.location)
            s_obj = Spare.objects.get(no=sil_obj.spare_no)
            si_obj = SpareInventory.objects.filter(spare=s_obj, location=sl_obj, delete_flag=False).first()

            befor_qty = si_obj.qty
            qty_add = befor_qty + abs(sil_obj.qty)
            si_obj.qty = qty_add

            befor_total_count = si_obj.total_count
            total_count_add = befor_total_count + abs(sil_obj.qty) * si_obj.spare.cost
            si_obj.total_count = total_count_add

            si_obj.save()

            return Response('撤销成功')
        else:
            raise ValidationError('只有出库履历还可以撤销')


@method_decorator([api_recorder], name="dispatch")
class SpareTypeViewSet(ModelViewSet):
    """备品备件类型"""
    queryset = SpareType.objects.all()
    serializer_class = SpareTypeSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = SpareTypeFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'name', 'no', 'delete_flag')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.delete_flag:
            instance.delete_flag = False
        else:
            s_obj = instance.s_spare_type.all().filter(delete_flag=False).first()
            if s_obj:
                raise ValidationError('此类型已被备品备件物料绑定了，不可禁用')
            instance.delete_flag = True
        instance.last_updated_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class SpareViewSet(ModelViewSet):
    """备品备件信息"""
    queryset = Spare.objects.filter(delete_flag=False).all()
    serializer_class = SpareSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = SpareFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'name', 'no')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        slb_obj = instance.slb_spare.all().filter(delete_flag=False).first()
        if slb_obj:
            raise ValidationError('此物料已经和库存位绑定了，不能删除')
        instance.delete_flag = True
        instance.last_updated_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class SpareLocationViewSet(ModelViewSet):
    """位置点"""
    queryset = SpareLocation.objects.filter(delete_flag=False).all()
    serializer_class = SpareLocationSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = SpareLocationFilter

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated], url_path='name_list',
            url_name='name_list')
    def name_list(self, request, pk=None):
        """展示Location所以的name"""
        name_list = SpareLocation.objects.filter(delete_flag=False).all().values('id', 'name', 'used_flag')
        # names = list(set(name_list))
        return Response(name_list)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.used_flag:
            mlb_obj = SpareLocationBinding.objects.filter(location=instance, delete_flag=False).first()
            if mlb_obj:
                raise ValidationError('此站点已经绑定了物料，无法禁用！')
            instance.used_flag = 0
        else:
            instance.used_flag = 1
        instance.last_updated_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        query_params = self.request.query_params
        type_name = query_params.getlist('type_name[]')
        if not type_name:
            return super().get_queryset()
        l_set = SpareLocation.objects.filter(type__global_name__in=type_name).all()
        return l_set


class SpareImportExportAPIView(APIView):
    """备品备件基本信息导入导出"""

    def get(self, request, *args, **kwargs):
        """备品备件基本信息模板导出"""

        return spare_template()

    @atomic()
    def post(self, request, *args, **kwargs):
        """备品备件基本信息导入"""
        spare_upload(request, 1)
        return Response('导入成功')


class SpareInventoryImportExportAPIView(APIView):
    """备品备件入库信息导入导出"""

    def get(self, request, *args, **kwargs):
        """备品备件入库信息模板导出"""
        return spare_inventory_template()

    @atomic()
    def post(self, request, *args, **kwargs):
        """备品备件入库信息导入"""
        spare_upload(request, 2)
        return Response('导入成功')
