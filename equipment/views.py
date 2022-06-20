import copy
import datetime
import datetime as dt
import time
import calendar
import requests
import xlrd
import xlwt

from suds.client import Client
from io import BytesIO
from itertools import chain
from django.db.models.functions import TruncMonth
from django.db.models import F, Count, ExpressionWrapper, DurationField, Min
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from basics.models import EquipCategoryAttribute
from equipment.check_status_to_msg import get_ding_uids_by_name
from equipment.filters import EquipDownTypeFilter, EquipDownReasonFilter, EquipPartFilter, EquipMaintenanceOrderFilter, \
    PropertyFilter, PlatformConfigFilter, EquipMaintenanceOrderLogFilter, EquipCurrentStatusFilter, EquipSupplierFilter, \
    EquipPropertyFilter, EquipAreaDefineFilter, EquipPartNewFilter, EquipComponentTypeFilter, \
    EquipSpareErpFilter, EquipFaultTypeFilter, EquipFaultCodeFilter, ERPSpareComponentRelationFilter, \
    EquipFaultSignalFilter, EquipMachineHaltTypeFilter, EquipMachineHaltReasonFilter, EquipOrderAssignRuleFilter, \
    EquipBomFilter, EquipJobItemStandardFilter, EquipMaintenanceStandardFilter, EquipRepairStandardFilter, \
    EquipWarehouseInventoryFilter, EquipWarehouseStatisticalFilter, EquipWarehouseOrderDetailFilter, \
    EquipWarehouseRecordFilter, EquipApplyOrderFilter, EquipApplyRepairFilter, EquipWarehouseOrderFilter, \
    EquipPlanFilter, EquipInspectionOrderFilter
from equipment.models import EquipTargetMTBFMTTRSetting, EquipWarehouseAreaComponent, EquipRepairMaterialReq, \
    EquipInspectionOrder, EquipRegulationRecord, EquipMaintenanceStandardWork, EquipOrderEntrust
from equipment.serializers import *
from equipment.serializers import EquipRealtimeSerializer
from equipment.task import property_template, property_import
from equipment.utils import gen_template_response, get_staff_status, get_ding_uids, DinDinAPI, get_maintenance_status, \
    get_children_section
from mes.common_code import OMin, OMax, OSum, CommonDeleteMixin
from mes.derorators import api_recorder
from mes.paginations import SinglePageNumberPagination
from mes.permissions import PermissionClass
from plan.models import ProductClassesPlan
from production.models import TrainsFeedbacks
from quality.utils import get_cur_sheet, get_sheet_data
from terminal.models import ToleranceDistinguish, ToleranceProject, ToleranceHandle, ToleranceRule, Plan, ReportBasic
from system.models import Section, User


@method_decorator([api_recorder], name="dispatch")
class EquipRealtimeViewSet(ModelViewSet):
    queryset = Equip.objects.filter(delete_flag=False). \
        select_related('category__equip_type__global_name'). \
        prefetch_related('equip_current_status_equip__status', 'equip_current_status_equip__user')
    pagination_class = None
    serializer_class = EquipRealtimeSerializer


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
    queryset = EquipDownReason.objects.filter(delete_flag=False).order_by('-id')
    serializer_class = EquipDownReasonSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipDownReasonFilter

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_flag = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'no', 'desc')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class EquipCurrentStatusList(APIView):
    """设备现况汇总"""

    def get(self, request):
        ecs_set = EquipCurrentStatus.objects.filter(delete_flag=False).select_related()
        temp_dict = {x.equip.category.equip_type.global_name: [] for x in ecs_set}
        for ecs_obj in ecs_set:
            temp_dict[ecs_obj.equip.category.equip_type.global_name].append({'equip_name': ecs_obj.equip.equip_name,
                                                                             'equip_no': ecs_obj.equip.equip_no,
                                                                             'status': ecs_obj.status,
                                                                             'user': ecs_obj.user})
        return Response({'results': temp_dict})


@method_decorator([api_recorder], name="dispatch")
class EquipCurrentStatusViewSet(ModelViewSet):
    """设备现况"""
    queryset = EquipCurrentStatus.objects.filter(delete_flag=False).all()
    serializer_class = EquipCurrentStatusSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)

    filter_class = EquipCurrentStatusFilter

    @atomic()
    def update(self, request, *args, **kwargs):
        data = request.data
        instance = self.get_object()
        if instance.status in ['运行中', '空转']:
            wsp_obj = WorkSchedulePlan.objects.filter(start_time__lte=data['note_time'],
                                                      end_time__gte=data['note_time'],
                                                      plan_schedule__work_schedule__work_procedure__global_name__icontains='密炼').first()
            if not wsp_obj:
                raise ValidationError('当前日期没有工厂时间')
            if data['down_flag']:
                instance.status = '停机'
                instance.save()
            EquipMaintenanceOrder.objects.create(order_uid=uuid.uuid1(),
                                                 first_down_reason=data['first_down_reason'],
                                                 first_down_type=data['first_down_type'],
                                                 order_src=1,
                                                 note_time=datetime.now(),
                                                 down_time=data['note_time'],
                                                 down_flag=data['down_flag'],
                                                 equip_part_id=data['equip_part'],
                                                 factory_date=wsp_obj.plan_schedule.day_time,
                                                 created_user=request.user)
        elif instance.status in ['停机', '维修结束']:
            instance.status = '运行中'
            instance.save()
        else:
            raise ValidationError('此状态不允许有操作')
        return Response('操作成功')


@method_decorator([api_recorder], name="dispatch")
class EquipPartViewSet(ModelViewSet):
    """设备部位"""
    queryset = EquipPart.objects.filter(delete_flag=False).order_by('-id')
    serializer_class = EquipPartSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipPartFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'no', 'name')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_flag = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class EquipMaintenanceOrderViewSet(ModelViewSet):
    """维修表单"""
    queryset = EquipMaintenanceOrder.objects.filter(delete_flag=False).order_by('-id')
    serializer_class = EquipMaintenanceOrderSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipMaintenanceOrderFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return EquipMaintenanceCreateOrderSerializer
        if self.action in ('update', 'partial_update'):
            return EquipMaintenanceOrderUpdateSerializer
        else:
            return EquipMaintenanceOrderSerializer


@method_decorator([api_recorder], name="dispatch")
class EquipMaintenanceOrderOtherView(GenericAPIView):
    queryset = EquipMaintenanceOrder.objects.filter(delete_flag=False).order_by('-id')
    serializer_class = EquipMaintenanceOrderUpdateSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipMaintenanceOrderFilter

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        instance = EquipMaintenanceOrder.objects.get(id=pk)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # self.perform_update(serializer)
        serializer.save()
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


@method_decorator([api_recorder], name="dispatch")
class PropertyTypeNodeViewSet(ModelViewSet):
    """资产类型节点"""
    queryset = PropertyTypeNode.objects.filter(delete_flag=False).all()
    serializer_class = PropertyTypeNodeSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)

    def partent_children(self, partent_set):
        options = [{'id': i.id, 'value': i.name} for i in partent_set]
        for children in options:
            partent_set = PropertyTypeNode.objects.filter(parent=children['id'], delete_flag=False).all()
            if partent_set:
                children['children'] = self.partent_children(partent_set)
        return options

    def list(self, request, *args, **kwargs):
        partent_set = PropertyTypeNode.objects.filter(parent__isnull=True, delete_flag=False).all()
        options = self.partent_children(partent_set)
        return Response(options)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if PropertyTypeNode.objects.filter(parent=instance.id, delete_flag=False).exists():
            raise ValidationError(f'{instance.name}节点有子节点，不允许删除')
        if instance.property_type_node_name.filter(delete_flag=False).exists():
            raise ValidationError(f'{instance.name}节点已被使用，不允许删除')

        instance.delete_flag = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class PropertyViewSet(ModelViewSet):
    """资产"""
    queryset = Property.objects.filter(delete_flag=False).all()
    serializer_class = PropertySerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = PropertyFilter

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_flag = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated], url_path='export-property',
            url_name='export-property')
    def export_property(self, request, pk=None):
        """模板下载"""
        return property_template()

    @action(methods=['post'], detail=False, permission_classes=[IsAuthenticated], url_path='import-property',
            url_name='import-property')
    def import_property(self, request, pk=None):
        """模板导入"""
        file = request.FILES.get('file')
        property_import(file)
        return Response('导入成功')


@method_decorator([api_recorder], name="dispatch")
class PlatformConfigViewSet(ModelViewSet):
    """通知配置"""
    queryset = PlatformConfig.objects.filter(delete_flag=False).all()
    serializer_class = PlatformConfigSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = PlatformConfigFilter

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_flag = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class EquipMaintenanceOrderLogViewSet(ModelViewSet):
    """#设备维修履历"""
    queryset = EquipMaintenanceOrder.objects.filter(delete_flag=False).order_by('equip_part__equip')
    serializer_class = EquipMaintenanceOrderLogSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipMaintenanceOrderLogFilter
    pagination_class = SinglePageNumberPagination

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            i_list = [i.get('repair_time').seconds for i in serializer.data if i.get('repair_time') is not None]
            data_list = serializer.data
            if not i_list:
                data_list.append(
                    {'max_repair_time': None, 'min_repair_time': None, 'sum_repair_time': None})
            else:
                data_list.append(
                    {'max_repair_time': max(i_list), 'min_repair_time': min(i_list), 'sum_repair_time': sum(i_list)})
            return self.get_paginated_response(data_list)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@method_decorator([api_recorder], name="dispatch")
class PersonalStatisticsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        all_flag = request.query_params.get("all")
        today = datetime.now().date()
        monday = today - dt.timedelta(days=today.weekday())
        sunday = today + dt.timedelta(days=6 - today.weekday())
        time_dispatch = {
            "日": {"factory_date": today, "down_flag": True},
            "月": {"factory_date__month": datetime.now().month, "factory_date__year": datetime.now().year,
                  "down_flag": True},
            "周": {"factory_date__range": (monday, sunday), "down_flag": True},
        }
        base_filter = {}
        ret = {}
        if not all_flag:
            base_filter = {"maintenance_user": request.user}
        for k, v in time_dispatch.items():
            filter_dict = {
                # "begin_time__isnull": False,
                # "end_time__isnull": False,
            }
            filter_dict.update(**v)
            data = EquipMaintenanceOrder.objects.filter(**base_filter, **filter_dict). \
                aggregate(min_time=OMin((F('end_time') - F('begin_time'))),
                          max_time=OMax((F('end_time') - F('begin_time'))),
                          all_time=OSum((F('end_time') - F('begin_time'))))
            data["min_time"] = data.get("min_time", 0)
            data["max_time"] = data.get("max_time", 0)
            data["all_time"] = data.get("max_time", 0)
            ret.update(**{k: data})
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class EquipErrorDayStatisticsView(APIView):

    def get(self, request, *args, **kwargs):
        day_time = request.query_params.get('day_time', '2021-03-03')
        try:
            now = datetime.strptime(day_time, "%Y-%m-%d")
        except:
            raise ValidationError("时间格式错误")
        work_schedule_plan = WorkSchedulePlan.objects.filter(
            start_time__lte=now,
            end_time__gte=now,
            plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
        if not work_schedule_plan:
            raise ValidationError(f'{now}无排班，请补充排班信息')
        day_time = work_schedule_plan.plan_schedule.day_time
        factory_date = request.query_params.get("day_time", day_time)
        temp_set = EquipMaintenanceOrder.objects.filter(factory_date=factory_date, down_flag=True)
        # 动态生成表头字段
        equip_list = list(set(temp_set.values_list('equip_part__equip__equip_no', flat=True)))
        class_list = list(
            GlobalCode.objects.filter(global_type__type_name='班次', use_flag=True).values_list('global_name', flat=True))
        class_count = len(class_list)
        time_list = [0 for _ in class_list]
        percent_list = [0 for _ in class_list]
        class_list.append(str(factory_date))
        ret = {x: {"class_name": class_list, "error_time": copy.deepcopy(time_list),
                   "error_percent": copy.deepcopy(percent_list)} for x in equip_list}
        data_set = temp_set.values('equip_part__equip__equip_no', 'class_name'). \
            annotate(all_time=OSum((F('end_time') - F('begin_time')))).values(
            'equip_part__equip__equip_no', 'class_name', 'all_time')
        for temp in data_set:
            # class_dict.update(**{temp.get('class_name'): {
            #     "error_time": temp.get("all_time"),
            #     "error_percent": round(temp.get('all_time')/(12*60), 4)},
            #     "equip": temp.get('equip_part__equip__equip_no')
            # })
            # ret.append(class_dict)
            equip_data = ret[temp.get('equip_part__equip__equip_no')]
            data_index = equip_data["class_name"].index(temp.get('class_name'))
            time_time = round(temp.get('all_time').total_seconds() / 60, 2) if temp.get('all_time') else 0
            equip_data["error_time"][data_index] = time_time
            equip_data["error_percent"][data_index] = round(time_time / (12 * 60), 4)
        for k in ret.keys():
            ret[k]["error_time"].append(round(sum(ret[k]["error_time"]), 2))
            ret[k]["error_percent"].append(round(sum(ret[k]["error_percent"]) / class_count, 4))
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class EquipErrorMonthStatisticsView(APIView):

    def get(self, request, *args, **kwargs):
        month_time = request.query_params.get('day_time', '2021-03-03')
        try:
            now = datetime.strptime(month_time, "%Y-%m-%d")
        except:
            raise ValidationError("时间格式错误")
        month = now.month
        year = now.year
        temp_set = EquipMaintenanceOrder.objects.filter(factory_date__year=year, factory_date__month=month,
                                                        down_flag=True)
        title_set = set(temp_set.values("equip_part__name").annotate().values_list("equip_part__name", flat=True))
        equip_list = set(temp_set.values_list('equip_part__equip__equip_no', flat=True))
        data = {e: {} for e in equip_list}
        data_set = temp_set.values('equip_part__equip__equip_no', 'equip_part__name'). \
            annotate(all_time=OSum(F('end_time') - F('begin_time'))). \
            values('equip_part__equip__equip_no', 'equip_part__name', 'all_time').order_by(
            'equip_part__equip__equip_no')
        # data_set = temp_set.values('equip_part__equip__equip_no', 'equip_part__name'). \
        #     annotate(all_time=Sum((F('end_time') - F('begin_time')) / (1000000 * 60))). \
        #     values('equip_part__equip__equip_no', 'equip_part__name', 'all_time').order_by('equip_part__equip__equip_no')
        data_set = list(data_set)
        for temp in data_set:
            data[temp.get('equip_part__equip__equip_no')].update(**{
                temp.get('equip_part__name'): round(temp.get('all_time').total_seconds() / 60, 2) if temp.get(
                    'all_time') else 0})
        for k, v in data.items():
            data[k]["sum"] = sum(v.values())
        ret = {"equips": data,
               "title": title_set}
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class EquipErrorWeekStatisticsView(APIView):

    def get(self, request, *args, **kwargs):
        day_time = request.query_params.get('day_time', '2021-03-03')
        try:
            factory_date = datetime.strptime(day_time, "%Y-%m-%d")
        except:
            raise ValidationError("时间格式错误")
        monday = factory_date - dt.timedelta(days=factory_date.weekday())
        sunday = factory_date + dt.timedelta(days=6 - factory_date.weekday())
        temp_set = EquipMaintenanceOrder.objects.filter(factory_date__gte=monday, factory_date__lte=sunday,
                                                        down_flag=True)
        # 各个机台数据
        title_set = set(temp_set.values("equip_part__name").annotate().values_list("equip_part__name", flat=True))
        equip_list = set(temp_set.values_list('equip_part__equip__equip_no', flat=True))
        data = {e: {} for e in equip_list}
        data_set = temp_set.values('equip_part__equip__equip_no', 'equip_part__name'). \
            annotate(all_time=OSum((F('end_time') - F('begin_time')))). \
            values('equip_part__equip__equip_no', 'equip_part__name', 'all_time').order_by(
            'equip_part__equip__equip_no')
        for temp in data_set:
            data[temp.get('equip_part__equip__equip_no')].update(**{
                temp.get('equip_part__name'): round(temp.get('all_time').total_seconds() / 60, 2) if temp.get(
                    'all_time') else 0})
        for k, v in data.items():
            data[k]["sum"] = sum(v.values())
        # sorted(data.items(), key=lambda x)
        ret = {"equips": data,
               "title_set": title_set}
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class MonthErrorSortView(APIView):

    def get(self, request):
        month_time = request.query_params.get('day_time', '2021-03-03')
        try:
            now = datetime.strptime(month_time, "%Y-%m-%d")
        except:
            raise ValidationError("时间格式错误")
        month = now.month
        year = now.year
        temp_set = EquipMaintenanceOrder.objects.filter(factory_date__year=year, factory_date__month=month,
                                                        down_flag=True)
        data_set = temp_set.values('equip_part__equip__equip_no', 'equip_part__name'). \
            annotate(all_time=OSum((F('end_time') - F('begin_time')))). \
            values('equip_part__equip__equip_no', 'equip_part__name', 'all_time').order_by('all_time')
        equip_list = [x.get('equip_part__equip__equip_no') for x in data_set]
        data = {e: {} for e in equip_list}
        for temp in data_set:
            data[temp.get('equip_part__equip__equip_no')].update(**{
                temp.get('equip_part__name'): round(temp.get('all_time').total_seconds() / 60, 2) if temp.get(
                    'all_time') else 0})
        for k, v in data.items():
            data[k]["sum"] = sum(v.values())
        ret = []
        for k, v in data.items():
            new_data = {k: sorted(v.items(), key=lambda x: x[1], reverse=True)}
            ret.append(new_data)

        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class EquipOverview(APIView):

    def get(self, request):
        rep = {"cdata": {}}
        # day_time = datetime.today()
        # factory_date = datetime.strptime(day_time, "%Y-%m-%d")
        factory_date = datetime.today()
        monday = factory_date - dt.timedelta(days=factory_date.weekday())
        sunday = factory_date + dt.timedelta(days=6 - factory_date.weekday())
        temp_set = EquipMaintenanceOrder.objects.filter(factory_date__gte=monday, factory_date__lte=sunday,
                                                        down_flag=True).order_by('equip_part__equip__equip_no')
        # 各个机台周停机数据
        equip_list = list(set(temp_set.values_list('equip_part__equip__equip_no', flat=True))).sort()
        data_set = temp_set.values('equip_part__equip__equip_no'). \
            annotate(all_time=OSum((F('end_time') - F('begin_time')))). \
            values('equip_part__equip__equip_no', 'all_time').order_by(
            'equip_part__equip__equip_no')
        data_list = [round(x.get('all_time').total_seconds() / 60, 2) if x.get("all_time") else 0 for x in data_set]
        rep["cdata"]["category"] = equip_list
        rep["cdata"]["lineData"] = data_list

        # 各设备部位月故障统计
        year = factory_date.year
        month = factory_date.month
        temp_set = EquipMaintenanceOrder.objects.filter(factory_date__year=year, factory_date__month=month,
                                                        down_flag=True)
        data_set = temp_set.values('equip_part__name'). \
            annotate(all_time=OSum((F('end_time') - F('begin_time')))). \
            values('equip_part__name', 'all_time')
        part_data = [{"value": x.get('all_time'), "name": x.get("equip_part__name")} for x in data_set]
        rep["seriesData"] = part_data

        # 设备日累计故障时间
        temp_set = EquipMaintenanceOrder.objects.filter(factory_date=factory_date).values(
            'equip_part__equip__equip_no').annotate(all_time=OSum((F('end_time') - F('begin_time')))).order_by(
            'equip_part__equip__equip_no')
        day_data = [{"name": x.get('equip_part__equip__equip_no'), "value": x.get("all_time")} for x in temp_set]
        rep["data"] = day_data

        # 维修单，单日数据滚动
        temp_set = list(EquipMaintenanceOrder.objects.filter(factory_date=factory_date).order_by(
            'equip_part__equip__equip_no'))
        day_detail = [[temp_set.index(x), x.order_uid,
                       x.equip_part.equip.equip_no + "/" + x.equip_part.name,
                       x.get_status_display(), x.maintenance_user.username, x.created_date] for x in temp_set]
        sheet = {"header": ["序号", "单号", "设备部位", "状态", "操作人", "申请时间"],
                 "data": day_detail}
        rep["config"] = sheet

        temp_set = EquipCurrentStatus.objects.values("equip__equip_no",
                                                     "equip__category__equip_type__global_name").annotate(
            status=Max('status')).values("equip__category__equip_type__global_name", "equip__equip_no",
                                         "status").order_by("equip__equip_no")

        # 设备现况
        rep["current"] = {"mix": [], "weigh": [], "check": [], "others": []}
        for temp in temp_set:
            if temp.get("equip__category__equip_type__global_name") == "密炼设备":
                rep["current"]["mix"].append({"name": temp.get("equip__equip_no"), "value": temp.get("status")})
            elif temp.get("equip__category__equip_type__global_name") == "称量设备":
                rep["current"]["weigh"].append({"name": temp.get("equip__equip_no"), "value": temp.get("status")})
            elif temp.get("equip__category__equip_type__global_name") == "检测设备":
                rep["current"]["check"].append({"name": temp.get("equip__equip_no"), "value": temp.get("status")})
            else:
                rep["current"]["others"].append({"name": temp.get("equip__equip_no"), "value": temp.get("status")})
        return Response(rep)


# **************************2021-10-09最新VIEWS**************************


@method_decorator([api_recorder], name="dispatch")
class EquipSupplierViewSet(CommonDeleteMixin, ModelViewSet):
    """供应商管理台账"""
    queryset = EquipSupplier.objects.filter(delete_flag=False).order_by('-id')
    serializer_class = EquipSupplierSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipSupplierFilter

    FILE_NAME = '供应商管理台账'
    EXPORT_FIELDS_DICT = {'供应商编号': 'supplier_code',
                          '供应商名称': 'supplier_name',
                          '地域': 'region',
                          '联系人名称': 'contact_name',
                          '联系人电话': 'contact_phone',
                          '供应商类别': 'supplier_type',
                          '是否启用': 'use_flag_name',
                          '录入者': 'created_username',
                          '录入时间': 'created_date',
                          }

    """数据导出"""

    def list(self, request, *args, **kwargs):
        export = self.request.query_params.get('export')
        all = self.request.query_params.get('all')
        queryset = self.filter_queryset(self.get_queryset())
        if all:
            return Response(queryset.filter(use_flag=True).values('id', 'supplier_name'))
        if export:
            data = self.get_serializer(queryset, many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['post'], detail=False, permission_classes=[], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        if cur_sheet.ncols != len(self.EXPORT_FIELDS_DICT):
            raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet, start_row=1)
        area_list = []
        for item in data:
            lst = [i[0] for i in data]
            if lst.count(item[0]) > 1:
                raise ValidationError('导入的供应商编码不能重复')
            lst = [i[1] for i in data]
            if lst.count(item[1]) > 1:
                raise ValidationError('导入的供应商名称不能重复')
            obj = EquipSupplier.objects.filter(Q(supplier_code=item[0]) | Q(supplier_name=item[1])).first()
            if not obj:
                if item[5] not in ['普通供应商', '集采供应商']:
                    raise ValidationError('该供应商类别不存在')
                area_list.append({"supplier_code": item[0],
                                  "supplier_name": item[1],
                                  "region": item[2],
                                  "contact_name": item[3],
                                  "contact_phone": item[4] if item[4] else None,
                                  "supplier_type": item[5] if item[5] else None,
                                  })
        s = EquipSupplierSerializer(data=area_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            if len(s.validated_data) < 1:
                raise ValidationError('没有可导入的数据')
            s.save()
        else:
            raise ValidationError('供应商或编号已存在！')
        return Response(f'成功导入{len(s.validated_data)}条数据')

    @action(methods=['get'], detail=False, permission_classes=[], url_path='get_name', url_name='get_name')
    def get_name(self, request):
        try:
            dic = self.queryset.aggregate(Max('supplier_code'))
            res = dic['supplier_code__max']
            if res:
                results = res[0:3] + str('%04d' % (int(res[3:]) + 1))
                return Response({'results': results})
            return Response({'results': 'GYS0001'})
        except:
            return Response({'results': 'GYS000X'})


@method_decorator([api_recorder], name="dispatch")
class EquipPropertyViewSet(CommonDeleteMixin, ModelViewSet):
    """设备固定资产台账"""
    queryset = EquipProperty.objects.filter(delete_flag=False).order_by('-id')
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipPropertyFilter

    FILE_NAME = '设备固定资产台账'
    EXPORT_FIELDS_DICT = {
        '固定资产': 'property_no',
        '原编码': 'src_no',
        '财务编码': 'financial_no',
        '设备型号': 'equip_type_no',
        '设备编码': 'equip_no',
        '设备名称': 'equip_name',
        '设备制造商': 'made_in',
        '产能': 'capacity',
        '价格': 'price',
        '状态': 'status_name',
        '设备类型': 'equip_type_name',
        '出厂编码': 'leave_factory_no',
        '出厂日期': 'leave_factory_date',
        '使用日期': 'use_date',
        '录入人': 'created_username',
        '录入日期': 'created_date',
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return EquipPropertySerializer
        return EquipPropertyCreatSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_flag = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    """数据导出"""

    def list(self, request, *args, **kwargs):
        export = self.request.query_params.get('export')
        queryset = self.filter_queryset(self.get_queryset())
        if export:
            data = self.get_serializer(queryset, many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['post'], detail=False, permission_classes=[], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlsx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        if cur_sheet.ncols != len(self.EXPORT_FIELDS_DICT):
            raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet)
        area_list = []
        for item in data:
            obj = EquipProperty.objects.filter(equip_no=item[4], equip_name=item[5]).first()
            if not obj:
                status_dict = {'使用中': 1, '废弃': 2, '限制': 3}
                equip_type = EquipCategoryAttribute.objects.filter(category_no=item[3], use_flag=True).first()
                equip_supplier = EquipSupplier.objects.filter(supplier_name=item[6], use_flag=True).first()
                if item[12]:
                    leave_factory_date = dt.date(*map(int, item[12].split('-'))) if isinstance(item[12],
                                                                                               str) else datetime.date(
                        xlrd.xldate.xldate_as_datetime(item[12], 0))
                else:
                    leave_factory_date = None
                if item[13]:
                    use_date = dt.date(*map(int, item[13].split('-'))) if isinstance(item[13], str) else datetime.date(
                        xlrd.xldate.xldate_as_datetime(item[13], 0))
                else:
                    use_date = None
                if not equip_type:
                    raise ValidationError('导入的设备型号{}不存在'.format(item[3]))
                area_list.append({"property_no": item[0] if item[0] else None,
                                  "src_no": item[1] if item[1] else None,
                                  "financial_no": item[2] if item[2] else None,
                                  "equip_type": equip_type.id,
                                  "equip_no": item[4],
                                  "equip_name": item[5],
                                  "equip_supplier": equip_supplier.id if equip_supplier else None,
                                  "capacity": item[7] if item[7] else None,
                                  "price": item[8] if item[8] else None,
                                  "status": status_dict.get(item[9]),
                                  "equip_type_name": item[10],
                                  "leave_factory_no": item[11] if item[11] else None,
                                  "leave_factory_date": leave_factory_date,
                                  "use_date": use_date,
                                  })
        s = EquipPropertySerializer(data=area_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=True):
            if len(s.validated_data) < 1:
                raise ValidationError('没有可导入的数据')
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response(f'成功导入{len(s.validated_data)}条数据')


@method_decorator([api_recorder], name='dispatch')
class EquipAreaDefineViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipAreaDefine.objects.filter(delete_flag=False).order_by('-id')
    serializer_class = EquipAreaDefineSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipAreaDefineFilter
    FILE_NAME = '位置区域信息'
    EXPORT_FIELDS_DICT = {"位置区域编号": "area_code",
                          "位置区域名称": "area_name",
                          "巡检顺序编号": "inspection_line_no",
                          "备注说明": "desc",
                          "是否启用": "use_flag_name",
                          "录入人": "created_username",
                          "录入时间": "created_date"
                          }

    @action(methods=['post'], detail=False, permission_classes=[], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlsx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        data = get_sheet_data(cur_sheet)
        area_list = []
        for item in data:
            lst = [i[0] for i in data]
            if lst.count(item[0]) > 1:
                raise ValidationError('导入的区域编码不能重复')
            lst = [i[1] for i in data]
            if lst.count(item[1]) > 1:
                raise ValidationError('导入的区域名称不能重复')
            if type(item[2]) != int or type(item[2]) != float:
                raise ValidationError(f'巡检顺序编号导入格式有误{item[2]}')
            obj = EquipAreaDefine.objects.filter(Q(area_code=item[0]) | Q(area_name=item[1])).first()
            if not obj:
                area_list.append({"area_code": item[0],
                                  "area_name": item[1],
                                  "inspection_line_no": int(item[2]) if item[2] else None,
                                  "desc": item[3]})
        s = EquipAreaDefineSerializer(data=area_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            if len(s.validated_data) < 1:
                raise ValidationError('没有可导入的数据')
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response(f'成功导入{len(s.validated_data)}条数据')

    def list(self, request, *args, **kwargs):
        export = self.request.query_params.get('export')
        all_area = self.request.query_params.get('all')
        queryset = self.filter_queryset(self.get_queryset())
        if export:
            data = self.get_serializer(queryset, many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        if all_area:
            return Response(list(queryset.values_list('area_name', flat=True).distinct()))
        return super().list(request, *args, **kwargs)

    @action(methods=['get'], detail=False, permission_classes=[], url_path='get_name', url_name='get_name')
    def get_name(self, request):
        try:
            dic = self.queryset.aggregate(Max('area_code'))
            res = dic['area_code__max']
            if res:
                results = res[0:4] + str('%04d' % (int(res[4:]) + 1))
                return Response({'results': results})
            return Response({'results': 'WZQY0001'})
        except:
            return Response({'results': 'WZQY000X'})


@method_decorator([api_recorder], name="dispatch")
class EquipPartNewViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipPartNew.objects.all().order_by('-id')
    serializer_class = EquipPartNewSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipPartNewFilter
    FILE_NAME = '设备部位信息'
    EXPORT_FIELDS_DICT = {
                          "部位分类": "global_name",
                          "部位代码": "part_code",
                          "部位名称": "part_name",
                          "是否启用": "use_flag_name",
                          "录入人": "created_username",
                          "录入时间": "created_date"
                          }

    @action(methods=['post'], detail=False, permission_classes=[], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlsx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        if cur_sheet.ncols != len(self.EXPORT_FIELDS_DICT):
            raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet)
        parts_list = []
        for item in data:
            lst = [i[1] for i in data]
            if lst.count(item[1]) > 1:
                raise ValidationError('导入的部位编码不能重复')
            lst = [i[2] for i in data]
            if lst.count(item[2]) > 1:
                raise ValidationError('导入的部位名称不能重复')
            global_part_type = GlobalCode.objects.filter(global_name=item[0]).first()
            if not global_part_type:
                raise ValidationError('部位分类{}不存在'.format(item[0]))
            obj = EquipPartNew.objects.filter(Q(part_code=item[1]) | Q(part_name=item[2])).first()
            if not obj:
                parts_list.append({"global_part_type": global_part_type.id,
                                   "part_code": item[1],
                                   "part_name": item[2]})
        s = EquipPartNewSerializer(data=parts_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            if len(s.validated_data) < 1:
                raise ValidationError('没有可导入的数据')
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response(f'成功导入{len(s.validated_data)}条数据')

    def list(self, request, *args, **kwargs):
        export = self.request.query_params.get('export')
        queryset = self.filter_queryset(self.get_queryset())
        if export:
            data = self.get_serializer(queryset, many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        if self.request.query_params.get('all'):
            use_flag = [True] if not self.request.query_params.get('all_part') else [True, False]
            data = EquipPartNew.objects.filter(use_flag__in=use_flag).values('id', 'part_name')
            return Response({'results': data})
        return super().list(request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class EquipComponentTypeViewSet(CommonDeleteMixin, ModelViewSet):
    """设备部件分类"""
    queryset = EquipComponentType.objects.order_by('component_type_code')
    serializer_class = EquipComponentTypeSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipComponentTypeFilter
    FILE_NAME = '设备部件分类'
    EXPORT_FIELDS_DICT = {"部件分类": "component_type_code",
                          "部位名称": "component_type_name",
                          "录入人": "created_username",
                          "录入时间": "created_date"
                          }

    def list(self, request, *args, **kwargs):
        export = self.request.query_params.get('export')
        queryset = self.filter_queryset(self.get_queryset())
        if export:
            data = self.get_serializer(queryset, many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        if self.request.query_params.get('all'):
            data = EquipComponentType.objects.filter(use_flag=True).values('id', 'component_type_name')
            return Response({'results': data})
        return super().list(request, *args, **kwargs)

    @action(methods=['post'], detail=False, permission_classes=[], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlsx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        if cur_sheet.ncols != len(self.EXPORT_FIELDS_DICT):
            raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet)
        parts_list = []
        for item in data:
            lst = [i[0] for i in data]
            if lst.count(item[0]) > 1:
                raise ValidationError('导入的类型编码不能重复')
            lst = [i[1] for i in data]
            if lst.count(item[1]) > 1:
                raise ValidationError('导入的类型名称不能重复')
            obj = EquipComponentType.objects.filter(Q(component_type_code=item[0]) |
                                                    Q(component_type_name=item[1])).first()
            if not obj:
                parts_list.append({"component_type_code": item[0],
                                   "component_type_name": item[1]})
        s = EquipComponentTypeSerializer(data=parts_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            if len(s.validated_data) < 1:
                raise ValidationError('没有可导入的数据')
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response(f'成功导入{len(s.validated_data)}条数据')


@method_decorator([api_recorder], name='dispatch')
class EquipComponentViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        展示所有设备部件定义
    create:
        新建部件定义
    update:
        修改部件定义
    """
    queryset = EquipComponent.objects.all()
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    FILE_NAME = '设备部件列表'
    EXPORT_FIELDS_DICT = {
        "所属设备部位": "equip_part_name",
        "部件分类": "equip_component_type_name",
        "部件代码": "component_code",
        "部件名称": "component_name",
        "是否绑定备件": "is_binding",
        "是否启用": "use_flag_name",
        "录入人": "created_username",
        "录入时间": "created_date"
    }

    def get_queryset(self):
        query_params = self.request.query_params
        equip_part = query_params.get('equip_part')
        equip_component_type = query_params.get('equip_component_type')
        component_name = query_params.get('component_name')
        is_binding = query_params.get('is_binding')
        use_flag = query_params.get('use_flag')
        filter_kwargs = {}
        if equip_part:
            filter_kwargs['equip_part_id'] = equip_part
        if equip_component_type:
            filter_kwargs['equip_component_type__component_type_name__icontains'] = equip_component_type
        if component_name:
            filter_kwargs['component_name__icontains'] = component_name
        if is_binding:
            filter_kwargs['equip_components__isnull'] = False if is_binding == 'true' else True
        if use_flag:
            filter_kwargs['use_flag'] = use_flag
        query_set = self.queryset.filter(**filter_kwargs)
        return query_set

    def get_serializer_class(self):
        if self.action == 'list':
            return EquipComponentListSerializer
        return EquipComponentCreateSerializer

    def list(self, request, *args, **kwargs):
        export = self.request.query_params.get('export')
        component_id = self.request.query_params.get('component_id')
        query_set = self.get_queryset()
        if export:
            data = self.get_serializer(query_set, many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        if self.request.query_params.get('all'):
            data = EquipComponent.objects.filter(use_flag=True).values('id', 'component_name')
            return Response({'results': data})
        if component_id:
            data = EquipComponent.objects.filter(equip_part=component_id).values('id', 'component_name')
            return Response({'results': data})
        return super(EquipComponentViewSet, self).list(request, *args, **kwargs)

    @action(methods=['post'], detail=False, permission_classes=[], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlsx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        if cur_sheet.ncols != len(self.EXPORT_FIELDS_DICT):
            raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet)
        parts_list = []
        for item in data:
            lst = [i[2] for i in data]
            if lst.count(item[2]) > 1:
                raise ValidationError('导入的部件编码不能重复')
            lst = [i[3] for i in data]
            if lst.count(item[3]) > 1:
                raise ValidationError('导入的部件名称不能重复')
            equip_part = EquipPartNew.objects.filter(part_name=item[0], use_flag=True).first()
            equip_component_type = EquipComponentType.objects.filter(component_type_name=item[1], use_flag=True).first()

            if not equip_part:
                raise ValidationError('部位{}不存在'.format(item[0]))
            if not equip_component_type:
                raise ValidationError('部件分类{}不存在'.format(item[1]))
            obj = EquipComponent.objects.filter(Q(component_code=item[2]) | Q(component_name=item[3])).first()
            if not obj:
                parts_list.append({"equip_part": equip_part.id,
                                   "equip_component_type": equip_component_type.id,
                                   "component_code": item[2],
                                   "component_name": item[3],
                                   "use_flag": 1 if item[5] == 'Y' else 0})
        s = EquipComponentCreateSerializer(data=parts_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            if len(s.validated_data) < 1:
                raise ValidationError('没有可导入的数据')
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response(f'成功导入{len(s.validated_data)}条数据')


@method_decorator([api_recorder], name='dispatch')
class ERPSpareComponentRelationViewSet(ModelViewSet):
    """
    list:
        部件erp备件关系
    create:
        新增部件与备件erp绑定关系
    """
    queryset = ERPSpareComponentRelation.objects.all()
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ERPSpareComponentRelationFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return ERPSpareComponentRelationCreateSerializer
        return ERPSpareComponentRelationListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


@method_decorator([api_recorder], name='dispatch')
class EquipSpareErpViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        备件erp信息
    create:
        新建备件代码定义
    update:
        编辑、停用备件代码定义
    retrieve:
        备件代码定义详情
    """
    queryset = EquipSpareErp.objects.all()
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipSpareErpFilter
    FILE_NAME = '备件代码定义'
    EXPORT_FIELDS_DICT = {
        "备件代码": "spare_code",
        "备件名称": "spare_name",
        "备件唯一id": "unique_id",
        "备件分类": "equip_component_type_name",
        "规格型号": "specification",
        "技术参数": "technical_params",
        "标准单位": "unit",
        "关键部位": "key_parts_flag_name",
        "库存下限": "lower_stock",
        "库存上限": "upper_stock",
        "计划价格": "cost",
        "材质": "texture_material",
        "有效期(天)": "period_validity",
        "供应商名称": "supplier_name",
        "是否启用": "use_flag_name",
        "录入人": "created_username",
        "录入时间": "created_date"
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return EquipSpareErpListSerializer
        return EquipSpareErpCreateSerializer

    def list(self, request, *args, **kwargs):
        all = self.request.query_params.get('all')
        export = self.request.query_params.get('export')
        if export:
            data = self.get_serializer(self.filter_queryset(self.get_queryset()), many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        if all == '0':
            data = self.get_queryset().values('equip_component_type__component_type_name').distinct()
            return Response({'results': data})
        elif all == '1':
            data = EquipComponentType.objects.filter(use_flag=True).values('id', 'component_type_name')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)

    @action(methods=['post'], detail=False, permission_classes=[], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlsx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        if cur_sheet.ncols != len(self.EXPORT_FIELDS_DICT):
            raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet)
        parts_list = []
        for item in data:
            lst = [i[0] for i in data]
            if lst.count(item[0]) > 1:
                raise ValidationError('导入的备件编码不能重复')
            lst = [i[1] for i in data]
            if lst.count(item[1]) > 1:
                raise ValidationError('导入的备件名称不能重复')
            equip_component_type = EquipComponentType.objects.filter(component_type_name=item[3]).first()
            if not equip_component_type:
                raise ValidationError('备件分类{}不存在'.format(item[3]))
            obj = EquipSpareErp.objects.filter(Q(spare_code=item[0]) | Q(spare_name=item[1])).first()
            if not obj:
                parts_list.append({"spare_code": item[0],
                                   "spare_name": item[1],
                                   "unique_id": item[2] if item[2] else None,
                                   "equip_component_type": equip_component_type.id,
                                   "specification": item[4] if item[4] else None,
                                   "technical_params": item[5] if item[5] else None,
                                   "unit": item[6] if item[6] else None,
                                   "key_parts_flag": 1 if item[7] == '是' else 0,
                                   "lower_stock": item[8] if item[8] else None,
                                   "upper_stock": item[9] if item[9] else None,
                                   "cost": item[10] if item[10] else None,
                                   "texture_material": item[11] if item[11] else None,
                                   "period_validity": item[12] if item[12] else None,
                                   "supplier_name": item[13] if item[13] else None,
                                   "use_flag": 1 if item[14] == 'Y' else 0,
                                   "info_source": "ERP"})
        s = EquipSpareErpImportCreateSerializer(data=parts_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            if len(s.validated_data) < 1:
                raise ValidationError('没有可导入的数据')
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response(f'成功导入{len(s.validated_data)}条数据')


@method_decorator([api_recorder], name='dispatch')
class EquipBomViewSet(ModelViewSet):
    """
        list:
            设备bom信息
        create:
            新建节点、粘贴节点
        update:
            更新标准及区域信息
        retrieve:
            节点详情
        """
    queryset = EquipBom.objects.all()
    permission_classes = (IsAuthenticated,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipBomFilter

    # FILE_NAME = '设备BOM'
    # EXPORT_FIELDS_DICT = {
    #     "节点编号": "node_id",
    #     "分厂": "factory_id",
    #     "区域名称": "equip_area_name",
    #     "区域编号": "equip_area_code",
    #     "设备类型": "property_type_node",
    #     "设备机台编号": "equip_no",
    #     "设备机台名称": "equip_name",
    #     "设备机台规格": "equip_type",
    #     "设备机台状态": "equip_status",
    #     "设备部位编号": "part_code",
    #     "设备部位": "part_name",
    #     "设备部件编号": "component_code",
    #     "设备部件": "component_name",
    #     "设备备件规格": "component_type",
    #     "设备备件状态": "part_status",
    #     "备件绑定信息": "component_spart_binfingflag",
    #     "保养标准": "baoyang_standard_name",
    #     "维修标准": "repair_standard_name",
    #     "点检标准": "xunjian_standard_name",
    #     "润滑标准": "runhua_standard_name",
    #     "计量标定标准": "biaoding_standard_name",
    #     "录入人": "created_username",
    #     "录入时间": "created_date"
    # }

    def get_serializer_class(self):
        if self.action == 'update':
            return EquipBomUpdateSerializer
        return EquipBomSerializer

    def list(self, request, *args, **kwargs):
        tree = self.request.query_params.get('tree')
        title = self.request.query_params.get('title')
        export = self.request.query_params.get('export')
        if export:
            data = EquipBomSerializer(self.filter_queryset(self.get_queryset()), many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        if not tree:
            if title:
                data = self.filter_queryset(self.get_queryset()).values('id', 'factory_id')
                return Response({'results': data})
            return super().list(request, *args, **kwargs)
        data = []
        index_tree = {}
        for section in self.get_queryset():
            equip_property_type_id = equip_property_type_name = equip_info_id = equip_info_code = equip_category_id = \
                equip_part_id = equip_part_code = equip_component_id = equip_component_code = ''
            # 设备类型id
            if section.property_type_id:
                equip_property_type_id = section.property_type_id
                equip_property_type_name = section.property_type.global_name
            # 机台id和机型id
            if section.equip_info:
                equip_info_id = section.equip_info_id
                equip_info_code = section.equip_info.equip_no
                equip_category_id = section.equip_info.category_id
            # 部位id
            if section.part:
                equip_part_id = section.part_id
                equip_part_code = section.part.part_code
            # 部件id
            if section.component:
                equip_component_id = section.component_id
                equip_component_code = section.component.component_code
            if section.id not in index_tree:
                index_tree[section.id] = dict({"id": section.id, "factory_id": section.factory_id, "children": [],
                                               "level": section.level, 'location': section.location,
                                               "equip_category_id": equip_category_id,
                                               "equip_component_code": equip_component_code,
                                               "equip_part_code": equip_part_code, "equip_info_name": equip_info_code,
                                               "equip_property_type_name": equip_property_type_name,
                                               "equip_property_type_id": equip_property_type_id,
                                               "equip_part_id": equip_part_id, "equip_info_id": equip_info_id,
                                               "equip_component_id": equip_component_id})
            if not section.parent_flag:  # 根节点
                data.append(index_tree[section.id])  # 浅拷贝
                continue

            if section.parent_flag_id in index_tree:  # 子节点
                if "children" not in index_tree[section.parent_flag_id]:
                    index_tree[section.parent_flag_id]["children"] = []

                index_tree[section.parent_flag_id]["children"].append(index_tree[section.id])
                index_tree[section.parent_flag_id]["children"].sort(key=lambda x: x['location'])

            else:  # 没有节点则加入
                index_tree[section.parent_flag_id] = dict(
                    {"id": section.parent_flag_id, "factory_id": section.parent_flag.factory_id,
                     "level": section.parent_flag.level, "children": [], "equip_category_id": equip_category_id,
                     "equip_part_id": equip_part_id, "equip_component_id": equip_component_id,
                     'location': section.location,
                     'equip_info_id': equip_info_id, 'equip_property_type_id': equip_property_type_id,
                     "equip_property_type_name": equip_property_type_name, "equip_component_name": equip_component_code,
                     "equip_part_name": equip_part_code, "equip_info_name": equip_info_code})
                index_tree[section.parent_flag_id]["children"].append(index_tree[section.id])
                index_tree[section.parent_flag_id]["children"].sort(key=lambda x: x['location'])
        return Response({'results': data})

    @atomic
    def create(self, request, *args, **kwargs):

        def get_location(parent_flag_info):
            # max无法正确比较1-9 和 1-10
            child_data = self.get_queryset().filter(parent_flag=parent_flag_info.id).values_list('location', flat=True).distinct()
            prefix = []
            for i in child_data:
                if not prefix:
                    prefix = i.split('-')
                    continue
                n_num = i.split('-')[-1]
                if int(n_num) > int(prefix[-1]):
                    prefix = prefix[:-1] + [n_num]
            max_location = '-'.join(prefix)
            if max_location:
                if len(max_location) == 1:
                    location = parent_flag_info.location + str(int(max_location.split('-')[-1]) + 1)
                else:
                    location = parent_flag_info.location + '-' + str(int(max_location.split('-')[-1]) + 1)
            else:
                if not parent_flag_info.location:
                    location = '1'
                else:
                    location = f'{parent_flag_info.location}-1'
            return location

        def add_parent(instance, children):
            # 当前节点数据
            for child in children:
                child_current_data = EquipBom.objects.filter(id=child['id']).values().first()
                child_current_data.pop('id')
                child_current_data['parent_flag_id'] = instance.id
                if child_current_data['level'] == 2:
                    child_current_data.update({'property_type_id': child_current_data['property_type_id']})
                elif child_current_data['level'] == 3:
                    equip = Equip.objects.filter(id=child_current_data['equip_info_id']).first()
                    child_current_data.update({'property_type_id': instance.property_type_id,
                                               'equip_info_id': child_current_data['equip_info_id'],
                                               'node_id': equip.equip_no})
                elif child_current_data['level'] == 4:
                    equip_part = EquipPartNew.objects.filter(id=child_current_data['part_id']).first()
                    child_current_data.update({'property_type_id': instance.property_type_id,
                                               'equip_info_id': instance.equip_info_id,
                                               'node_id': f'{instance.node_id}-{equip_part.part_code}'})
                elif child_current_data['level'] == 5:
                    equip_component = EquipComponent.objects.filter(id=child_current_data['component_id']).first()
                    child_current_data.update({'property_type_id': instance.property_type_id,
                                               'equip_info_id': instance.equip_info_id,
                                               'part_id': instance.part_id,
                                               'node_id': f'{instance.node_id}-{equip_component.component_code}'})
                else:
                    pass
                child_current_data['location'] = get_location(instance)
                child_instance = EquipBom.objects.create(**child_current_data)
                e_chidren = child.pop('children', [])
                if e_chidren:
                    add_parent(child_instance, e_chidren)
                else:
                    continue

        data = copy.deepcopy(self.request.data)
        handle = data.pop('handle')
        parent_flag = data.pop('parent_flag', '')
        factory = data.pop('factory_id')
        factory_id = factory.strip()
        current_flag_id = data.pop('current_flag_id', '')
        curr_label_obj_id = data.get('curr_label_obj_id')
        children = data.pop('children', [])
        parent_flag_info = EquipBom.objects.filter(id=parent_flag).first()
        children_of_parent = EquipBom.objects.filter(parent_flag=parent_flag)
        if not factory_id:
            raise ValidationError('输入名称不可全为空格')
        if not handle:  # 新建
            curr_data = {'factory_id': factory_id, 'parent_flag': parent_flag_info.id}
            if parent_flag_info.level == 0:
                if children_of_parent.filter(factory_id=factory_id):
                    raise ValidationError('工厂名称已经存在')
                curr_data.update({'level': 1})
            elif parent_flag_info.level == 1:
                if children_of_parent.filter(property_type=curr_label_obj_id):
                    raise ValidationError('设备类型已经存在')
                curr_data.update({'level': 2, 'property_type': curr_label_obj_id})
            elif parent_flag_info.level == 2:
                if children_of_parent.filter(equip_info=curr_label_obj_id):
                    raise ValidationError('设备已经存在')
                equip = Equip.objects.filter(id=curr_label_obj_id).first()
                curr_data.update({'property_type': parent_flag_info.property_type_id, 'level': 3,
                                  'equip_info': curr_label_obj_id, 'node_id': equip.equip_no})
            elif parent_flag_info.level == 3:
                if children_of_parent.filter(part=curr_label_obj_id):
                    raise ValidationError('设备部位已经存在')
                equip_part = EquipPartNew.objects.filter(id=curr_label_obj_id).first()
                curr_data.update({'property_type': parent_flag_info.property_type_id, 'part': curr_label_obj_id,
                                  'equip_info': parent_flag_info.equip_info_id, 'level': 4,
                                  'node_id': f'{parent_flag_info.node_id}-{equip_part.part_code}'})
            else:
                if children_of_parent.filter(component=curr_label_obj_id):
                    raise ValidationError('设备部件已经存在')
                equip_component = EquipComponent.objects.filter(id=curr_label_obj_id).first()
                curr_data.update({'property_type': parent_flag_info.property_type_id, 'part': parent_flag_info.part_id,
                                  'equip_info': parent_flag_info.equip_info_id, 'component': curr_label_obj_id,
                                  'level': 5,
                                  'node_id': f'{parent_flag_info.node_id}-{equip_component.component_code}'})
            # 节点位置
            curr_data['location'] = get_location(parent_flag_info)
            serializer = self.get_serializer(data=curr_data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        current_data = EquipBom.objects.filter(id=current_flag_id).values().first()
        if not current_data:
            raise ValidationError(f'未找到节点数据, 不可粘贴')
        if current_data['level'] == 1:
            if EquipBom.objects.filter(factory_id=factory_id):
                raise ValidationError('工厂名称已经存在')
        elif current_data['level'] == 2:
            if children_of_parent.filter(property_type=curr_label_obj_id):
                raise ValidationError('设备类型已经存在')
            current_data.update({'property_type_id': curr_label_obj_id})
        elif current_data['level'] == 3:
            if children_of_parent.filter(equip_info=curr_label_obj_id):
                raise ValidationError('设备已经存在')
            equip = Equip.objects.filter(id=curr_label_obj_id).first()
            current_data.update({'equip_info_id': curr_label_obj_id, 'node_id': equip.equip_no})
        elif current_data['level'] == 4:
            if children_of_parent.filter(part=curr_label_obj_id):
                raise ValidationError('设备部位已经存在')
            equip_part = EquipPartNew.objects.filter(id=curr_label_obj_id).first()
            current_data.update({'equip_info_id': parent_flag_info.equip_info_id, 'part_id': curr_label_obj_id,
                                 'node_id': f'{parent_flag_info.node_id}-{equip_part.part_code}'})
        else:
            if children_of_parent.filter(component=curr_label_obj_id):
                raise ValidationError('设备部件已经存在')
            equip_component = EquipComponent.objects.filter(id=curr_label_obj_id).first()
            current_data.update({'equip_info_id': parent_flag_info.equip_info_id, 'part_id': parent_flag_info.part_id,
                                 'component_id': curr_label_obj_id,
                                 'node_id': f'{parent_flag_info.node_id}-{equip_component.component_code}'})
        # 节点位置
        current_data.pop('id')
        current_data['factory_id'] = factory_id
        current_data['location'] = get_location(parent_flag_info)
        current_data['parent_flag_id'] = parent_flag
        instance = EquipBom.objects.create(**current_data)
        if children:
            add_parent(instance, children)
        return Response('添加成功')

    @atomic
    @action(methods=['post'], detail=False, permission_classes=[], url_path='exchange_location',
            url_name='exchange_location')
    def exchange_location(self, request):
        def exchange_children_location(parent_instance):
            children_instance = parent_instance.equipbom_set.all()
            if children_instance:
                for instance in children_instance:
                    instance.location = parent_instance.location + instance.location[-2:]
                    instance.save()
                    exchange_children_location(instance)

        choice_location = self.request.data.get('choice_location')
        other_location = self.request.data.get('other_location')
        choice_instance = self.get_queryset().filter(id=choice_location).first()
        other_instance = self.get_queryset().filter(id=other_location).first()
        # 部件层互换位置
        choice_instance.location, other_instance.location = other_instance.location, choice_instance.location
        choice_instance.save()
        other_instance.save()
        for instance in [choice_instance, other_instance]:
            exchange_children_location(instance)
        return Response('操作成功')


@method_decorator([api_recorder], name="dispatch")
class EquipFaultTypeViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        设备故障分类列表
    create:
        创建设备故障分类
    update:
        修改设备故障分类
    destroy:
        删除设备故障分类
    """
    queryset = EquipFaultType.objects.filter(delete_flag=False).order_by("id")
    serializer_class = EquipFaultTypeSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipFaultTypeFilter


@method_decorator([api_recorder], name="dispatch")
class EquipFaultCodeViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        公共代码列表
    create:
        创建公共代码
    update:
        修改公共代码
    """
    queryset = EquipFault.objects.filter(delete_flag=False, equip_fault_type__use_flag=1).order_by("id")
    serializer_class = EquipFaultCodeSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipFaultCodeFilter


@method_decorator([api_recorder], name="dispatch")
class EquipFaultSignalViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipFaultSignal.objects.order_by('id')
    serializer_class = EquipFaultSignalSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipFaultSignalFilter
    FILE_NAME = '设备故障信号定义'
    EXPORT_FIELDS_DICT = {"信号编号": "signal_code",
                          "信号名称": "signal_name",
                          "机台编号": "equip_no",
                          "机台名称": "equip_name",
                          "设备部位": "equip_part_name",
                          "设备部件": "equip_component_name",
                          "信号变量名": "signal_variable_name",
                          "信号数据类型": "signal_variable_type",
                          "报警下限值": "alarm_signal_minvalue",
                          "报警上限值": "alarm_signal_maxvalue",
                          "报警持续时间（秒）": "alarm_signal_duration",
                          "报警是否停机": "alarm_signal_down_flag_name",
                          "报警停机描述": "alarm_signal_desc",
                          "故障下限值": "fault_signal_minvalue",
                          "故障上限值": "fault_signal_maxvalue",
                          "故障持续时间（秒）": "fault_signal_duration",
                          "故障是否停机": "fault_signal_down_flag_name",
                          "故障停机描述": "fault_signal_desc",
                          "是否启用": "use_flag_name",
                          }

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'signal_name', 'signal_code')
            return Response({'results': data})
        if self.request.query_params.get('export'):
            data = self.get_serializer(queryset, many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        else:
            return super().list(request, *args, **kwargs)

    @action(methods=['post'], detail=False, permission_classes=[], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlsx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        if cur_sheet.ncols != len(self.EXPORT_FIELDS_DICT):
            raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet)
        signal_list = []
        for item in data:
            lst = [i[0] for i in data]
            if lst.count(item[0]) > 1:
                raise ValidationError('导入的信号编号不能重复')
            lst = [i[1] for i in data]
            if lst.count(item[1]) > 1:
                raise ValidationError('导入的信号名称不能重复')
            equip = Equip.objects.filter(equip_no=item[2]).first()
            equip_part = EquipPartNew.objects.filter(part_name=item[4]).first()
            equip_component = EquipComponent.objects.filter(component_name=item[5]).first()
            if not equip:
                raise ValidationError('机台编号{}不存在'.format(item[2]))
            if not equip_component:
                equip_component = None
            if not equip_part:
                equip_part = None
            if not EquipFaultSignal.objects.filter(Q(signal_code=item[0]) | Q(signal_name=item[1])).exists():
                signal_list.append({"signal_code": item[0],
                                    "signal_name": item[1],
                                    "signal_variable_name": str(item[6]) if item[6] else None,
                                    "signal_variable_type": item[7] if item[7] else None,
                                    "alarm_signal_minvalue": item[8] if item[8] else None,
                                    "alarm_signal_maxvalue": item[9] if item[9] else None,
                                    "alarm_signal_duration": item[10] if item[10] else None,
                                    "alarm_signal_down_flag": True if item[11] == 'Y' else False,
                                    "alarm_signal_desc": item[12] if item[12] else None,
                                    "fault_signal_minvalue": item[13] if item[13] else None,
                                    "fault_signal_maxvalue": item[14] if item[14] else None,
                                    "fault_signal_duration": item[15] if item[15] else None,
                                    "fault_signal_down_flag": True if item[16] == 'Y' else False,
                                    "fault_signal_desc": item[17] if item[17] else None,
                                    "equip": equip.id,
                                    "equip_part": equip_part.id if equip_part else None,
                                    "equip_component": equip_component.id if equip_component else None,
                                    })
        s = EquipFaultSignalSerializer(data=signal_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            if len(s.validated_data) < 1:
                raise ValidationError('没有可导入的数据')
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response(f'成功导入{len(s.validated_data)}条数据')

    @action(methods=['get'], detail=False, permission_classes=[], url_path='get_name', url_name='get_name')
    def get_name(self, request):
        try:
            dic = self.queryset.aggregate(Max('signal_code'))
            res = dic.get('signal_code__max')
            if res:
                results = res[0:2] + str('%04d' % (int(res[2:]) + 1))
                return Response({'results': results})
            return Response({'results': 'IO0001'})
        except:
            return Response({'results': 'IO000X'})


@method_decorator([api_recorder], name="dispatch")
class EquipMachineHaltTypeViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipMachineHaltType.objects.filter(delete_flag=False).order_by("id")
    serializer_class = EquipMachineHaltTypeSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipMachineHaltTypeFilter
    pagination_class = None


@method_decorator([api_recorder], name="dispatch")  # 本来是删除，现在改为是启用就改为禁用 是禁用就改为启用
class EquipMachineHaltReasonViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipMachineHaltReason.objects.filter(equip_machine_halt_type__use_flag=1).order_by("id")
    serializer_class = EquipMachineHaltReasonSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipMachineHaltReasonFilter
    pagination_class = None


@method_decorator([api_recorder], name="dispatch")
class EquipOrderAssignRuleViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipOrderAssignRule.objects.filter(delete_flag=False).order_by("id")
    serializer_class = EquipOrderAssignRuleSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipOrderAssignRuleFilter
    FILE_NAME = '工单指派规则'
    EXPORT_FIELDS_DICT = {"规则编号": "rule_code",
                          "规则名称": "rule_name",
                          "作业类型": "work_type",
                          "设备类型": "equip_type_name",
                          "设备条件": "equip_condition",
                          "重要程度": "important_level",
                          "接单间隔时间（分钟）": "receive_interval",
                          "接单重复提示次数": "receive_warning_times",
                          "维修开始时间间隔（分钟）": "start_interval",
                          "开始重复提示次数": "start_warning_times",
                          "验收间隔时间（分钟）": "accept_interval",
                          "验收重复提示次数": "accept_warning_times",
                          "是否启用": "use_flag_name",
                          "录入人": "created_username",
                          "录入时间": "created_date",
                          }

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('export'):
            data = self.get_serializer(queryset, many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        else:
            return super().list(request, *args, **kwargs)

    @action(methods=['post'], detail=False, permission_classes=[], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlsx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        if cur_sheet.ncols != len(self.EXPORT_FIELDS_DICT):
            raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet)
        signal_list = []
        for item in data:
            lst = [i[0] for i in data]
            if lst.count(item[0]) > 1:
                raise ValidationError('导入的类型编码不能重复')
            lst = [i[1] for i in data]
            if lst.count(item[1]) > 1:
                raise ValidationError('导入的类型名称不能重复')
            equip_type = GlobalCode.objects.filter(global_name=item[3]).first()
            if not equip_type:
                raise ValidationError('设备类型{}不存在'.format(item[3]))
            if not EquipOrderAssignRule.objects.filter(Q(rule_code=item[0]) | Q(rule_name=item[1])).exists():
                signal_list.append({"rule_code": item[0],
                                    "rule_name": item[1],
                                    "work_type": item[2],
                                    "equip_type": equip_type.id,
                                    "equip_condition": item[4],
                                    "important_level": item[5],
                                    "receive_interval": item[6] if item[6] else None,
                                    "receive_warning_times": item[7] if item[7] else None,
                                    "start_interval": item[8] if item[8] else None,
                                    "start_warning_times": item[9] if item[9] else None,
                                    "accept_interval": item[10] if item[10] else None,
                                    "accept_warning_times": item[11] if item[11] else None,
                                    })
        s = EquipOrderAssignRuleSerializer(data=signal_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            if len(s.validated_data) < 1:
                raise ValidationError('没有可导入的数据')
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response(f'成功导入{len(s.validated_data)}条数据')

    @action(methods=['get'], detail=False, permission_classes=[], url_path='get_name', url_name='get_name')
    def get_name(self, request):
        try:
            dic = self.queryset.aggregate(Max('rule_code'))
            res = dic.get('rule_code__max')
            if res:
                results = res[0:4] + str('%04d' % (int(res[4:]) + 1))
                return Response({'results': results})
            return Response({'results': 'ZPGZ0001'})
        except:
            return Response({'results': 'ZPGZ000X'})


@method_decorator([api_recorder], name="dispatch")
class EquipTargetMTBFMTTRSettingView(APIView):

    def get(self, request):
        return Response(EquipTargetMTBFMTTRSetting.objects.order_by('equip__equip_no').values(
            'id', 'equip', 'equip__equip_no', 'equip__equip_name', 'target_mtb', 'target_mttr'))

    def post(self, request):
        data = request.data
        if not isinstance(data, list):
            raise ValidationError('data error!')
        try:
            for item in data:
                EquipTargetMTBFMTTRSetting.objects.filter(id=item['id']).update(**{'target_mtb': item['target_mtb'],
                                                                                   'target_mttr': item['target_mttr']})
        except Exception:
            raise ValidationError('数据错误')
        return Response('修改成功')


@method_decorator([api_recorder], name="dispatch")
class EquipMaintenanceAreaSettingViewSet(ModelViewSet):
    queryset = EquipMaintenanceAreaSetting.objects.filter(delete_flag=False).order_by("id")
    serializer_class = EquipMaintenanceAreaSettingSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('maintenance_user_id',)


@method_decorator([api_recorder], name="dispatch")
class EquipJobItemStandardViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list: 查询设备作业项目标准定义
    retrieve: 设备作业项目标准定义详情
    create: 新建设备作业项目标准定义
    delete: 停用设备作业项目标准定义
    """
    queryset = EquipJobItemStandard.objects.filter(delete_flag=False).order_by("-created_date")
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipJobItemStandardFilter
    FILE_NAME = '设备作业项目标准定义'
    EXPORT_FIELDS_DICT = {
        "作业类型": "work_type",
        "标准编号": "standard_code",
        "作业项目标准名称": "standard_name",
        "作业详细内容": "work_details_column",
        "判断标准": "check_standard_desc_column",
        "判断类型": "check_standard_type_column",
        "录入人": "created_username",
        "录入时间": "created_date",
    }

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return EquipJobItemStandardListSerializer
        elif self.action == 'update':
            return EquipJobItemStandardUpdateSerializer
        return EquipJobItemStandardCreateSerializer

    def list(self, request, *args, **kwargs):
        export = self.request.query_params.get('export')
        if export:
            data = self.get_serializer(self.filter_queryset(self.get_queryset()), many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        return super().list(request, *args, **kwargs)

    @action(methods=['post'], detail=False, permission_classes=[], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlsx(self, request):
        def handle_data(work_details_column, check_standard_desc_column, check_standard_type_column):
            work_details = []
            try:
                standard = {i.split('、')[0]: i.split('、')[1] for i in check_standard_desc_column.split('；')[:-1]}
                type = {i.split('、')[0]: i.split('、')[1] for i in check_standard_type_column.split('；')[:-1]}
                for i in work_details_column.split('；')[:-1]:
                    seq, content = i.split('、')
                    data = {"sequence": seq, "content": content, "check_standard_desc": standard.get(seq),
                            "check_standard_type": type.get(seq)}
                    work_details.append(data)
            except:
                raise ValidationError('导入的数据格式有误')
            return work_details

        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        if cur_sheet.ncols != len(self.EXPORT_FIELDS_DICT):
            raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet)
        parts_list = []
        for item in data:
            if not item[3]:
                raise ValidationError('作业详情内容不可为空')
            if not item[4]:
                raise ValidationError('判断标准不可为空')
            if not item[5]:
                raise ValidationError('类型不可为空')
            lst = [i[1] for i in data]
            if lst.count(item[1]) > 1:
                raise ValidationError('导入的标准编码不能重复')
            lst = [i[2] for i in data]
            if lst.count(item[2]) > 1:
                raise ValidationError('导入的标准名称不能重复')
            obj = EquipJobItemStandard.objects.filter(Q(standard_code=item[1]) | Q(standard_name=item[2])).first()
            if not obj:
                parts_list.append({
                    "work_type": item[0],
                    "standard_code": item[1],
                    "standard_name": item[2],
                    "work_details": handle_data(item[3], item[4], item[5]),
                })
        s = EquipJobItemStandardCreateSerializer(data=parts_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            if len(s.validated_data) < 1:
                raise ValidationError('没有可导入的数据')
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response(f'成功导入{len(s.validated_data)}条数据')


@method_decorator([api_recorder], name="dispatch")
class EquipMaintenanceStandardViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipMaintenanceStandard.objects.order_by('-created_date')
    serializer_class = EquipMaintenanceStandardSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipMaintenanceStandardFilter
    FILE_NAME = '设备维护作业标准定义'
    EXPORT_FIELDS_DICT = {
        "作业类型": "work_type",
        "标准编号": "standard_code",
        "标准名称": "standard_name",
        "类别": "type",
        "机台": "equip",
        "部位名称": "equip_part_name",
        "部件名称": "equip_component_name",
        "设备条件": "equip_condition",
        "重要程度": "important_level",
        "作业项目": "equip_job_item_standard_name",
        "起始时间": "start_time",
        "维护周期": "maintenance_cycle",
        "周期单位": "cycle_unit",
        "周期数": "cycle_num",
        "所需人数": "cycle_person_num",
        "作业时间": "operation_time",
        "作业时间单位": "operation_time_unit",
        # "所需物料名称": "spare_list_str",
        "录入人": "created_username",
        "录入时间": "created_date",
    }

    def export(self, export_filed_dict, data, file_name):
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = file_name
        response['Content-Disposition'] = u'attachment;filename= ' + filename.encode('gbk').decode(
            'ISO-8859-1') + '.xls'
        # 创建一个文件对象
        wb = xlwt.Workbook(encoding='utf8')
        # 创建一个sheet对象
        sheet = wb.add_sheet(file_name, cell_overwrite_ok=True)
        style = xlwt.XFStyle()
        style.alignment.wrap = 1

        # 写入文件标题
        for col_num in range(len(export_filed_dict)):
            sheet.write(0, col_num, list(export_filed_dict.keys())[col_num])
            # 写入数据
            data_row = 1
            for i in data:
                if not i.get('equip_component_name'):
                    i.update({'equip_component_name': None})
                sheet.write(data_row, col_num, i[list(export_filed_dict.values())[col_num]])
                data_row += 1

        # 写出到IO
        output = BytesIO()
        wb.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response

    def create(self, request, *args, **kwargs):
        spare_list = request.data.get('spare_list', None)
        work_list = request.data.get('work_list', None)
        serializer = EquipMaintenanceStandardCreateSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            obj = EquipMaintenanceStandard.objects.create(**serializer.validated_data, created_user=self.request.user)
            if spare_list:
                for item in spare_list:
                    EquipMaintenanceStandardMaterials.objects.create(equip_maintenance_standard=obj,
                                                                     equip_spare_erp_id=item['equip_spare_erp__id'],
                                                                     quantity=item['quantity'])
            if work_list:  # 新建巡检标准时选择作业项目
                for item in work_list:
                    standard_code = obj.standard_code  # 巡检标准编号
                    area_code = EquipAreaDefine.objects.filter(id=item['equip_area_define__id']).first().area_code
                    equip_component = item.get('equip_component__id')
                    EquipMaintenanceStandardWork.objects.create(equip_maintenance_standard=obj,
                                                                equip_part_id=item['equip_part__id'],
                                                                equip_area_define_id=item['equip_area_define__id'],
                                                                equip_job_item_standard_id=item['equip_job_item_standard__id'],
                                                                equip_component_id=equip_component,
                                                                lot_no=f'{standard_code}{area_code}')
            return Response('新建成功')

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = EquipMaintenanceStandardCreateSerializer(instance, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        id = int(kwargs.get('pk'))
        spare_list = request.data.get('spare_list', None)
        work_list = request.data.get('work_list', None)
        if spare_list:
            EquipMaintenanceStandardMaterials.objects.filter(equip_maintenance_standard_id=id).delete()
            for item in spare_list:
                EquipMaintenanceStandardMaterials.objects.create(equip_maintenance_standard_id=id,
                                                                 equip_spare_erp_id=item['equip_spare_erp__id'],
                                                                 quantity=item['quantity'])
        if work_list:
            EquipMaintenanceStandardWork.objects.filter(equip_maintenance_standard_id=id).delete()
            for item in work_list:
                standard_code = EquipMaintenanceStandard.objects.filter(id=id).first().standard_code
                area_code = EquipAreaDefine.objects.filter(id=item['equip_area_define__id']).first().area_code
                equip_component = item.get('equip_component__id')
                EquipMaintenanceStandardWork.objects.create(equip_maintenance_standard_id=id,
                                                            equip_part_id=item['equip_part__id'],
                                                            equip_area_define_id=item['equip_area_define__id'],
                                                            equip_job_item_standard_id=item['equip_job_item_standard__id'],
                                                            equip_component_id=equip_component,
                                                            lot_no=f'{standard_code}{area_code}')

        else:
            EquipMaintenanceStandardMaterials.objects.filter(equip_maintenance_standard_id=id).delete()

        self.perform_update(serializer)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).distinct()
        if self.request.query_params.get('all'):
            data = self.get_serializer(queryset, many=True).data
            return Response(data)
        page = self.paginate_queryset(queryset)
        if self.request.query_params.get('export'):
            data = self.get_serializer(queryset, many=True).data
            return self.export(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['post'], detail=False, permission_classes=[], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlsx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        if cur_sheet.ncols != len(self.EXPORT_FIELDS_DICT):
            raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet)
        signal_list = []
        for item in data:
            equip_part = EquipPartNew.objects.filter(part_name=item[5]).first()
            equip_component = EquipComponent.objects.filter(component_name=item[6]).first()
            equip_job_item_standard = EquipJobItemStandard.objects.filter(standard_name=item[9]).first()
            if item[0] != '巡检' and not equip_part:
                raise ValidationError(f'部位名称{item[5]}不存在')
            if item[0] != '巡检' and not equip_job_item_standard:
                raise ValidationError(f'作业项目{item[9]}不存在')
            try:
                if item[10]:
                    start_time = dt.date(*map(int, item[10].split('-'))) if isinstance(item[10], str) else datetime.date(
                        xlrd.xldate.xldate_as_datetime(item[10], 0))
            except:
                raise ValidationError('导入的开始时间格式有误')

            lst = [i[1] for i in data]
            if lst.count(item[1]) > 1:
                raise ValidationError('导入的物料编码不能重复')
            lst = [i[2] for i in data]
            if lst.count(item[2]) > 1:
                raise ValidationError('导入的物料名称不能重复')

            if not EquipMaintenanceStandard.objects.filter(
                    Q(Q(standard_code=item[1]) | Q(standard_name=item[2]))).exists():
                signal_list.append({"work_type": item[0],
                                    "standard_code": item[1],
                                    "standard_name": item[2],
                                    "equip_no": item[4],
                                    "equip_part": equip_part.id if equip_part else None,
                                    "equip_component": equip_component.id if equip_component else None,
                                    "equip_condition": item[7],
                                    "important_level": item[8],
                                    "equip_job_item_standard": equip_job_item_standard.id if equip_job_item_standard else None,
                                    "start_time": start_time if item[10] else None,
                                    "maintenance_cycle": item[11] if item[11] else None,
                                    "cycle_unit": item[12] if item[12] else None,
                                    "cycle_num": item[13] if item[13] else None,
                                    "cycle_person_num": item[14] if item[13] else None,
                                    "operation_time": item[15] if item[15] else None,
                                    "operation_time_unit": item[16] if item[16] else None,
                                    "remind_flag1": True,
                                    "remind_flag2": True,
                                    "remind_flag3": False,
                                    "spares": item[17] if item[17] else 'no',  # '清洁剂'
                                    })

        serializer = EquipMaintenanceStandardImportSerializer(data=signal_list, many=True, context={'request': request})
        if serializer.is_valid(raise_exception=False):
            if len(serializer.validated_data) < 1:
                raise ValidationError('没有可导入的数据')
            for data in serializer.validated_data:
                spares = dict(data).pop('spares')
                data.pop('spares')
                spare_list = spares.split(',') or spares.split(' ') or spares.split('，')
                spare_obj_list = []
                for spare in spare_list:
                    if spare != 'no':
                        spare_obj = EquipSpareErp.objects.filter(spare_name=spare).first()
                        spare_obj_list.append(spare_obj)
                        if not spare_obj:
                            raise ValidationError(f'所选物料名称{spare}不存在')
                obj = EquipMaintenanceStandard.objects.create(**data)
                for spare_obj in spare_obj_list:
                    EquipMaintenanceStandardMaterials.objects.create(equip_maintenance_standard=obj,
                                                                     equip_spare_erp=spare_obj,
                                                                     quantity=1)  # 默认1
        else:
            raise ValidationError('导入的数据类型有误')
        return Response(f'成功导入{len(serializer.validated_data)}条数据')

    @action(methods=['get'], detail=False, permission_classes=[], url_path='get_name', url_name='get_name')
    def get_name(self, request):
        rule_code = self.request.query_params.get('rule_code')
        try:
            if not rule_code:
                raise ValidationError('传入参数有误')
            dic = self.queryset.filter(work_type=rule_code).aggregate(Max('standard_code'))
            res = dic.get('standard_code__max')
            if res:
                results = res[0:4] + str('%04d' % (int(res[4:]) + 1))
                return Response({'results': results})
        except:
            pass
        kwargs = {'巡检': 'XJBZ0001',
                  '保养': 'BYBZ0001',
                  '标定': 'BDBZ0001',
                  '润滑': 'RHBZ0001'}
        return Response({'results': kwargs[rule_code]})


@method_decorator([api_recorder], name="dispatch")
class EquipRepairStandardViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipRepairStandard.objects.order_by('-created_date')
    serializer_class = EquipRepairStandardSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipRepairStandardFilter
    FILE_NAME = '设备维修作业标准定义'
    EXPORT_FIELDS_DICT = {
        "标准编号": "standard_code",
        "标准名称": "standard_name",
        "机台": "equip",
        "部位名称": "equip_part_name",
        "部件名称": "equip_component_name",
        "设备条件": "equip_condition",
        "重要程度": "important_level",
        "故障分类": "equip_fault_name",
        "作业项目": "equip_job_item_standard_name",
        "所需人数": "cycle_person_num",
        "作业时间": "operation_time",
        "作业时间单位": "operation_time_unit",
        "录入人": "created_username",
        "录入时间": "created_date",
    }

    def export(self, export_filed_dict, data, file_name):
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = file_name
        response['Content-Disposition'] = u'attachment;filename= ' + filename.encode('gbk').decode(
            'ISO-8859-1') + '.xls'
        # 创建一个文件对象
        wb = xlwt.Workbook(encoding='utf8')
        # 创建一个sheet对象
        sheet = wb.add_sheet(file_name, cell_overwrite_ok=True)
        style = xlwt.XFStyle()
        style.alignment.wrap = 1

        # 写入文件标题
        for col_num in range(len(export_filed_dict)):
            sheet.write(0, col_num, list(export_filed_dict.keys())[col_num])
            # 写入数据
            data_row = 1
            for i in data:
                if not i.get('equip_component_name'):
                    i.update({'equip_component_name': None})
                sheet.write(data_row, col_num, i[list(export_filed_dict.values())[col_num]])
                data_row += 1

        # 写出到IO
        output = BytesIO()
        wb.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response

    def create(self, request, *args, **kwargs):
        spare_list = request.data.get('spare_list', None)
        serializer = EquipRepairStandardCreateSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            obj = EquipRepairStandard.objects.create(**serializer.validated_data, created_user=self.request.user)
            if spare_list:
                for item in spare_list:
                    EquipRepairStandardMaterials.objects.create(equip_repair_standard=obj,
                                                                equip_spare_erp_id=item['equip_spare_erp__id'],
                                                                quantity=item['quantity'])
            return Response('新建成功')

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = EquipRepairStandardCreateSerializer(instance, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        id = int(kwargs.get('pk'))
        spare_list = request.data.get('spare_list', None)
        if spare_list:
            EquipRepairStandardMaterials.objects.filter(equip_repair_standard_id=id).delete()
            for item in spare_list:
                EquipRepairStandardMaterials.objects.create(equip_repair_standard_id=id,
                                                            equip_spare_erp_id=item['equip_spare_erp__id'],
                                                            quantity=item['quantity'])
        else:
            EquipRepairStandardMaterials.objects.filter(equip_repair_standard_id=id).delete()
        self.perform_update(serializer)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).distinct()
        page = self.paginate_queryset(queryset)
        if self.request.query_params.get('all'):
            data = self.get_serializer(queryset, many=True).data
            return Response(data)
        if self.request.query_params.get('export'):
            data = self.get_serializer(queryset, many=True).data
            return self.export(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['post'], detail=False, permission_classes=[], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlsx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        if cur_sheet.ncols != len(self.EXPORT_FIELDS_DICT):
            raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet)
        signal_list = []
        for item in data:
            equip_part = EquipPartNew.objects.filter(part_name=item[3]).first()
            equip_component = EquipComponent.objects.filter(component_name=item[4]).first()
            equip_fault = EquipFault.objects.filter(fault_name=item[7]).first()
            equip_job_item_standard = EquipJobItemStandard.objects.filter(standard_name=item[8]).first()

            if not equip_part:
                raise ValidationError(f'部位名称{item[3]}不存在')
            if not equip_fault:
                raise ValidationError(f'故障分类{item[7]}不存在')
            if not equip_job_item_standard:
                raise ValidationError(f'作业项目{item[8]}不存在')

            lst = [i[0] for i in data]
            if lst.count(item[0]) > 1:
                raise ValidationError('导入的物料编码不能重复')
            lst = [i[1] for i in data]
            if lst.count(item[1]) > 1:
                raise ValidationError('导入的物料名称不能重复')

            if not EquipRepairStandard.objects.filter(Q(Q(standard_code=item[0]) | Q(standard_name=item[1]))).exists():
                signal_list.append({"standard_code": item[0],
                                    "standard_name": item[1],
                                    "equip_no": item[2],
                                    "equip_part": equip_part.id,
                                    "equip_component": equip_component.id if equip_component else None,
                                    "equip_condition": item[5],
                                    "important_level": item[6],
                                    "equip_fault": equip_fault.id,
                                    "equip_job_item_standard": equip_job_item_standard.id,
                                    "cycle_person_num": item[9] if item[9] else None,
                                    "operation_time": item[10] if item[10] else None,
                                    "operation_time_unit": item[11] if item[11] else None,
                                    "remind_flag1": True,
                                    "remind_flag2": True,
                                    "remind_flag3": False,
                                    })

        serializer = EquipRepairStandardImportSerializer(data=signal_list, many=True, context={'request': request})
        if serializer.is_valid(raise_exception=False):
            if len(serializer.validated_data) < 1:
                raise ValidationError('没有可导入的数据')
            for data in serializer.validated_data:
                EquipRepairStandard.objects.create(**data)
        else:
            raise ValidationError('导入的数据类型有误')
        return Response(f'成功导入{len(serializer.validated_data)}条数据')

    @action(methods=['get'], detail=False, permission_classes=[], url_path='get_name', url_name='get_name')
    def get_name(self, request):
        try:
            dic = self.queryset.aggregate(Max('standard_code'))
            res = dic.get('standard_code__max')
            if res:
                results = res[0:4] + str('%04d' % (int(res[4:]) + 1))
                return Response({'results': results})
            return Response({'results': 'WXBZ0001'})
        except:
            return Response({'results': 'WXBZ000X'})


@method_decorator([api_recorder], name='dispatch')
class GetDefaultCodeView(APIView):
    permission_classes = (IsAuthenticated, )

    def get(self, request):
        work_type = self.request.query_params.get('work_type')
        if work_type == '部件':
            max_standard_code = \
                EquipComponent.objects.filter(component_code__startswith='BJ').aggregate(
                    max_code=Max('component_code'))[
                    'max_code']
            next_standard_code = max_standard_code[:2] + '%04d' % (
                    int(max_standard_code[2:]) + 1) if max_standard_code else 'BJ0001'
        elif work_type in ['巡检', '维修', '保养', '润滑', '标定']:
            map_dict = {'巡检': 'XJ', '维修': 'WX', '保养': 'BY', '润滑': 'RH', '标定': 'BD'}
            prefix = map_dict.get(work_type)
            max_standard_code = \
                EquipJobItemStandard.objects.filter(work_type=work_type, standard_code__startswith=prefix).aggregate(
                    max_code=Max('standard_code'))['max_code']
            code_num = '%04d' % (int(max_standard_code[2:]) + 1) if max_standard_code else '0001'
            next_standard_code = prefix + code_num
        elif work_type == '故障':
            equip_fault_type = self.request.query_params.get('equip_fault_type')
            max_standard_code = EquipFault.objects.filter(equip_fault_type__fault_type_code=equip_fault_type,
                                                          fault_code__startswith=equip_fault_type).aggregate(
                max_code=Max('fault_code'))['max_code']
            code_num = '%04d' % (int(max_standard_code[len(equip_fault_type):]) + 1) if max_standard_code else '0001'
            next_standard_code = equip_fault_type + code_num
        elif work_type == '停机':
            equip_machine_halt_type = self.request.query_params.get('equip_machine_halt_type')
            max_standard_code = EquipMachineHaltReason.objects.filter(
                equip_machine_halt_type__machine_halt_type_code=equip_machine_halt_type,
                machine_halt_reason_code__startswith=equip_machine_halt_type).aggregate(
                max_code=Max('machine_halt_reason_code'))['max_code']
            code_num = '%04d' % (
                    int(max_standard_code[len(equip_machine_halt_type):]) + 1) if max_standard_code else '0001'
            next_standard_code = equip_machine_halt_type + code_num
        elif work_type == '信号':
            max_standard_code = \
                EquipFaultSignal.objects.filter(signal_code__startswith='IO').aggregate(max_code=Max('signal_code'))[
                    'max_code']
            code_num = '%04d' % (int(max_standard_code[2:]) + 1) if max_standard_code else '0001'
            next_standard_code = 'IO' + code_num
        elif work_type == '部位':
            max_standard_code = \
                EquipPartNew.objects.filter(part_code__startswith='BW').aggregate(max_code=Max('part_code'))['max_code']
            next_standard_code = max_standard_code[:2] + '%04d' % (
                    int(max_standard_code[2:]) + 1) if max_standard_code else 'BW0001'
        elif work_type in ['区分', '项目', '处理']:
            map_dict = {'区分': 'GCQF', '项目': 'GCXM', '处理': 'CLKW'}
            prefix = map_dict.get(work_type)
            model_name = ToleranceDistinguish if work_type == '区分' else (
                ToleranceProject if work_type == '项目' else ToleranceHandle)
            max_standard_code = model_name.objects.all().aggregate(max_code=Max('keyword_code'))['max_code']
            next_standard_code = prefix + ('%04d' % (int(max_standard_code[4:]) + 1) if max_standard_code else '0001')
        elif work_type == '公差规则':
            max_standard_code = ToleranceRule.objects.all().aggregate(max_code=Max('rule_code'))['max_code']
            next_standard_code = 'GCBZ' + ('%04d' % (int(max_standard_code[4:]) + 1) if max_standard_code else '0001')
        else:
            raise ValidationError('该类型默认编码暂未提供')
        return Response(next_standard_code)


@method_decorator([api_recorder], name='dispatch')
class EquipWarehouseAreaViewSet(ModelViewSet):
    queryset = EquipWarehouseArea.objects.filter(delete_flag=False)
    serializer_class = EquipWarehouseAreaSerializer
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        equip_spare = self.request.query_params.get('equip_spare')  # 备件入库时库区选择
        if self.request.query_params.get('all'):
            data = self.get_serializer(self.queryset, many=True).data
            return Response(data)
        if equip_spare:
            obj = EquipSpareErp.objects.filter(id=equip_spare).first()
            results = self.queryset.filter(Q(warehouse_area__equip_component_type=obj.equip_component_type) | Q(warehouse_area__isnull=True)).values('id', 'area_name')
            first = EquipWarehouseInventory.objects.filter(equip_spare_id=equip_spare, quantity__gt=0).first()
            # 该备件可以存放的库区和库位
            if first:
                return Response({"success": True, "message": None, "data": {'results': results, 'first': {'area_id': first.equip_warehouse_area.id,
                                                         'area_name': first.equip_warehouse_area.area_name,
                                                         'location_id': first.equip_warehouse_location.id,
                                                         'location_name': first.equip_warehouse_location.location_name}}})
            return Response({"success": True, "message": None, "data": {'results': results, 'first': {
                'area_id': results[0]['id'] if results else None,
                'area_name': results[0]['area_name'] if results else None,
            }}})
        return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if EquipWarehouseInventory.objects.filter(equip_warehouse_area=instance, quantity__gt=0).exists():
            raise ValidationError('库区正在使用')
        instance.delete_flag = True
        instance.save()
        EquipWarehouseLocation.objects.filter(equip_warehouse_area=instance).update(delete_flag=True)
        return Response('删除成功')


@method_decorator([api_recorder], name='dispatch')
class EquipWarehouseLocationViewSet(ModelViewSet):
    queryset = EquipWarehouseLocation.objects.filter(delete_flag=False).order_by('location_name')
    serializer_class = EquipWarehouseLocationSerializer
    permission_classes = (IsAuthenticated,)
    filter_fields = ('equip_warehouse_area_id',)

    def list(self, request, *args, **kwargs):
        area_id = self.request.query_params.get('equip_warehouse_area_id')
        spare_code = self.request.query_params.get('spare_code')
        if self.request.query_params.get('all'):
            queryset = self.filter_queryset(self.queryset)
            if spare_code:
                already_locations = set(EquipWarehouseInventory.objects.filter(delete_flag=False, quantity__gt=0,
                                                                               equip_spare__spare_code=spare_code,
                                                                               equip_warehouse_area__id=area_id)
                                        .values_list('equip_warehouse_location__id', flat=True))
                queryset = queryset.filter(id__in=already_locations)
            data = self.get_serializer(queryset, many=True).data
            return Response(data)
        return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if EquipWarehouseInventory.objects.filter(equip_warehouse_location=instance, quantity__gt=0).exists():
            raise ValidationError('库位正在使用')
        instance.delete_flag = True
        instance.save()
        return Response('删除成功')


@method_decorator([api_recorder], name='dispatch')
class EquipWarehouseOrderViewSet(ModelViewSet):
    queryset = EquipWarehouseOrder.objects.filter(delete_flag=False).order_by('-id')
    serializer_class = EquipWarehouseOrderSerializer
    permission_classes = (IsAuthenticated,)
    filter_class = EquipWarehouseOrderFilter

    def get_serializer_class(self):
        if self.action == 'list':
            return EquipWarehouseOrderListSerializer
        else:
            return EquipWarehouseOrderSerializer

    def list(self, request, *args, **kwargs):
        state = self.request.query_params.get('status')
        order = self.request.query_params.get('order', None)
        page = self.request.query_params.get('page', 1)
        page_size = self.request.query_params.get('page_size', 10)
        spare_name = self.request.query_params.get('spare_name')
        spare_code = self.request.query_params.get('spare_code')
        work_order_no = self.request.query_params.get('work_order_no')
        unique_id = self.request.query_params.get('unique_id')
        filter_kwargs = {}
        if spare_name:
            filter_kwargs['spare_name'] = spare_name
        if spare_code:
            filter_kwargs['spare_code'] = spare_code
        if unique_id:
            filter_kwargs['unique_id'] = unique_id
        if work_order_no:
            data = EquipApplyOrder.objects.exclude(status='已关闭').values('work_order_no',
                                                                        'created_date', 'plan_name')
            [i.update(created_date=i['created_date'].strftime('%Y-%m-%d %H:%M:%S')) for i in data]
            return Response(data)
        if state == '入库':
            data = EquipSpareErp.objects.filter(use_flag=True, **filter_kwargs
                                                ).values('id', 'spare_code', 'unique_id', 'spare_name',
                                                         'equip_component_type__component_type_name',
                                                         'specification', 'technical_params', 'unit')
            for i in data:
                i['spare__code'] = i['spare_code']
                i['component_type_name'] = i['equip_component_type__component_type_name']
            st = (int(page) - 1) * int(page_size)
            et = int(page) * int(page_size)
            count = len(data)
            return Response({'results': data[st:et], 'count': count})
        else:
            if order == 'in':
                queryset = self.filter_queryset(self.get_queryset().filter(status__in=[1, 2, 3, 7]))
            elif order == 'out':
                queryset = self.filter_queryset(self.get_queryset().filter(status__in=[4, 5, 6]))
            else:
                queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status in [1, 4, 7]:
            self.perform_destroy(instance)
            return Response({"success": True, "message": '删除成功', "data": None})
        raise ValidationError('单据入库中或已入库不能删除')

    @action(methods=['post'], detail=False, url_path='close-order', url_name='close-order', permission_classes=(IsAuthenticated, ))
    def close_order(self, request):
        try:
            order_id = int(self.request.data.get('id'))
            instance = EquipWarehouseOrder.objects.get(id=order_id)
        except Exception:
            raise ValidationError('object does not exist!')
        instance.status = 7
        instance.last_updated_user = self.request.user
        instance.save()
        instance.order_detail.filter().update(status=7)
        return Response('OK')

    @action(methods=['get'], detail=False, url_path='get_order_id', url_name='get_order_id')
    def get_order_id(self, request):
        state = request.query_params.get('status', '入库')
        if state == '入库':
            res = EquipWarehouseOrder.objects.filter(created_date__gt=dt.date.today(), status__in=[1, 2, 3, 7]).values(
                'order_id').last()
            if res:
                return Response(res['order_id'][:10] + str('%04d' % (int(res['order_id'][11:]) + 1)))
            else:
                return Response('RK' + str(dt.date.today().strftime('%Y%m%d')) + '0001')
        if state == '出库':
            res = EquipWarehouseOrder.objects.filter(created_date__gt=dt.date.today(), status__in=[4, 5, 6]).values(
                'order_id').last()
            if res:
                return Response(res['order_id'][:10] + str('%04d' % (int(res['order_id'][11:]) + 1)))
            else:
                return Response('CK' + str(dt.date.today().strftime('%Y%m%d')) + '0001')


@method_decorator([api_recorder], name='dispatch')
class EquipWarehouseOrderDetailViewSet(ModelViewSet):
    queryset = EquipWarehouseOrderDetail.objects.filter(delete_flag=False).order_by('-created_date')
    serializer_class = EquipWarehouseOrderDetailSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipWarehouseOrderDetailFilter

    @atomic
    def create(self, request, *args, **kwargs):
        data = self.request.data
        in_quantity = data.get('in_quantity', 1)
        out_quantity = data.get('out_quantity', 1)
        enter_time = data.get('enter_time', None)
        outer_time = data.get('outer_time', None)
        receive_user = data.get('receive_user', None)
        purpose = data.get('purpose', None)
        status = data.get('status')  # 1 入库 2 出库
        instance = self.queryset.filter(equip_warehouse_order_id=data['equip_warehouse_order'], equip_spare_id=data['equip_spare']).first()
        query = EquipWarehouseInventory.objects.filter(equip_spare_id=data['equip_spare'], delete_flag=False,
                                                       equip_warehouse_location_id=data[
                                                           'equip_warehouse_location']).first()
        enter_time = datetime.strptime(enter_time, '%Y-%m-%d %H:%M:%S') if enter_time else datetime.now()
        outer_time = datetime.strptime(outer_time, '%Y-%m-%d %H:%M:%S') if outer_time else datetime.now()
        if status == 1:
            if instance.plan_in_quantity <= instance.in_quantity:
                return Response({"success": False, "message": '该单据已入库完成', "data": None})
            if instance.in_quantity + in_quantity > instance.plan_in_quantity:
                return Response({"success": False, "message": '入库数量大于单据剩余未入库数量', "data": None})
            if instance.in_quantity + in_quantity == instance.plan_in_quantity:
                instance.status = 3  # 已完成
            elif instance.in_quantity + in_quantity < instance.plan_in_quantity:
                instance.status = 2  # 入库中
            instance.in_quantity += data['in_quantity']
            instance.enter_time = enter_time
            instance.save()

            if query:
                query.quantity += in_quantity
                query.save()
            else:
                query = EquipWarehouseInventory.objects.create(
                    created_user=self.request.user,
                    equip_spare=instance.equip_spare,
                    quantity=in_quantity,
                    equip_warehouse_area_id=data['equip_warehouse_area'],
                    equip_warehouse_location_id=data['equip_warehouse_location']
                )
            # 判断入库单据是否完成
            if self.queryset.filter(equip_warehouse_order=data['equip_warehouse_order'], status__in=[1, 2]).exists():
                EquipWarehouseOrder.objects.filter(order_detail=instance).update(status=2)
            else:
                EquipWarehouseOrder.objects.filter(order_detail=instance).update(status=3)
            # 记录履历
            EquipWarehouseRecord.objects.create(status='入库',
                                                now_quantity=query.quantity,
                                                equip_warehouse_area_id=data['equip_warehouse_area'],
                                                equip_warehouse_location_id=data['equip_warehouse_location'],
                                                equip_spare=instance.equip_spare,
                                                quantity=in_quantity,
                                                equip_warehouse_order_detail=instance,
                                                created_user=self.request.user
                                                )
            return Response({"success": True, "message": '入库成功', "data": data})
        if status == 2:
            # 出库的时候，根据出库的数量，判断库区中数量够不够
            if not query:
                return Response({"success": False, "message": '当前库位不存在该备件', "data": None})
            if query.quantity < out_quantity:
                return Response({"success": False, "message": '当前库区中的数量不足', "data": None})
            # 使用库存数量判断
            if out_quantity > query.quantity:
                return Response({"success": False, "message": '出库数量不能大于单据出库数量', "data": None})
            # if instance.plan_out_quantity <= out_quantity + instance.out_quantity:
            #     instance.out_quantity += out_quantity
            #     instance.status = 6  # 出库完成
            # else:
            instance.out_quantity += out_quantity
            instance.status = 5  # 出库中
            query.quantity -= out_quantity
            query.save()
            instance.outer_time = outer_time
            # 记录领用人和用途
            instance.receive_user = receive_user
            instance.purpose = purpose
            instance.save()

            # 判断出库单据是否完成
            if self.queryset.filter(equip_warehouse_order_id=data['equip_warehouse_order'], status__in=[4, 5]).exists():
                EquipWarehouseOrder.objects.filter(order_detail=instance).update(status=5)
            else:
                EquipWarehouseOrder.objects.filter(order_detail=instance).update(status=6)

            # 记录履历
            EquipWarehouseRecord.objects.create(status='出库',
                                                now_quantity=query.quantity,
                                                equip_warehouse_area_id=data['equip_warehouse_area'],
                                                equip_warehouse_location_id=data['equip_warehouse_location'],
                                                equip_spare=instance.equip_spare,
                                                quantity=out_quantity,
                                                equip_warehouse_order_detail=instance,
                                                created_user=self.request.user
                                                )
            return Response({"success": True, "message": '出库成功', "data": data})


@method_decorator([api_recorder], name='dispatch')
class EquipWarehouseInventoryViewSet(ModelViewSet):
    queryset = EquipWarehouseInventory.objects.filter(delete_flag=False)
    serializer_class = EquipWarehouseInventorySerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipWarehouseInventoryFilter
    FILE_NAME = '备件库存统计'
    EXPORT_FIELDS_DICT = {
        "库区": "equip_warehouse_area__area_name",
        "库位": "equip_warehouse_location__location_name",
        "备件分类": "component_type_name",
        "备件代码": "spare__code",
        "备件名称": "spare_name",
        "规格型号": "specification",
        "用途": "technical_params",
        "在库数量": "quantity",
        "标准单位": "unit",
        "库存下限": "lower_stock",
        "库存上限": "upper_stock",
    }

    def list(self, request, *args, **kwargs):
        page = self.request.query_params.get('page', 1)
        page_size = self.request.query_params.get('page_size', 10)
        equip_spare = self.request.query_params.get('equip_spare')
        equip_warehouse_location = self.request.query_params.get('equip_warehouse_location')
        if self.request.query_params.get("detail"):
            queryset = EquipWarehouseRecord.objects.filter(equip_spare_id=equip_spare,
                                                          equip_warehouse_location_id=equip_warehouse_location).order_by('id')

            if queryset.filter(status='盘库').exists():
                last_date = queryset.filter(status='盘库').last().last_updated_date
                data = queryset.filter(last_updated_date__gte=last_date).order_by('id')
            else:
                data = queryset
            # 只显示最后一次盘库到当前时间的记录
            results = EquipWarehouseRecordSerializer(data, many=True).data
            return Response({'results': results})
        if equip_spare:  # 获取库存中备件的库区和库位
            quantity = 0
            location_id = self.request.query_params.get('location_id')
            area_id = self.request.query_params.get('area_id')
            if location_id and area_id:
                inventory = self.queryset.filter(equip_spare_id=equip_spare, equip_warehouse_area_id=area_id,
                                                 quantity__gt=0, equip_warehouse_location_id=location_id).aggregate(total=Sum('quantity'))['total']
                if inventory:
                    quantity = inventory
                return Response({"quantity": quantity})
            first = self.queryset.filter(equip_spare_id=equip_spare, quantity__gt=0).first()  # 默认显示的库区和库位
            area = self.queryset.filter(equip_spare_id=equip_spare, quantity__gt=0).values('equip_warehouse_area__area_name', 'equip_warehouse_area__id').distinct()
            location = self.queryset.filter(equip_spare_id=equip_spare, quantity__gt=0).values('equip_warehouse_location__location_name', 'equip_warehouse_location__id', 'equip_warehouse_area__id').distinct()
            if not first:
                return Response({"quantity": quantity})
            inventory = self.queryset.filter(equip_spare_id=equip_spare, equip_warehouse_area=first.equip_warehouse_area,
                                             quantity__gt=0, equip_warehouse_location=first.equip_warehouse_location).aggregate(
                total=Sum('quantity'))['total']
            if inventory:
                quantity = inventory
            return Response({'area': area, 'location': location, 'quantity': quantity, 'first': {
                'area_name': first.equip_warehouse_area.area_name,
                'area_id': first.equip_warehouse_area.id,
                'location_name': first.equip_warehouse_location.location_name,
                'location_id': first.equip_warehouse_location.id,
            }})
        if self.request.query_params.get('use'):
            data = self.filter_queryset(self.queryset.filter(quantity__gt=0)).values('equip_spare').annotate(qty=Sum('quantity')).values(
                                            'equip_spare__equip_component_type__component_type_name',
                                            'equip_spare__spare_code',
                                            'equip_spare__spare_name',
                                            'equip_spare__specification',
                                            'equip_spare__technical_params',
                                            'qty',
                                            'equip_spare',
                                            'equip_spare__unit',
                                            'equip_spare__upper_stock',
                                            'equip_spare__lower_stock')
        else:
            data = self.filter_queryset(self.queryset.filter(quantity__gt=0)).values('equip_spare', 'equip_warehouse_location').annotate(
                quantity=Sum('quantity')).values(
                                                 'equip_warehouse_area__id',
                                                 'equip_warehouse_area__area_name',
                                                 'equip_warehouse_location__id',
                                                 'equip_warehouse_location__location_name',
                                                 'equip_spare__equip_component_type__component_type_name',
                                                 'equip_spare__spare_code',
                                                 'equip_spare__spare_name',
                                                 'equip_spare__specification',
                                                 'equip_spare__technical_params',
                                                 'quantity',
                                                 'equip_spare',
                                                 'equip_spare__unit',
                                                 'equip_spare__upper_stock',
                                                 'equip_spare__lower_stock').distinct()
        for item in data:
            item['component_type_name'] = item['equip_spare__equip_component_type__component_type_name']
            item['spare_name'] = item['equip_spare__spare_name']
            item['spare__code'] = item['equip_spare__spare_code']
            item['specification'] = item['equip_spare__specification']
            item['technical_params'] = item['equip_spare__technical_params']
            item['upper_stock'] = item['equip_spare__upper_stock']
            item['lower_stock'] = item['equip_spare__lower_stock']
            item['unit'] = item['equip_spare__unit']
        if self.request.query_params.get('export'):
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        st = (int(page) - 1) * int(page_size)
        et = int(page) * int(page_size)
        count = len(data)
        if self.request.query_params.get('all'):
            return Response({'results': data})
        return Response({'results': data[st:et], 'count': count})

    @atomic
    def create(self, request, *args, **kwargs):
        handle = self.request.data.get('handle')
        data = self.request.data
        inventory = self.queryset.filter(equip_spare_id=data['equip_spare'], equip_warehouse_location_id=data['equip_warehouse_location__id']).first()
        if not inventory:
            return Response({"success": False, "message": '备件代码不存在', "data": None})
        if handle:
            # 盘库
            if handle == '盘库':
                quantity = data.get('quantity')
                inventory.quantity = data['quantity']
            elif handle == '移库':
                if data['move_equip_warehouse_location__id'] == data['equip_warehouse_location__id']:
                    return Response({"success": False, "message": '不能移动到当前库区', "data": None})
                quantity = f"-{data.get('quantity')}"
                if inventory.quantity < data['quantity']:
                    return Response({"success": False, "message": '当前库存数量不足', "data": None})
                inventory.quantity -= data['quantity']
                new_queryset = self.queryset.filter(equip_spare_id=data['equip_spare'], equip_warehouse_location_id=data['move_equip_warehouse_location__id'])
                if new_queryset.exists():
                    new = new_queryset.first()
                    new.quantity += data['quantity']
                    new.save()
                    new_quantity = new.quantity
                else:
                    obj = self.queryset.create(quantity=data['quantity'], equip_spare_id=data['equip_spare'],
                                         equip_warehouse_area_id=data['move_equip_warehouse_area__id'],
                                         equip_warehouse_location_id=data['move_equip_warehouse_location__id'])
                    new_quantity = obj.quantity
                # 记录履历
                EquipWarehouseRecord.objects.create(
                    status=handle,
                    revocation_desc=data.get('desc'),
                    equip_warehouse_area_id=data.get('move_equip_warehouse_area__id'),
                    equip_warehouse_location_id=data.get('move_equip_warehouse_location__id'),
                    now_quantity=new_quantity,
                    quantity=f"+{data.get('quantity')}",
                    equip_spare_id=data.get('equip_spare'),
                    created_user=self.request.user),
            elif handle == '删除':
                inventory.quantity = 0
                quantity = inventory.quantity
                inventory.delete_flag = True
            else:
                raise ValidationError('未知操作')
            # 记录履历
            inventory.save()
            now_quantity = inventory.quantity
            EquipWarehouseRecord.objects.create(
                status=handle,
                revocation_desc=data.get('desc'),
                equip_warehouse_area_id=data.get('equip_warehouse_area__id'),
                equip_warehouse_location_id=data.get('equip_warehouse_location__id'),
                now_quantity=now_quantity,
                quantity=quantity,
                equip_spare_id=data.get('equip_spare'),
                created_user=self.request.user)
            return Response({"success": True, "message": '操作成功', "data": data})

        else:
            return super().update(request, *args, **kwargs)


class EquipWarehouseRecordViewSet(ModelViewSet):
    queryset = EquipWarehouseRecord.objects.filter(status__in=['入库', '出库']).order_by('-created_date')
    serializer_class = EquipWarehouseRecordSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipWarehouseRecordFilter
    FILE_NAME = '备件出入库履历'
    EXPORT_FIELDS_DICT = {
        "出库/入库": "status",
        "出入库单号": "order_id",
        "工单编号": "work_order_no",
        "备件代码": "spare_code",
        "备件名称": "spare_name",
        "备件分类": "component_type_name",
        "规格型号": "specification",
        "用途": "technical_params",
        "单价": "cost",
        "数量": "quantity",
        "单位": "unit",
        "金额": "money",
        "库区": "area_name",
        "库位": "location_name",
        "操作人": "created_username",
        "操作日期": "created_date",
        "是否撤销": "revocation",
        "撤销备注": "revocation_desc"
    }

    def list(self, request, *args, **kwargs):
        if self.request.query_params.get('export'):
            serializer = self.get_serializer(self.filter_queryset(self.queryset), many=True)
            return gen_template_response(self.EXPORT_FIELDS_DICT, list(serializer.data), self.FILE_NAME)
        if self.request.query_params.get('work_order_no'):
            work_order_no = self.request.query_params.get('work_order_no')
            order = EquipApplyOrder.objects.filter(work_order_no=work_order_no).first()
            fault_name = order.result_fault_cause if order.result_fault_cause else (
                order.equip_repair_standard.standard_name if order.equip_repair_standard else order.equip_maintenance_standard.standard_name)
            return Response({'plan_name': order.plan_name,
                             'work_order_no': order.work_order_no,
                             'equip_no': order.equip_no,
                             'fault_name': fault_name,
                             'result_fault_desc': order.result_fault_desc})

        return super().list(request, *args, **kwargs)

    @atomic
    def update(self, request, *args, **kwargs):  # 撤销
        revocation_desc = self.request.data.get('revocation_desc')
        equip_warehouse_location = self.request.data.get('equip_warehouse_location')
        equip_spare = self.request.data.get('equip_spare')
        instance = self.get_object()
        quantity = int(instance.quantity)
        inventory = EquipWarehouseInventory.objects.filter(equip_spare_id=equip_spare,
                                                          equip_warehouse_location_id=equip_warehouse_location).first()
        if instance.created_user == self.request.user:
            order_detail = instance.equip_warehouse_order_detail
            if instance.status == '入库':
                if order_detail.in_quantity == quantity:
                    order_detail.status = 1
                else:
                    order_detail.status = 2
                order_detail.in_quantity -= quantity
                EquipWarehouseOrder.objects.filter(order_detail=order_detail).update(status=2)
                if inventory.quantity <= quantity:
                    inventory.quantity = 0
                else:
                    inventory.quantity -= quantity
                inventory.save()
            if instance.status == '出库':
                order_detail.out_quantity -= quantity
                if order_detail.out_quantity == quantity:
                    order_detail.status = 4
                else:
                    order_detail.status = 5
                EquipWarehouseOrder.objects.filter(order_detail=order_detail).update(status=5)
                inventory.quantity += quantity
                inventory.save()
            EquipWarehouseRecord.objects.filter(id=instance.id).update(revocation='Y')
            order_detail.save()
            # 记录履历
            EquipWarehouseRecord.objects.create(
                status='撤销',
                equip_warehouse_area=instance.equip_warehouse_area,
                equip_warehouse_location=instance.equip_warehouse_location,
                equip_warehouse_order_detail=instance.equip_warehouse_order_detail,
                now_quantity=inventory.quantity,
                quantity=quantity,
                equip_spare=instance.equip_spare,
                created_user=self.request.user,
                revocation_desc=revocation_desc if revocation_desc else None
            )
            return Response('撤销成功')
        return Response('只能撤销自己的单据')


@method_decorator([api_recorder], name='dispatch')
class EquipWarehouseStatisticalViewSet(ListModelMixin, GenericViewSet):
    queryset = EquipWarehouseRecord.objects.filter(revocation='N')
    serializer_class = EquipWarehouseRecordSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipWarehouseStatisticalFilter
    FILE_NAME = '出入库统计分析'
    EXPORT_FIELDS_DICT = {
        "物料编码": "spare__code",
        "物料名称": "spare_name",
        "备件分类": "component_type_name",
        "规格型号": "specification",
        "用途": "technical_params",
        "单价": "equip_spare__cost",
        "入库数量": "in_qty",
        "数量单位": "unit",
        "入库金额": "in_money",
        "出库数量": "out_qty",
        "出库金额": "out_money"
    }

    def list(self, request, *args, **kwargs):
        page = self.request.query_params.get('page', 1)
        page_size = self.request.query_params.get('page_size', 10)
        if self.request.query_params.get('detail'):  # 入出库统计明细
            results = self.serializer_class(self.filter_queryset(self.queryset), many=True).data
            return Response({'results': results})
        else:
            results = self.filter_queryset(self.queryset.filter(status__in=['入库', '出库'])).values('equip_spare').annotate(
                in_qty=Sum('quantity', distinct=True, filter=Q(status='入库')),
                out_qty=Sum('quantity', distinct=True, filter=Q(status='出库'))).values(
                'in_qty', 'out_qty', 'equip_spare', 'equip_spare__spare_code',
                'equip_spare__spare_name',
                'equip_spare__equip_component_type__component_type_name',
                'equip_spare__specification', 'equip_spare__technical_params',
                'equip_spare__unit', 'equip_spare__cost')
            for item in results:
                item['spare__code'] = item['equip_spare__spare_code']
                item['component_type_name'] = item['equip_spare__equip_component_type__component_type_name']
                item['spare_name'] = item['equip_spare__spare_name']
                item['specification'] = item['equip_spare__specification']
                item['technical_params'] = item['equip_spare__technical_params']
                item['unit'] = item['equip_spare__unit']
                item['in_qty'] = item['in_qty'] if item['in_qty'] else 0
                item['out_qty'] = item['out_qty'] if item['out_qty'] else 0
                item['in_money'] = (item['in_qty'] * item['equip_spare__cost']) if item['equip_spare__cost'] and item['in_qty'] else 0
                item['out_money'] = (item['out_qty'] * item['equip_spare__cost']) if item['equip_spare__cost'] and item['out_qty'] else 0
            st = (int(page) - 1) * int(page_size)
            et = int(page) * int(page_size)
            if self.request.query_params.get('export'):
                return gen_template_response(self.EXPORT_FIELDS_DICT, results, self.FILE_NAME)
            count = len(results)
            return Response({'results': results[st:et], 'count': count})


@method_decorator([api_recorder], name='dispatch')
class EquipAutoPlanView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        get_code = self.request.query_params.get('get_code')
        spare_code = self.request.query_params.get('spare_code')
        order_id = self.request.query_params.get('order_id')
        default_staff = self.request.query_params.get('default_staff')  # 保养组名单
        if default_staff:
            init_section = Section.objects.filter(name='保养组').last()
            if not init_section:
                return Response({"success": False, "message": "未找到保养组", "data": []})
            section_list = get_children_section(init_section, include_self=True)
            res = list(User.objects.filter(section__name__in=section_list, is_active=True).annotate(order_id=F('username')).values('id', 'order_id').distinct())
            return Response({"success": True, "message": "获取保养组成员信息成功", "data": res})
        if get_code:
            if get_code == "1":
                order_list = EquipWarehouseOrder.objects.filter(status__in=[1, 2], order_detail__delete_flag=False,
                                                                order_detail__equip_spare__spare_code=spare_code) \
                    .values('id', 'order_id')
            else:
                order_list = EquipWarehouseOrder.objects.filter(status__in=[4, 5], order_detail__delete_flag=False,
                                                                order_detail__equip_spare__spare_code=spare_code) \
                    .values('id', 'order_id')
            return Response({"success": True, "message": None, "data": order_list})
        if spare_code and order_id:  # 获取入库/出库备件信息
            order = EquipWarehouseOrderDetail.objects.filter(equip_spare__spare_code=spare_code, delete_flag=False,
                                                             equip_warehouse_order__order_id=order_id).first()
            if not order:
                return Response({"success": False, "message": '条码扫描有误', "data": None})
            obj = EquipSpareErp.objects.filter(spare_code=spare_code).first()
            if order.status in [1, 2, 3]:  # 入库单据
                quantity = order.plan_in_quantity - order.in_quantity
                queryset = EquipWarehouseInventory.objects.filter(equip_spare__spare_code=spare_code, quantity__gt=0)
                default = queryset.first()
                area = EquipWarehouseArea.objects.filter(
                    Q(warehouse_area__equip_component_type=obj.equip_component_type) | Q(
                        warehouse_area__isnull=True)).first()
                areas = EquipWarehouseArea.objects.filter(delete_flag=False).values('id', 'area_name')
                areas = [{'equip_warehouse_area_id': item['id'], 'area_name': item['area_name']} for item in areas]
                if not area:
                    return Response({"success": False, "message": '该备件没有可存放的库区', "data": None})
                location = list(EquipWarehouseLocation.objects.filter(equip_warehouse_area=area,
                                                                 delete_flag=False).values('id', 'location_name'))
                # 该备件可以存放的库区和库位
                if default:  # 默认显示的库区
                    area_id = default.equip_warehouse_area.id
                    area_name = default.equip_warehouse_area.area_name
                    de_location_name = default.equip_warehouse_location.location_name
                    de_location_id = default.equip_warehouse_location.id
                else:
                    area_id = area.id if area else None
                    area_name = area.area_name if area else None
                    de_location_name = location[0].get('location_name')
                    de_location_id = location[0].get('id')
                # 将默认显示的库位放到第一个
                for i in location:
                    if i['id'] == de_location_id:
                        location.insert(0, location.pop(location.index(i)))

            else:  # 出库单据
                quantity = 0
                location_id = self.request.query_params.get('location_id')
                area_id = self.request.query_params.get('area_id')
                if location_id and area_id:
                    inventory = EquipWarehouseInventory.objects.filter(equip_spare__spare_code=spare_code, delete_flag=False,
                                                                       equip_warehouse_area_id=area_id, quantity__gt=0,
                                                                       equip_warehouse_location_id=location_id).aggregate(total=Sum('quantity'))['total']
                    if inventory:
                        quantity = inventory
                    return Response({"success": True, "message": None, "data": {"quantity": quantity}})
                queryset = EquipWarehouseInventory.objects.filter(equip_spare__spare_code=spare_code, quantity__gt=0)
                default = queryset.first()
                if not default:
                    return Response({"success": False, "message": '库存中不存在该备件', "data": None})
                area_id = default.equip_warehouse_area.id
                area_name = default.equip_warehouse_area.area_name
                areas = queryset.values('equip_warehouse_area__id', 'equip_warehouse_area__area_name').distinct()
                areas = [{'equip_warehouse_area_id': item['equip_warehouse_area__id'], 'area_name': item['equip_warehouse_area__area_name']} for item in areas]
                res = queryset.values('equip_warehouse_location__location_name', 'equip_warehouse_location__id').distinct()
                location = [{'id': item['equip_warehouse_location__id'],
                             'location_name': item['equip_warehouse_location__location_name']} for item in res]
                de_location_name = default.equip_warehouse_location.location_name
                de_location_id = default.equip_warehouse_location.id
                # 当前库区的所有库位
                # 将默认显示的库位放到第一个
                for i in location:
                    if i['id'] == de_location_id:
                        location.insert(0, location.pop(location.index(i)))
                        quantity = default.quantity
            now_locations = list(default.equip_warehouse_area.equipwarehouselocation_set.filter(id__in=list(queryset.values_list('equip_warehouse_location_id', flat=True))).values('id', 'location_name')) if default else []
            data = {
                'id': order.id,
                "equip_warehouse_order": order.equip_warehouse_order.id,
                'spare_code': order.equip_spare.spare_code,
                'spare_name': order.equip_spare.spare_name,
                'quantity': quantity,
                'area_id': area_id,
                'area_name': area_name,
                'areas': areas,
                'location': now_locations,
                'de_location_id': de_location_id,  # 默认显示的库区
                'de_location_name': de_location_name,
                'equip_spare': order.equip_spare.id
            }
            return Response({"success": True, "message": None, "data": data})
        else:  # 备件移库/盘库
            data = EquipWarehouseInventory.objects.filter(equip_spare__spare_code=spare_code, quantity__gt=0)\
                .values('equip_spare', 'equip_warehouse_location').annotate(
                quantity=Sum('quantity')).values(
                'equip_warehouse_area__id',
                'equip_warehouse_area__area_name',
                'equip_warehouse_location__id',
                'equip_warehouse_location__location_name',
                'equip_spare__spare_code',
                'equip_spare__spare_name',
                'quantity',
                'equip_spare').distinct()
            dic = {}
            if data:
                location = [{'id': item['equip_warehouse_location__id'],
                             'location_name': item['equip_warehouse_location__location_name'],
                             'quantity': item['quantity']
                             } for item in data]
                move_location = EquipWarehouseLocation.objects.filter(equip_warehouse_area_id=data[0]['equip_warehouse_area__id'],
                                                                      delete_flag=False).values('id', 'location_name')
                dic.update({
                    'area_id': data[0]['equip_warehouse_area__id'],
                    'area_name': data[0]['equip_warehouse_area__area_name'],
                    'location': location,
                    'spare_code': data[0]['equip_spare__spare_code'],
                    'spare_name': data[0]['equip_spare__spare_name'],
                    'move_location': move_location,
                    'equip_spare': data[0]['equip_spare']
                })
            return Response({"success": True, "message": None, "data": dic})


@method_decorator([api_recorder], name='dispatch')
class EquipApplyRepairViewSet(ModelViewSet):
    """
    list:报修申请列表
    create:新增报修申请
    """
    queryset = EquipApplyRepair.objects.all().order_by('-id')
    serializer_class = EquipApplyRepairSerializer
    permission_classes = (IsAuthenticated, PermissionClass({'view': ['view_equip_apply_repair', 'assign_d_equip_apply_order'],
                                                            'add': ['add_equip_apply_repair', 'assign_d_equip_apply_order']}))
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipApplyRepairFilter


@method_decorator([api_recorder], name='dispatch')
class EquipApplyOrderViewSet(ModelViewSet):
    """
    list:设备维修工单列表
    """
    queryset = EquipApplyOrder.objects.all().order_by('-id')
    serializer_class = EquipApplyOrderSerializer
    permission_classes = (IsAuthenticated, PermissionClass({'view': ['view_equip_apply_order', 'close_d_equip_apply_order',
                                                                     'export_equip_apply_order', 'view_d_equip_apply_order',
                                                                     'close_d_equip_apply_order'],
                                                            'add': ['close_equip_apply_order', 'assign_equip_apply_order',
                                                                    'receive_equip_apply_order', 'charge_equip_apply_order',
                                                                    'begin_equip_apply_order', 'accept_equip_apply_order',
                                                                    'regulation_equip_apply_order', 'receive_d_equip_apply_order',
                                                                    'view_d_equip_apply_order'],
                                                            'change': ['handle_equip_apply_order']}))
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipApplyOrderFilter
    FILE_NAME = '设备维修工单表'
    EXPORT_FIELDS_DICT = {
        "计划/报修编号": "plan_id",
        "计划/报修名称": "plan_name",
        "工单编号": "work_order_no",
        "机台": "equip_no",
        "部位名称": "part_name",
        "维修标准/故障原因": "fault_reason",
        "故障详情描述": "result_fault_desc",
        "维修备注": "result_repair_desc",
        "计划维修日期": "planned_repair_date",
        "设备条件": "equip_condition",
        "重要程度": "importance_level",
        "状态": "status",
        "维修人": "repair_user",
        "维修开始时间": "repair_start_datetime",
        "维修结束时间": "repair_end_datetime",
        "是否需要物料": "result_material_requisition",
        "是否需要外协助": "result_need_outsourcing",
        "是否等待物料": "wait_material",
        "是否等待外维修": "wait_outsourcing",
        "指派人": "assign_user",
        "指派时间": "assign_datetime",
        "被指派人": "assign_to_user",
        "接单人": "receiving_user",
        "接单时间": "receiving_datetime",
        "报修人": "created_username",
        "报修时间": "created_date",
        "验收人": "accept_user",
        "验收时间": "accept_datetime",
        "验收结果": "result_accept_result",
        "验收记录": "result_accept_result",
    }

    def get_user(self, section, users=[]):  # 获取当前部门负责人下的所有人
        if section.in_charge_user:
            users += [section.in_charge_user.username]
        users += User.objects.filter(section=section).values_list('username', flat=True)
        for s in Section.objects.filter(parent_section=section):
            self.get_user(s, users)
        return users

    def get_assign_user_queryset(self, status, users):
        queryset_id = []
        queryset = EquipApplyOrder.objects.filter(status=status).values('assign_to_user', 'id')
        for item in queryset:
            if item['assign_to_user'].split(',')[0] in users:
                queryset_id.append(item['id'])
        return EquipApplyOrder.objects.filter(id__in=queryset_id) if queryset_id else None

    def get_queryset(self):
        my_order = self.request.query_params.get('my_order')
        status = self.request.query_params.get('status')
        searched = self.request.query_params.get('searched')
        orders_filter = self.request.query_params.get('orders_filter', 'false')  # 工单大厅只展示个人相关的单据
        user_name = self.request.user.username
        query_set = self.queryset
        # my_order: '1'个人工单页面、'2'工单大厅; status空表示进行中或工单搜索; searched空名下进行中工单,反之在所有工单中检索
        if my_order == '1':
            if not status:
                if not searched:
                    # 判断当前用户是否是部门负责人，是的话可以看到所有执行中的单据
                    section = Section.objects.filter(in_charge_user=self.request.user).first()
                    if section:
                    # if Section.objects.filter(name='设备科', in_charge_user=self.request.user).exists():  # 写死，设备科
                        users = self.get_user(section, users=[])
                        query_set = query_set.filter(Q(Q(status='已接单', receiving_user__in=users) |
                                                       Q(status='已开始', repair_end_datetime__isnull=True,
                                                         receiving_user__in=users)))
                    else:
                        query_set = query_set.filter(  # repair_user
                            Q(Q(status='已接单', repair_user__icontains=user_name) |
                              Q(status='已开始', repair_end_datetime__isnull=True, repair_user__icontains=user_name) |
                              Q(status__in=['已接单', '已开始'], entrust_to_user__icontains=user_name)
                              ))
                else:
                    query_set = query_set.filter(
                        Q(assign_to_user__icontains=user_name) | Q(receiving_user=user_name) |
                        Q(repair_user__icontains=user_name) | Q(accept_user=user_name) | Q(status='已生成'))
            else:
                section = Section.objects.filter(in_charge_user=self.request.user).first()
                if section:
                    users = self.get_user(section, users=[])
                    query_set = query_set.filter(Q(status='已生成') | Q(Q(status='已完成') & Q(receiving_user__in=users)) |
                                                 Q(Q(status__in=['已接单', '已开始']) & Q(receiving_user__in=users)) |
                                                 Q(Q(status='已验收', receiving_user__in=users)))
                    queryset_assigned = self.get_assign_user_queryset('已指派', users)
                    if queryset_assigned:
                        query_set = query_set | queryset_assigned
                else:
                    query_set = query_set.filter(Q(status='已生成') |
                    Q(Q(status='已完成') & Q(Q(accept_user=user_name) | Q(repair_user__icontains=user_name) | Q(created_user__username=user_name))) |
                    Q(Q(status='已指派') & Q(assign_to_user__icontains=user_name)) |
                    Q(Q(status__in=['已接单', '已开始']) & Q(Q(entrust_to_user=user_name) | Q(repair_user__icontains=user_name))) |
                    Q(Q(status='已验收', accept_user=user_name)))

        elif my_order == '2':
            if orders_filter == 'true':
                query_set = query_set.filter(Q(assign_user__icontains=user_name) | Q(assign_to_user__icontains=user_name) |
                                             Q(receiving_user__icontains=user_name) | Q(repair_user__icontains=user_name) |
                                             Q(accept_user__icontains=user_name) | Q(created_user__username__icontains=user_name))
            if not status and not searched:
                query_set = query_set.filter(Q(Q(status='已接单') | Q(status='已开始', repair_end_datetime__isnull=True)))
        return query_set

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        my_order = self.request.query_params.get('my_order')
        orders_filter = self.request.query_params.get('orders_filter', 'false')  # 工单大厅只展示个人相关的单据
        user_name = self.request.user.username
        if self.request.query_params.get('export'):
            data = EquipApplyOrderExportSerializer(self.filter_queryset(self.get_queryset()), many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        # 小程序获取数量 带指派 带接单 进行中 已完成 已验收
        if my_order == '1':
            wait_assign = self.queryset.filter(status='已生成').count()
            section = Section.objects.filter(in_charge_user=self.request.user).first()
            if section:
                users = self.get_user(section, users=[])
                # assigned = self.queryset.filter(status='已指派', assign_to_user__in=self.users).count()
                queryset_assigned = self.get_assign_user_queryset('已指派', users)
                assigned = queryset_assigned.count() if queryset_assigned else 0
                processing = self.queryset.filter(Q(
                                                    Q(status='已接单', receiving_user__in=users) |
                                                    Q(status='已开始', receiving_user__in=users))).count()
                finished = self.queryset.filter(Q(status='已完成', receiving_user__in=users)).count()
            else:
                assigned = self.queryset.filter(status='已指派', assign_to_user__icontains=user_name).count()
                processing = self.queryset.filter(Q(Q(status='已接单', repair_user__icontains=user_name) |
                                                    Q(status='已开始', repair_end_datetime__isnull=True,
                                                      repair_user__icontains=user_name) |
                                                    Q(status__in=['已接单', '已开始'], entrust_to_user__icontains=user_name))).count()
            # finished = self.queryset.filter(status='已完成', accept_user=user_name).count()
                finished = self.queryset.filter(Q(status='已完成') & Q(Q(accept_user=user_name) | Q(repair_user__icontains=user_name) | Q(created_user__username=user_name))).count()
            accepted = self.queryset.filter(status='已验收', accept_user=user_name).count()
        else:
            query_set = self.queryset
            if orders_filter == 'true':
                query_set = query_set.filter(Q(assign_user__icontains=user_name) | Q(assign_to_user__icontains=user_name) |
                                             Q(receiving_user__icontains=user_name) | Q(repair_user__icontains=user_name) |
                                             Q(accept_user__icontains=user_name) | Q(created_user__username__icontains=user_name))
            wait_assign = query_set.filter(status='已生成').count()
            assigned = query_set.filter(status='已指派').count()
            processing = query_set.filter(Q(Q(status='已接单') | Q(status='已开始', repair_end_datetime__isnull=True))).count()
            finished = query_set.filter(status='已完成').count()
            accepted = query_set.filter(status='已验收').count()
        data = {'wait_assign': wait_assign, 'assigned': assigned, 'processing': processing,
                'finished': finished, 'accepted': accepted}
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            for item in serializer.data:
                item.update(data)
            response = self.get_paginated_response(serializer.data)
            response.data.update({'index': data})
            return response

        serializer = self.get_serializer(queryset, many=True)
        for item in serializer.data:
            item.update(data)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # 增减维修人员
        if self.request.data.get('order_id'):
            data = self.request.data
            users = '，'.join(data.get('users'))
            # 记录到增减人员履历中
            obj = self.queryset.filter(id=data.get('order_id')).first()
            new_users = data.get('users')
            actual_users = EquipRegulationRecord.objects.filter(plan_id=obj.plan_id, status='增').values_list('user', flat=True)
            #  新增的
            add_user = list(set(new_users).difference(set(actual_users)))
            # 要删除的
            del_user = list(set(actual_users).difference(set(new_users)))
            for user in add_user:  # 增加人员
                regulation = EquipRegulationRecord.objects.filter(plan_id=obj.plan_id, status='减', user=user)
                if obj.status == '已接单':
                    if regulation.exists():
                        regulation.update(status='增')
                    elif not regulation.exists():
                        EquipRegulationRecord.objects.create(plan_id=obj.plan_id, status='增', user=user)
                elif obj.status == '已开始':
                    if regulation.exists():
                        regulation.update(begin_time=datetime.now(), status='增', end_time=None)
                    elif not regulation.exists():
                        EquipRegulationRecord.objects.create(plan_id=obj.plan_id, status='增', user=user, begin_time=datetime.now())
            for user in del_user:  # 删除人员     没有     增的有
                regulation = EquipRegulationRecord.objects.filter(plan_id=obj.plan_id, status='增', user=user)
                if obj.status == '已接单':
                    if regulation.exists():
                        regulation.update(status='减')
                elif obj.status == '已开始':
                    if regulation.exists():
                        use_time = regulation.first().use_time + float('%.2f' % ((datetime.now() - regulation.first().begin_time).total_seconds() / 60))
                        regulation.update(status='减', end_time=datetime.now(), use_time=use_time)
            # 不变的
            # list(set(actual_users).intersection(set(new_users)))
            self.queryset.filter(id=data.get('order_id')).update(repair_user=users)
            return Response('修改完成')
        return super().create(request, *args, **kwargs)

    @atomic
    @action(methods=['post'], detail=False, url_name='multi_update', url_path='multi_update')
    def multi_update(self, request):
        data = copy.deepcopy(self.request.data)
        pks = data.pop('pks')
        opera_type = data.pop('opera_type')
        user_ids = self.request.user.username
        ding_api = DinDinAPI()
        now_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        plan_ids = self.get_queryset().filter(id__in=pks).values_list('plan_id', flat=True)
        content = {}
        if opera_type == '指派':
            assign_num = EquipApplyOrder.objects.filter(~Q(status__in=['已生成', '已指派', '已接单']), id__in=pks).count()
            if assign_num != 0:
                raise ValidationError('存在非可指派/改派的订单, 请刷新订单!')
            assign_to_user = data.get('assign_to_user')
            if not assign_to_user:
                raise ValidationError('未选择被指派人')
            data = {
                'status': data.get('status'), 'assign_to_user': ','.join(assign_to_user), 'assign_user': user_ids,
                'assign_datetime': now_date, 'last_updated_date': datetime.now(), 'receiving_user': None,
                'receiving_datetime': None
            }
            content.update({"title": "您有新的设备维修单到达，请尽快处理！",
                            "form": [{"key": "指派人:", "value": self.request.user.username},
                                     {"key": "指派时间:", "value": now_date}]})
            user_ids = get_ding_uids(ding_api, names=assign_to_user)
        elif opera_type == '接单':
            assign_to_num = EquipApplyOrder.objects.filter(~Q(status='已指派'), id__in=pks).count()
            if assign_to_num != 0:
                raise ValidationError('存在未被指派的订单, 请刷新订单!')
            data = {
                'status': data.get('status'), 'receiving_user': user_ids, 'repair_user': user_ids,
                'receiving_datetime': now_date, 'last_updated_date': datetime.now(), 'timeout_color': None
            }
            # 记录到增减人员履历中
            for plan_id in plan_ids:
                EquipRegulationRecord.objects.create(user=user_ids, plan_id=plan_id, status='增')
            content.update({"title": f"您指派的设备维修单已被{user_ids}接单",
                            "form": [{"key": "接单人:", "value": user_ids},
                                     {"key": "接单时间:", "value": now_date}]})
            user_ids = get_ding_uids(ding_api, pks)
        elif opera_type == '退单':
            receive_num = EquipApplyOrder.objects.filter(~Q(status='已指派'), id__in=pks).count()
            if receive_num != 0:
                raise ValidationError('未指派订单无法退单, 请刷新订单!')
            data = {
                'status': data.get('status'), 'receiving_user': None, 'receiving_datetime': None,
                'assign_user': None, 'assign_datetime': None, 'timeout_color': None, 'back_order': True,
                'assign_to_user': None, 'last_updated_date': datetime.now(), 'back_reason': data.get('back_reason')
            }
            content.update({"title": f"您指派的设备维修单已被{user_ids}退单",
                            "form": [{"key": "退单人:", "value": user_ids},
                                     {"key": "退单时间:", "value": now_date}]})
            user_ids = get_ding_uids(ding_api, pks)
        elif opera_type == '开始':
            # 修改
            receive_num = EquipApplyOrder.objects.filter(~Q(status='已接单'), id__in=pks).count()
            if receive_num != 0:
                raise ValidationError('订单未被接单, 请刷新订单!')
            # 如果是报修工单，故障发生时间
            obj = self.get_queryset().filter(id__in=pks).first()
            fault_datetime = now_date
            if obj and EquipApplyRepair.objects.filter(plan_id=obj.plan_id).exists():
                fault_datetime = EquipApplyRepair.objects.filter(plan_id=obj.plan_id).first().fault_datetime
            data = {
                'status': data.get('status'), 'repair_start_datetime': now_date, 'fault_datetime': fault_datetime,
                'last_updated_date': datetime.now(), 'timeout_color': None
            }
            # 记录到增减人员履历中
            for plan_id in plan_ids:
                EquipRegulationRecord.objects.filter(plan_id=plan_id).update(begin_time=datetime.now())
            # 更新维护计划状态
            equip_plan = EquipApplyOrder.objects.filter(id__in=pks).values_list('plan_id', flat=True)
            EquipPlan.objects.filter(plan_id__in=equip_plan).update(status='计划执行中')
        elif opera_type == '处理':
            repair_num = EquipApplyOrder.objects.filter(~Q(status='已开始'), id__in=pks).count()
            if repair_num != 0:
                raise ValidationError('未开始订单无法进行处理操作, 请刷新订单!')
            result_repair_final_result = data.get('result_repair_final_result')  # 维修结论
            work_content = data.pop('work_content', [])
            image_url_list = data.pop('image_url_list', [])
            video_url_list = data.pop('video_url_list', [])
            work_type = data.pop('work_type')
            work_order_no = data.pop('work_order_no')
            apply_material_list = data.pop('apply_material_list', [])
            if result_repair_final_result == '等待':
                data.update({'last_updated_date': datetime.now(), 'status': '已开始'})
                # 申请了物料,需要插入到物料申请表
            else:
                # 工单完成，设置验收人
                instance = self.queryset.filter(id__in=pks).first()
                if instance.created_user.username == '系统自动':
                    data.update({'repair_end_datetime': now_date, 'last_updated_date': datetime.now(), 'status': '已验收',
                                 'accept_user': '系统自动', 'accept_datetime': now_date, 'result_accept_desc': '验收通过',
                                 'result_accept_result': '合格'})
                else:
                    data.update({'repair_end_datetime': now_date, 'last_updated_date': datetime.now(), 'status': '已完成',
                                 'accept_user': instance.created_user.username})
            data.update({'result_repair_graph_url': json.dumps(image_url_list), 'result_repair_video_url': json.dumps(video_url_list)})
            # 记录到增减人员履历中
            for plan_id in plan_ids:
                queryset = EquipRegulationRecord.objects.filter(plan_id=plan_id, status='增')
                for obj in queryset:
                    obj.end_time = datetime.now()
                    obj.use_time += float('%.2f' %((datetime.now() - obj.begin_time).total_seconds() / 60))
                    obj.save()
            # 更新作业内容
            if work_type == "维修":
                result_standard = data.get('result_repair_standard')
                instance = EquipRepairStandard.objects.filter(id=result_standard).first()
            else:
                result_standard = data.get('result_maintenance_standard')
                instance = EquipMaintenanceStandard.objects.filter(id=result_standard).first()
            if instance:
                EquipResultDetail.objects.filter(work_order_no=work_order_no).delete()
                for item in work_content:
                    item.update({'work_type': work_type, 'work_order_no': work_order_no})
                    EquipResultDetail.objects.create(**item)
            for apply_material in apply_material_list:
                EquipRepairMaterialReq.objects.create(**apply_material)
        elif opera_type == '验收':
            accept_num = EquipApplyOrder.objects.filter(~Q(status='已完成'), id__in=pks).count()
            if accept_num != 0:
                raise ValidationError('已完成订单才可验收, 请刷新订单!')
            image_url_list = data.pop('image_url_list', [])
            video_url_list = data.pop('video_url_list', [])
            result_accept_result = data.get('result_accept_result')
            if result_accept_result == '合格':
                # 更新巡检中异常报修的工单状态
                for obj in self.get_queryset().filter(id__in=pks):
                    EquipInspectionOrder.objects.filter(apply_order=obj).update(status='已完成', repair_end_datetime=now_date)
                data = {
                    'status': data.get('status'), 'accept_datetime': now_date,
                    'result_accept_result': result_accept_result, 'timeout_color': None,
                    'result_accept_desc': data.get('result_accept_desc'),
                    'result_accept_graph_url': json.dumps(image_url_list), 'last_updated_date': datetime.now(),
                    'result_accept_video_url': json.dumps(video_url_list)
                }
            else:
                data = {
                    'status': data.get('status'), 'repair_end_datetime': None, 'accept_datetime': now_date,
                    'result_accept_result': result_accept_result, 'result_accept_video_url': json.dumps(video_url_list),
                    'result_accept_desc': data.get('result_accept_desc'),
                    'result_accept_graph_url': json.dumps(image_url_list), 'last_updated_date': datetime.now()
                }
        else:  # 关闭
            close_num = EquipApplyOrder.objects.filter(status='已关闭', id__in=pks).count()
            if close_num != 0:
                raise ValidationError('存在已经关闭的订单, 请刷新订单!')
            data = {'status': data.get('status'), 'last_updated_date': datetime.now(), 'timeout_color': None,
                    'close_reason': data.get('close_reason')}
            content.update({"title": f"您指派的设备维修单已被{user_ids}关闭",
                            "form": [{"key": "闭单人:", "value": user_ids},
                                     {"key": "关闭时间:", "value": now_date}]})
            user_ids = get_ding_uids(ding_api, pks)
        instances = self.get_queryset().filter(id__in=pks)
        # 更新数据
        instances.update(**data)
        # 更新维护计划状态
        res = self.queryset.filter(Q(plan_id__in=instances.values_list('plan_id', flat=True)) & ~Q(status__in=['已完成', '已验收']))
        if not res.exists():
            EquipPlan.objects.filter(plan_id__in=instances.values_list('plan_id', flat=True)).update(status='计划已完成')
        # 更新报修申请状态
        EquipApplyRepair.objects.filter(plan_id__in=instances.values_list('plan_id', flat=True)).update(
            status=data.get('status'))
        # 发送数据
        if user_ids and isinstance(user_ids, list):
            for order_id in pks:
                new_content = copy.deepcopy(content)
                instance = self.queryset.filter(id=order_id).first()
                fault_name = instance.result_fault_cause if instance.result_fault_cause else (
                    instance.equip_repair_standard.standard_name if instance.equip_repair_standard else instance.equip_maintenance_standard.standard_name)
                new_content['form'] = [{"key": "工单编号:", "value": instance.work_order_no},
                                       {"key": "机台:", "value": instance.equip_no},
                                       {"key": "部位名称:",
                                        "value": instance.equip_part_new.part_name if instance.equip_part_new else ''},
                                       {"key": "故障原因:", "value": fault_name},
                                       {"key": "重要程度:", "value": instance.importance_level}] + new_content['form']
                ding_api.send_message(user_ids, new_content, order_id)
        return Response(f'{opera_type}操作成功')


@method_decorator([api_recorder], name='dispatch')
class EquipInspectionOrderViewSet(ModelViewSet):
    """
    list:设备维修工单列表
    """
    queryset = EquipInspectionOrder.objects.all().order_by('-id')
    serializer_class = EquipInspectionOrderSerializer
    permission_classes = (IsAuthenticated, PermissionClass({'view': ['view_equip_inspection_order', 'export_equip_inspection_order',
                                                                     'view_d_equip_apply_order', 'close_d_equip_apply_order'],
                                                            'add': ['close_equip_inspection_order', 'assign_equip_inspection_order',
                                                                    'receive_equip_inspection_order', 'charge_equip_inspection_order',
                                                                    'begin_equip_inspection_order', 'regulation_equip_inspection_order',
                                                                    'view_d_equip_apply_order'],
                                                            'change': ['handle_equip_inspection_order']}))
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipInspectionOrderFilter
    FILE_NAME = '设备巡检工单表'
    EXPORT_FIELDS_DICT = {
        "计划编号": "plan_id",
        "计划名称": "plan_name",
        '序号': 'inspection_line_no',
        '区域': 'area_name',
        '类别': 'type',
        "工单编号": "work_order_no",
        "机台": "equip_no",
        "巡检标准": "equip_repair_standard_name",
        "计划巡检日期": "planned_repair_date",
        "设备条件": "equip_condition",
        "重要程度": "importance_level",
        "状态": "status",
        "指派人": "assign_user",
        "指派时间": "assign_datetime",
        "被指派人": "assign_to_user",
        "接单人": "receiving_user",
        "接单时间": "receiving_datetime",
        "巡检人": "repair_user",
        "巡检开始时间": "repair_start_datetime",
        "巡检结束时间": "repair_end_datetime",
        "录入人": "created_username",
        "录入时间": "created_date"
    }

    def get_user(self, section, users=[]):  # 获取当前部门负责人下的所有人
        if section.in_charge_user:
            users += [section.in_charge_user.username]
        users += User.objects.filter(section=section).values_list('username', flat=True)
        for s in Section.objects.filter(parent_section=section):
            self.get_user(s, users)
        return users

    def get_assign_user_queryset(self, status, users):
        queryset_id = []
        queryset = EquipInspectionOrder.objects.filter(status=status).values('assign_to_user', 'id')
        for item in queryset:
            if item['assign_to_user'].split(',')[0] in users:
                queryset_id.append(item['id'])
        return EquipInspectionOrder.objects.filter(id__in=queryset_id) if queryset_id else None

    def get_queryset(self):
        my_order = self.request.query_params.get('my_order')
        status = self.request.query_params.get('status')
        orders_filter = self.request.query_params.get('orders_filter', 'false')  # 工单大厅只展示个人相关的单据
        searched = self.request.query_params.get('searched')
        user_name = self.request.user.username
        query_set = self.queryset
        if my_order == '1':
            if not status:
                if not searched:
                    # 判断当前用户是否是部门负责人，是的话可以看到所有执行中的单据
                    section = Section.objects.filter(in_charge_user=self.request.user).first()
                    if section:
                        users = self.get_user(section, users=[])
                    # if Section.objects.filter(name='设备科', in_charge_user=self.request.user).exists():
                        query_set = query_set.filter(
                            Q(Q(status='已接单', receiving_user__in=users) |
                              Q(status='已开始', repair_end_datetime__isnull=True, receiving_user__in=users)))
                    else:
                        query_set = query_set.filter(  # repair_user
                            Q(Q(status='已接单', repair_user__icontains=user_name) |
                              Q(status='已开始', repair_end_datetime__isnull=True, repair_user__icontains=user_name)))
                else:
                    query_set = query_set.filter(
                        Q(assign_to_user__icontains=user_name) | Q(receiving_user=user_name) |
                        Q(repair_user__icontains=user_name) | Q(status='已生成'))
            else:
                section = Section.objects.filter(in_charge_user=self.request.user).first()
                if section:
                    users = self.get_user(section, users=[])
                    query_set = query_set.filter(Q(status='已生成') |
                    Q(Q(status='已完成') & Q(receiving_user__in=users)) |
                    # Q(Q(status='已指派') & Q(assign_to_user__in=self.users)) |
                    Q(Q(status__in=['已接单', '已开始']) & Q(receiving_user__in=users)) |
                    Q(Q(status='已验收', receiving_user__in=users)))
                    queryset_assigned = self.get_assign_user_queryset('已指派', users)
                    if queryset_assigned:
                        query_set = query_set | queryset_assigned

                else:
                    query_set = query_set.filter(Q(status='已生成') | Q(Q(status=status) & Q(Q(assign_to_user__icontains=user_name) | Q(receiving_user=user_name) |
                                                 Q(repair_user__icontains=user_name))))
        elif my_order == '2':
            if orders_filter == 'true':
                query_set = query_set.filter(Q(assign_user__icontains=user_name) | Q(assign_to_user__icontains=user_name) |
                                             Q(receiving_user__icontains=user_name) | Q(repair_user__icontains=user_name) |
                                             Q(created_user__username__icontains=user_name))
            if not status and not searched:
                query_set = query_set.filter(Q(Q(status='已接单') | Q(status='已开始', repair_end_datetime__isnull=True)))
        return query_set

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        my_order = self.request.query_params.get('my_order')
        orders_filter = self.request.query_params.get('orders_filter', 'false')  # 工单大厅只展示个人相关的单据
        user_name = self.request.user.username
        if self.request.query_params.get('export'):
            data = EquipInspectionOrderSerializer(self.filter_queryset(self.get_queryset()), many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        # 小程序获取数量 带指派 带接单 进行中 已完成 已验收
        if my_order == '1':
            user_name = self.request.user.username
            wait_assign = self.queryset.filter(status='已生成').count()
            section = Section.objects.filter(in_charge_user=self.request.user).first()
            if section:
                users = self.get_user(section, users=[])
                queryset_assigned = self.get_assign_user_queryset('已指派', users)
                assigned = queryset_assigned.count() if queryset_assigned else 0

            # if Section.objects.filter(name='设备科', in_charge_user=self.request.user).exists():
                processing = self.queryset.filter(Q(
                                                    Q(status='已接单', receiving_user__in=users) |
                                                    Q(status='已开始', repair_end_datetime__isnull=True, receiving_user__in=users))).count()
                finished = self.queryset.filter(Q(status='已完成', receiving_user__in=users)).count()

            else:
                processing = self.queryset.filter(Q(Q(status='已接单', repair_user__icontains=user_name) |
                                                    Q(status='已开始', repair_end_datetime__isnull=True,
                                                      repair_user__icontains=user_name))).count()
                assigned = self.queryset.filter(status='已指派', assign_to_user__icontains=user_name).count()
                finished = self.queryset.filter(Q(Q(status='已完成') & Q(Q(repair_user__icontains=user_name) | Q(assign_user=user_name)))).count()
        else:
            query_set = self.queryset
            if orders_filter == 'true':
                query_set = query_set.filter(
                    Q(assign_user__icontains=user_name) | Q(assign_to_user__icontains=user_name) |
                    Q(receiving_user__icontains=user_name) | Q(repair_user__icontains=user_name) |
                    Q(created_user__username__icontains=user_name))
            wait_assign = query_set.filter(status='已生成').count()
            assigned = query_set.filter(status='已指派').count()
            processing = query_set.filter(Q(Q(status='已接单') |
                                                Q(status='已开始', repair_end_datetime__isnull=True))).count()
            finished = query_set.filter(status='已完成').count()
        data = {'wait_assign': wait_assign, 'assigned': assigned, 'processing': processing, 'finished': finished}
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            for item in serializer.data:
                item.update(data)
            response = self.get_paginated_response(serializer.data)
            response.data.update({'index': data})
            return response

        serializer = self.get_serializer(queryset, many=True)
        for item in serializer.data:
            item.update(data)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # 增减巡检人员
        if self.request.data.get('order_id'):
            data = self.request.data
            users = '，'.join(data.get('users'))
            # 记录到增减人员履历中
            obj = self.queryset.filter(id=data.get('order_id')).first()
            new_users = data.get('users')
            actual_users = EquipRegulationRecord.objects.filter(plan_id=obj.plan_id, status='增').values_list('user', flat=True)
            #  新增的
            add_user = list(set(new_users).difference(set(actual_users)))
            # 要删除的
            del_user = list(set(actual_users).difference(set(new_users)))
            for user in add_user:  # 增加人员
                regulation = EquipRegulationRecord.objects.filter(plan_id=obj.plan_id, status='减', user=user)
                if obj.status == '已接单':
                    if regulation.exists():
                        regulation.update(status='增')
                    elif not regulation.exists():
                        EquipRegulationRecord.objects.create(plan_id=obj.plan_id, status='增', user=user)
                elif obj.status == '已开始':
                    if regulation.exists():
                        regulation.update(begin_time=datetime.now(), status='增', end_time=None)
                    elif not regulation.exists():
                        EquipRegulationRecord.objects.create(plan_id=obj.plan_id, status='增', user=user, begin_time=datetime.now())
            for user in del_user:  # 删除人员     没有     增的有
                regulation = EquipRegulationRecord.objects.filter(plan_id=obj.plan_id, status='增', user=user)
                if obj.status == '已接单':
                    if regulation.exists():
                        regulation.update(status='减')
                elif obj.status == '已开始':
                    if regulation.exists():
                        use_time = regulation.first().use_time + float('%.2f' % ((datetime.now() - regulation.first().begin_time).total_seconds() / 60))
                        regulation.update(status='减', end_time=datetime.now(), use_time=use_time)
            # 不变的
            # list(set(actual_users).intersection(set(new_users)))
            self.queryset.filter(id=data.get('order_id')).update(repair_user=users)
            return Response('修改完成')
        return super().create(request, *args, **kwargs)

    @atomic
    @action(methods=['post'], detail=False, url_name='temporary_save', url_path='temporary_save')
    def temporary_save(self, request):
        data = copy.deepcopy(self.request.data)
        work_content = data.pop('work_content', [])
        work_order_no = data.pop('work_order_no')

        # 更新作业内容
        result_standard = data.get('equip_repair_standard')
        instance = EquipMaintenanceStandard.objects.filter(id=result_standard).first()
        if instance:
            for item in work_content:
                uid = item.pop('uid', None)
                kwargs = {
                    'abnormal_operation_desc': item.get('abnormal_operation_desc'),
                    'abnormal_operation_result': item.get('abnormal_operation_result'),
                    'equip_jobitem_standard_id': item.get('equip_jobitem_standard_id'),
                    'job_item_check_standard': item.get('job_item_check_standard'),
                    'job_item_check_type': item.get('job_item_check_type'),
                    'job_item_content': item.get('job_item_content'),
                    'job_item_sequence': item.get('job_item_sequence'),
                    'operation_result': item.get('operation_result'),
                    'unit': item.get('unit'),
                    'abnormal_operation_url': None,
                    'is_save': True if item.get('is_save', None) else False
                }
                if item.get('abnormal_operation_url'):
                    kwargs['abnormal_operation_url'] = json.dumps(item['abnormal_operation_url'])
                kwargs.update({'work_type': '巡检', 'work_order_no': work_order_no})
                if uid:  # 更新
                    EquipResultDetail.objects.filter(id=uid).update(**kwargs)
                else:  # 新增
                    EquipResultDetail.objects.create(**kwargs)
        return Response('操作成功')


    @atomic
    @action(methods=['post'], detail=False, url_name='multi_update', url_path='multi_update')
    def multi_update(self, request):
        data = copy.deepcopy(self.request.data)
        pks = data.pop('pks')
        opera_type = data.pop('opera_type')
        user_ids = self.request.user.username
        ding_api = DinDinAPI()
        now_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        plan_ids = self.get_queryset().filter(id__in=pks).values_list('plan_id', flat=True)
        content = {}
        if opera_type == '指派':
            assign_num = EquipInspectionOrder.objects.filter(~Q(status='已生成'), id__in=pks).count()
            if assign_num != 0:
                raise ValidationError('存在非已生成的订单, 请刷新订单!')
            assign_to_user = data.get('assign_to_user')
            if not assign_to_user:
                raise ValidationError('未选择被指派人')
            data = {
                'status': data.get('status'), 'assign_to_user': ','.join(assign_to_user), 'assign_user': user_ids,
                'assign_datetime': now_date, 'last_updated_date': datetime.now()
            }
            content.update({"title": "您有新的设备巡检单到达，请尽快处理！",
                            "form": [{"key": "指派人:", "value": self.request.user.username},
                                     {"key": "指派时间:", "value": now_date}]})
            user_ids = get_ding_uids(ding_api, names=assign_to_user)
        elif opera_type == '接单':
            assign_to_num = EquipInspectionOrder.objects.filter(~Q(status='已指派'), id__in=pks).count()
            if assign_to_num != 0:
                raise ValidationError('存在未被指派的订单, 请刷新订单!')
            data = {
                'status': data.get('status'), 'receiving_user': user_ids, 'repair_user': user_ids, 'receiving_datetime': now_date,
                'last_updated_date': datetime.now(), 'timeout_color': None
            }
            # 记录到增减人员履历中
            for plan_id in plan_ids:
                EquipRegulationRecord.objects.create(user=user_ids, plan_id=plan_id, status='增')
            content.update({"title": f"您指派的设备巡检单已被{user_ids}接单",
                            "form": [{"key": "接单人:", "value": user_ids},
                                     {"key": "接单时间:", "value": now_date}]})
            user_ids = get_ding_uids(ding_api, pks, check_type='巡检')
        elif opera_type == '退单':
            receive_num = EquipInspectionOrder.objects.filter(~Q(status='已指派'), id__in=pks).count()
            if receive_num != 0:
                raise ValidationError('未指派订单无法退单, 请刷新订单!')
            data = {
                'status': data.get('status'), 'receiving_user': None, 'receiving_datetime': None,
                'assign_user': None, 'assign_datetime': None, 'timeout_color': None, 'back_order': True,
                'assign_to_user': None, 'last_updated_date': datetime.now(), 'back_reason': data.get('back_reason')
            }
            content.update({"title": f"您指派的设备巡检单已被{user_ids}退单",
                            "form": [{"key": "退单人:", "value": user_ids},
                                     {"key": "退单时间:", "value": now_date}]})
            user_ids = get_ding_uids(ding_api, pks, check_type='巡检')
        elif opera_type == '开始':
            receive_num = EquipInspectionOrder.objects.filter(~Q(status='已接单'), id__in=pks).count()
            if receive_num != 0:
                raise ValidationError('订单未被接单, 请刷新订单!')
            data = {
                'status': data.get('status'), 'repair_start_datetime': now_date,
                'last_updated_date': datetime.now(), 'timeout_color': None
            }
            # 记录到增减人员履历中
            for plan_id in plan_ids:
                EquipRegulationRecord.objects.filter(plan_id=plan_id).update(begin_time=datetime.now())
            # 更新维护计划状态
            equip_plan = EquipInspectionOrder.objects.filter(id__in=pks).values_list('plan_id', flat=True)
            EquipPlan.objects.filter(plan_id__in=equip_plan).update(status='计划执行中')
        elif opera_type == '处理':
            repair_num = EquipInspectionOrder.objects.filter(~Q(status='已开始'), id__in=pks).count()
            if repair_num != 0:
                raise ValidationError('未开始订单无法进行处理操作, 请刷新订单!')
            work_content = data.pop('work_content', [])
            image_url_list = data.pop('image_url_list', [])
            video_url_list = data.pop('video_url_list', [])
            work_order_no = data.pop('work_order_no')
            result = data.get('result_repair_final_result')
            data.update({'repair_end_datetime': now_date if result == '正常' else None,
                         'last_updated_date': datetime.now(), 'result_repair_video_url': json.dumps(video_url_list),
                         'status': '已完成' if result == '正常' else '已开始',
                         'result_repair_graph_url': json.dumps(image_url_list)})
            # 记录到增减人员履历中
            for plan_id in plan_ids:
                queryset = EquipRegulationRecord.objects.filter(plan_id=plan_id, status='增')
                for obj in queryset:
                    obj.end_time = datetime.now()
                    obj.use_time += float('%.2f' %((datetime.now() - obj.begin_time).total_seconds() / 60))
                    obj.save()
            # 更新作业内容
            result_standard = data.get('equip_repair_standard')
            instance = EquipMaintenanceStandard.objects.filter(id=result_standard).first()
            if instance:
                # EquipResultDetail.objects.filter(work_order_no=work_order_no).delete()
                for item in work_content:
                    uid = item.pop('uid', None)
                    kwargs = {
                        'abnormal_operation_desc': item.get('abnormal_operation_desc'),
                        'abnormal_operation_result': item.get('abnormal_operation_result'),
                        'equip_jobitem_standard_id': item.get('equip_jobitem_standard_id'),
                        'job_item_check_standard': item.get('job_item_check_standard'),
                        'job_item_check_type': item.get('job_item_check_type'),
                        'job_item_content': item.get('job_item_content'),
                        'job_item_sequence': item.get('job_item_sequence'),
                        'operation_result': item.get('operation_result'),
                        'unit': item.get('unit'),
                        'abnormal_operation_url': None,
                        'is_save': True if item.get('is_save', None) else False
                    }
                    if item.get('abnormal_operation_url'):
                        kwargs['abnormal_operation_url'] = json.dumps(item['abnormal_operation_url'])
                    kwargs.update({'work_type': '巡检', 'work_order_no': work_order_no})
                    if uid:  # 更新
                        EquipResultDetail.objects.filter(id=uid).update(**kwargs)
                    else:  # 新增
                        EquipResultDetail.objects.create(**kwargs)
        else:  # 关闭
            accept_num = EquipInspectionOrder.objects.filter(status='已关闭', id__in=pks).count()
            if accept_num != 0:
                raise ValidationError('存在已经关闭的订单, 请刷新订单!')
            data = {'status': data.get('status'), 'last_updated_date': datetime.now(), 'timeout_color': None,
                    'close_reason': data.get('close_reason')}
            content.update({"title": f"您指派的设备维修单已被{user_ids}关闭",
                            "form": [{"key": "闭单人:", "value": user_ids},
                                     {"key": "关闭时间:", "value": now_date}]})
            user_ids = get_ding_uids(ding_api, pks, check_type='巡检')
        # 更新数据
        instances = self.get_queryset().filter(id__in=pks)
        instances.update(**data)
        # 更新维护计划状态
        res = self.queryset.filter(Q(plan_id__in=instances.values_list('plan_id', flat=True)) & ~Q(status__in=['已完成', '已验收']))
        if not res.exists():
            EquipPlan.objects.filter(plan_id__in=instances.values_list('plan_id', flat=True)).update(status='计划已完成')
        # 发送数据
        if user_ids and isinstance(user_ids, list):
            for order_id in pks:
                new_content = copy.deepcopy(content)
                instance = self.queryset.filter(id=order_id).first()
                fault_name = instance.equip_repair_standard.standard_name if instance.equip_repair_standard else ''
                new_content['form'] = [{"key": "工单编号:", "value": instance.work_order_no},
                                       {"key": "机台:", "value": instance.equip_no},
                                       {"key": "巡检标准:", "value": fault_name},
                                       {"key": "重要程度:", "value": instance.importance_level}] + new_content['form']
                ding_api.send_message(user_ids, new_content, order_id, inspection=True)
        return Response(f'{opera_type}操作成功')


@method_decorator([api_recorder], name='dispatch')
class EquipRepairMaterialReqViewSet(ModelViewSet):
    """
    申请维修物料
    """
    queryset = EquipRepairMaterialReq.objects.all()
    serializer_class = EquipRepairMaterialReqSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)

    def get_queryset(self):
        warehouse_out_no = self.request.query_params.get('warehouse_out_no')
        query_set = self.queryset.filter(warehouse_out_no=warehouse_out_no)
        return query_set


@method_decorator([api_recorder], name='dispatch')
class UploadImageViewSet(ModelViewSet):
    """
    create:上传图片
    """
    queryset = UploadImage.objects.all()
    serializer_class = UploadImageSerializer
    filter_backends = (DjangoFilterBackend,)


@method_decorator([api_recorder], name='dispatch')
class GetStaffsView(APIView):
    """
    获取维修/巡检员工信息
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        ding_api = DinDinAPI()
        equip_no = self.request.query_params.get('equip_no')
        maintenance_type = self.request.query_params.get('maintenance_type', '通用')
        have_classes = self.request.query_params.get('have_classes')
        if not equip_no:
            section_name = self.request.query_params.get('section_name')
            if not section_name:
                instance = GlobalCode.objects.filter(global_type__type_name='设备部门组织名称', use_flag=1,
                                                     global_type__use_flag=1).first()
                if not instance:
                    return Response({'results': []})
                else:
                    section_name = instance.global_name
            if not have_classes:
                now_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                classes = '早班' if '08:00:00' < now_date[11:] < '20:00:00' else '夜班'
                record = WorkSchedulePlan.objects.filter(plan_schedule__day_time=now_date[:10], classes__global_name=classes,
                                                         plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
                group = record.group.global_name
                # 查询各员工考勤状态
                result = get_staff_status(ding_api, section_name, group)
            else:
                # 查询各员工考勤状态
                result = get_staff_status(ding_api, section_name)
        else:
            result = get_maintenance_status(ding_api, equip_no, maintenance_type)
        return Response({'results': result})


@method_decorator([api_recorder], name='dispatch')
class EquipCodePrintView(APIView):
    def post(self, request):
        res = GlobalCode.objects.filter(global_type__type_name='条码打印').first()
        if not res:
            raise ValidationError('请在公共代码添加条码打印类型')
        if len(res.global_name.split('.')) != 4:
            raise ValidationError('ip格式有误')
        url = {'code1': f'http://{res.global_name}:6111/printer/print-storehouse/',
               'code2': f'http://{res.global_name}:6111/printer/print-spareparts/',
               'code3': f'http://{res.global_name}:6111/printer/print-equip/',
               'code4': f'http://{res.global_name}:6111/printer/print-label/',
               }
        status = self.request.data.get('status')
        lot_no = self.request.data.get('lot_no', None)
        data = self.request.data

        try:
            if status == 1:  # 打印库位条码
                del data['status']
                res = requests.post(url=url.get('code1'), json=data, verify=False, timeout=10)
            if status == 2:  # 打印备件条码
                data = {"print_type":1,
                        "code": data.get('spare_code'),
                        "name": data.get('spare_name'),
                        "technical_params": data.get('technical_params'),
                        "barcode": data.get('spare_code')
                        }
                res = requests.post(url=url.get('code2'), json=data, verify=False, timeout=10)
            if status == 3:  # 打印bom条码
                obj = EquipBom.objects.filter(node_id=lot_no).first()
                if not obj:
                    raise ValidationError('节点编号不存在, 无法打印')
                code_type = len(lot_no.split('-'))  #  1=机台，2=部位，3=部件
                data = {
                        "print_type": code_type,
                        "property_type_node": obj.property_type.global_name if obj.property_type else None,
                        "equip_no": obj.equip_info.equip_no if obj.equip_info else None,
                        "equip_name": obj.equip_info.equip_name if obj.equip_info else None,
                        "equip_type": obj.equip_info.category.category_name if obj.equip_info else None,
                        "part_code": obj.part.part_code if obj.part else None,
                        "part_name": obj.part.part_name if obj.part else None,
                        "component_code": obj.component.component_code if obj.component else None,
                        "component_name": obj.component.component_name if obj.component else None,
                        "component_type": obj.component.equip_component_type.component_type_name if obj.component else None,
                        "node_id": lot_no}
                res = requests.post(url=url.get('code3'), json=data, verify=False, timeout=10)
            if status == 4:  # 巡检点标签打印
                data = {
                    "print_type": 1,
                    "area_code": data.get('area_code'),
                    "area_name": data.get('area_name'),
                    "part_name": data.get('part_name'),
                    "component_name": data.get('component_name'),
                    "lot_no": data.get('lot_no'),
                }
                res = requests.post(url=url.get('code4'), json=data, verify=False, timeout=10)
        except:
            raise ValidationError('打印超时，请检查您的网络或ip配置')
        return Response({'results': res.text})


@method_decorator([api_recorder], name='dispatch')
class EquipPlanViewSet(ModelViewSet):
    queryset = EquipPlan.objects.filter(delete_flag=False).order_by('-id')
    serializer_class = EquipPlanSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipPlanFilter
    FILE_NAME = '设别维护维修计划'
    EXPORT_FIELDS_DICT = {
        "作业类型": "work_type",
        "计划编号": "plan_id",
        "计划名称": "plan_name",
        "类别": "type",
        "机台": "equip_name",
        "维护标准": "standard",
        "设备条件": "equip_condition",
        "重要程度": "importance_level",
        "来源": "plan_source",
        "状态": "status",
        "计划维护日期": "planned_maintenance_date",
        "下次维护日期": "next_maintenance_date",
        "创建人": "created_username",
        "创建时间": "created_date",
    }

    def list(self, request, *args, **kwargs):
        if self.request.query_params.get('export'):
            data = self.get_serializer(self.filter_queryset(self.get_queryset()), many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        return super().list(request, *args, **kwargs)

    @action(methods=['post'], detail=False, permission_classes=[IsAuthenticated],
                url_path='close-plan', url_name='close-plan')
    def close_plan(self, request, pk=None):
        """关闭计划"""
        ids = self.request.data.get('plan_ids')
        for i in ids:
            self.queryset.filter(id=i).update(delete_flag=True)
        return Response('计划以关闭')

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated],
                url_path='get-plan-name', url_name='get-plan-name')
    def get_plan_name(self, request):
        if self.request.query_params.get('work_type'):
            kwargs = {
                '巡检': 'XJ',
                '保养': 'BY',
                '润滑': 'RH',
                '标定': 'BD',
                '维修': 'BX',
            }
            work_type = self.request.query_params.get('work_type')
            dic = EquipPlan.objects.filter(work_type=work_type, created_date__date=dt.date.today()).aggregate(
                Max('plan_id'))
            res = dic.get('plan_id__max')
            if res:
                plan_id = res[:10] + str('%04d' % (int(res[-4:]) + 1))
            else:
                plan_id = f'{kwargs.get(work_type)}{dt.date.today().strftime("%Y%m%d")}0001'
            return Response({'plan_name': f'{work_type}{plan_id}'})

    # 生成设备维修工单
    @atomic
    @action(methods=['post'], detail=False, permission_classes=[IsAuthenticated],
            url_path='generate-order', url_name='generate-order')
    def generate_order(self, request, *args, **kwargs):
        data = self.request.data
        results = []
        for i in data.get('ids'):
            plan = EquipPlan.objects.filter(id=i).first()
            equip_no = plan.equip_no
            equip_list = equip_no.split('，')
            if plan.work_type == '巡检':
                # if EquipInspectionOrder.objects.filter(plan_id=plan.plan_id).count() == len(equip_list):
                if EquipInspectionOrder.objects.filter(plan_id=plan.plan_id).exists():
                    raise ValidationError('工单已生成')
                for equip in equip_list:
                    work = list(EquipMaintenanceStandardWork.objects.filter(
                        equip_maintenance_standard=plan.equip_manintenance_standard).order_by('id'))
                    for work_detail in work:
                        max_order_code = EquipInspectionOrder.objects.filter(work_order_no__startswith=plan.plan_id).aggregate(
                            max_order_code=Max('work_order_no'))['max_order_code']
                        work_order_no = plan.plan_id + '-' + (
                            '%04d' % (int(max_order_code.split('-')[-1]) + 1) if max_order_code else '0001')
                        res = EquipInspectionOrder.objects.create(plan_id=plan.plan_id,
                                                                  plan_name=plan.plan_name,
                                                                  work_type=plan.work_type,
                                                                  work_order_no=work_order_no,
                                                                  equip_no=equip,
                                                                  equip_repair_standard=plan.equip_manintenance_standard,
                                                                  planned_repair_date=plan.planned_maintenance_date,
                                                                  status='已生成',
                                                                  equip_condition=plan.equip_condition,
                                                                  importance_level=plan.importance_level,
                                                                  created_user=self.request.user,
                                                                  equip_maintenance_standard_work=work_detail,
                                                                  inspection_line_no=work.index(work_detail) + 1
                                                                  )
                        results.append(res.id)
            else:
                if EquipApplyOrder.objects.filter(plan_id=plan.plan_id).count() == len(equip_list):
                    raise ValidationError('工单已生成')
                for equip in equip_list:
                    max_order_code = EquipApplyOrder.objects.filter(work_order_no__startswith=plan.plan_id).aggregate(
                        max_order_code=Max('work_order_no'))['max_order_code']
                    work_order_no = plan.plan_id + '-' + (
                        '%04d' % (int(max_order_code.split('-')[-1]) + 1) if max_order_code else '0001')
                    if plan.work_type == '维修':
                        equip_repair_standard = plan.equip_repair_standard
                        equip_manintenance_standard = None
                    else:
                        equip_repair_standard = None
                        equip_manintenance_standard = plan.equip_manintenance_standard
                    res = EquipApplyOrder.objects.create(plan_id=plan.plan_id,
                                                         plan_name=plan.plan_name,
                                                         work_type=plan.work_type,
                                                         work_order_no=work_order_no,
                                                         equip_no=equip,
                                                         equip_maintenance_standard=equip_manintenance_standard,
                                                         equip_repair_standard=equip_repair_standard,
                                                         planned_repair_date=plan.planned_maintenance_date,
                                                         status='已生成',
                                                         equip_condition=plan.equip_condition,
                                                         importance_level=plan.importance_level,
                                                         created_user=self.request.user)
                    results.append(res.id)
            plan.status = '已生成工单'
            plan.save()
        return Response(results)


@method_decorator([api_recorder], name='dispatch')
class EquipOrderListView(APIView):
    """
    根据机台和部位条码进行查询
    """

    def get(self, request):
        lot_no = self.request.query_params.get('lot_no')  # 扫描的条码
        search = self.request.query_params.get('search')
        my_order = self.request.query_params.get('my_order')
        accept_flag = self.request.query_params.get('accept_flag')
        page = self.request.query_params.get('page', 1)
        page_size = self.request.query_params.get('page_size', 10)
        user_name = self.request.user.username
        if accept_flag:
            if lot_no:
                queryset = EquipApplyOrder.objects.filter(Q(equip_part_new__part_code=lot_no) | Q(equip_no=lot_no),
                                                          Q(created_user__username=user_name) | Q(accept_user=user_name),
                                                          status__in=['已完成', '已验收'])
            else:
                queryset = EquipApplyOrder.objects.filter(Q(equip_part_new__part_code__icontains=search) |
                                                          Q(equip_no__icontains=search),
                                                          Q(created_user__username=user_name) | Q(accept_user=user_name),
                                                          status__in=['已完成', '已验收'])
            serializer = EquipApplyOrderSerializer(instance=queryset, many=True, context={'request': request}).data
        else:
            if lot_no:
                queryset1 = EquipApplyOrder.objects.filter(Q(equip_part_new__part_code=lot_no) | Q(equip_no=lot_no))
                queryset2 = EquipInspectionOrder.objects.filter(equip_no=lot_no)
            else:
                queryset1 = EquipApplyOrder.objects.filter(Q(equip_part_new__part_code__icontains=search) |
                                                           Q(equip_no__icontains=search))
                queryset2 = EquipInspectionOrder.objects.filter(equip_no__icontains=search)
            if my_order:
                queryset1 = queryset1.filter(Q(assign_user=user_name) | Q(assign_to_user=user_name) | Q(status='已生成') |
                                             Q(receiving_user=user_name) | Q(accept_user=user_name))
                queryset2 = queryset2.filter(Q(assign_user=user_name) | Q(assign_to_user=user_name) | Q(status='已生成') |
                                             Q(receiving_user=user_name))

            serializer1 = EquipApplyOrderSerializer(instance=queryset1, many=True, context={'request': request}).data
            serializer2 = EquipInspectionOrderSerializer(instance=queryset2, many=True, context={'request': request}).data
            serializer = serializer1 + serializer2
        st = (int(page) - 1) * int(page_size)
        et = int(page) * int(page_size)
        data = sorted(serializer, key=lambda x: x['created_date'], reverse=True)
        return Response({'results': data[st:et], 'count': len(data)})


@method_decorator([api_recorder], name='dispatch')
class EquipMTBFMTTPStatementView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_month_range(self, start_day, end_day):
        months = (end_day.year - start_day.year) * 12 + end_day.month - start_day.month
        month_range = ['%s年%s月' % (start_day.year + mon // 12, mon % 12 + 1)
                       for mon in range(start_day.month - 1, start_day.month + months)]
        return month_range

    def get(self, request):
        # 统计自然日生产时间
        s_time = self.request.query_params.get('s_time', None)  # 2021-12
        equip_list = [f'Z{"%.2d" % i}' for i in range(1, 16)]
        year = s_time.split('-')[0]
        month = s_time.split('-')[-1]
        if month == '01':
            begin_time = year + '-01-01'
            end_time = year + '-12-31'
        else:
            begin_time = s_time + '-01'
            day = calendar._monthlen(int(year) + 1, int(month) - 1)
            end_time = f"{ int(year) + 1}-{int(month) - 1}-{day}"
        time_range = [begin_time, end_time]
        time_list = self.get_month_range(dt.datetime.strptime(begin_time, '%Y-%m-%d'),
                                         dt.datetime.strptime(end_time, '%Y-%m-%d'))
        dic = {}
        for i in range(15):
            dic[equip_list[i] + '1'] = {'equip_no': equip_list[i], 'content': '理论生产总时间(h)', time_list[0]: None, time_list[1]: None, time_list[2]: None, time_list[3]: None, time_list[4]: None, time_list[5]: None, time_list[6]: None, time_list[7]: None, time_list[8]: None, time_list[9]: None, time_list[10]: None, time_list[11]: None}
            dic[equip_list[i] + '2'] = {'equip_no': equip_list[i], 'content': '故障时间(h)', time_list[0]: None, time_list[1]: None, time_list[2]: None, time_list[3]: None, time_list[4]: None, time_list[5]: None, time_list[6]: None, time_list[7]: None, time_list[8]: None, time_list[9]: None, time_list[10]: None, time_list[11]: None}
            dic[equip_list[i] + '3'] = {'equip_no': equip_list[i], 'content': '故障次数', time_list[0]: None, time_list[1]: None, time_list[2]: None, time_list[3]: None, time_list[4]: None, time_list[5]: None, time_list[6]: None, time_list[7]: None, time_list[8]: None, time_list[9]: None, time_list[10]: None, time_list[11]: None}
            dic[equip_list[i] + '4'] = {'equip_no': equip_list[i], 'content': 'MTBF', time_list[0]: None, time_list[1]: None, time_list[2]: None, time_list[3]: None, time_list[4]: None, time_list[5]: None, time_list[6]: None, time_list[7]: None, time_list[8]: None, time_list[9]: None, time_list[10]: None, time_list[11]: None}
            dic[equip_list[i] + '5'] = {'equip_no': equip_list[i], 'content': 'MTTR', time_list[0]: None, time_list[1]: None, time_list[2]: None, time_list[3]: None, time_list[4]: None, time_list[5]: None, time_list[6]: None, time_list[7]: None, time_list[8]: None, time_list[9]: None, time_list[10]: None, time_list[11]: None}
            dic[equip_list[i] + '6'] = {'equip_no': equip_list[i], 'content': '故障率', time_list[0]: None, time_list[1]: None, time_list[2]: None, time_list[3]: None, time_list[4]: None, time_list[5]: None, time_list[6]: None, time_list[7]: None, time_list[8]: None, time_list[9]: None, time_list[10]: None, time_list[11]: None}

        # 统计机台的故障用时
        # 已完成
        queryset = EquipApplyOrder.objects.filter(repair_start_datetime__date__range=time_range, status__in=['已完成', '已验收'], equip_condition='停机', equip_no__in=equip_list)
        query = queryset.annotate(month=TruncMonth('fault_datetime')).values('fault_datetime__year',
                                                                                    'fault_datetime__month',
                                                                                    'equip_no').annotate(
            time=OSum((F('repair_end_datetime') - F('fault_datetime'))), count=Count('id'))

        for item in query:
            #  当前月总时长
            total_time = calendar.monthrange(item["fault_datetime__year"], item["fault_datetime__month"])[1] * 24
            year_month = f'{item["fault_datetime__year"]}年{item["fault_datetime__month"]}月'
            if item['equip_no'] in equip_list:
                dic[item['equip_no'] + '1'][year_month] = total_time
                dic[item['equip_no'] + '2'][year_month] = round(item['time'].total_seconds() / 3600, 2),
                dic[item['equip_no'] + '3'][year_month] = item['count']
                dic[item['equip_no'] + '4'][year_month] = total_time / item['count']
                dic[item['equip_no'] + '5'][year_month] = round((item['time'].total_seconds() / 3600) / item['count'], 2)
                dic[item['equip_no'] + '6'][year_month] = round((item['time'].total_seconds()) / 3600 / total_time, 2)
        return Response(dic.values())


@method_decorator([api_recorder], name='dispatch')
class EquipWorkOrderStatementView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        s_time = self.request.query_params.get('s_time')
        e_time = self.request.query_params.get('e_time')
        plan_id = self.request.query_params.get('plan_id', '')
        work_order_no = self.request.query_params.get('work_order_no', '')
        work_type = self.request.query_params.get('work_type', '')
        time_range = {}
        if s_time:
            time_range = {'created_date__range': [s_time, e_time]}
        kwargs = {
            'plan_id__icontains': plan_id,
            'work_order_no__icontains': work_order_no,
            'work_type__icontains': work_type
        }
        queryset1 = EquipApplyOrder.objects.filter(**kwargs, **time_range, status='已验收').values('plan_id').annotate(
            派单时间=OSum(F('assign_datetime') - F('created_date')),
            接单时间=OSum(F('receiving_datetime') - F('assign_datetime')),
            维修时间=OSum(F('repair_end_datetime') - F('repair_start_datetime')),
            验收时间=OSum(F('accept_datetime') - F('repair_end_datetime'))
        ).values('plan_id', 'plan_name', 'work_order_no', 'work_type', '派单时间', '接单时间', '维修时间', '验收时间')
        queryset2 = EquipInspectionOrder.objects.filter(**kwargs, **time_range, status='已完成').values('plan_id').annotate(
            派单时间=OSum(F('assign_datetime') - F('created_date')),
            接单时间=OSum(F('receiving_datetime') - F('assign_datetime')),
            维修时间=OSum(F('repair_end_datetime') - F('repair_start_datetime')),
            验收时间=OSum(F('repair_end_datetime') - F('repair_end_datetime'))
        ).values('plan_id', 'plan_name', 'work_order_no', 'work_type', '派单时间', '接单时间', '维修时间', '验收时间')

        queryset = chain(queryset1, queryset2)

        res = [{
            'plan_id': item['plan_id'],
            'plan_name': item['plan_name'],
            'work_order_no': item['work_order_no'],
            'work_type': item['work_type'],
            '派单时间': round(item['派单时间'].total_seconds() / 60, 2),
            '接单时间': round(item['接单时间'].total_seconds() / 60, 2),
            '维修时间': round(item['维修时间'].total_seconds() / 60, 2),
            '验收时间': round(item['验收时间'].total_seconds() / 60, 2),
        } for item in queryset]
        return Response(res)


@method_decorator([api_recorder], name='dispatch')
class EquipStatementView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        s_time = self.request.query_params.get('s_time')
        e_time = self.request.query_params.get('e_time')
        equip_no = self.request.query_params.get('equip_no', '')
        work_type = self.request.query_params.get('work_type', '')
        time_range = {}
        if s_time:
            time_range = {'created_date__range': [s_time, e_time]}
        queryset1 = EquipApplyOrder.objects.filter(**time_range, status='已验收', equip_condition='停机', equip_no__icontains=equip_no, work_type__icontains=work_type)
        data1 = queryset1.values('equip_no', 'work_type').annotate(
            派单时间=OSum(F('assign_datetime') - F('created_date')),
            接单时间=OSum(F('receiving_datetime') - F('assign_datetime')),
            维修时间=OSum(F('repair_end_datetime') - F('repair_start_datetime')),
            验收时间=OSum(F('accept_datetime') - F('repair_end_datetime')),
            count=Count('id'),
        ).values('equip_no', 'work_type', '派单时间', '接单时间', '维修时间', '验收时间', 'count')
        queryset2 = EquipInspectionOrder.objects.filter(**time_range, status='已完成', equip_condition='停机', equip_no__icontains=equip_no,  work_type__icontains=work_type)
        data2 = queryset2.values('equip_no', 'work_type').annotate(
            派单时间=OSum(F('assign_datetime') - F('created_date')),
            接单时间=OSum(F('receiving_datetime') - F('assign_datetime')),
            维修时间=OSum(F('repair_end_datetime') - F('repair_start_datetime')),
            验收时间=OSum(F('repair_end_datetime') - F('repair_end_datetime')),
            count=Count('id')
        ).values('equip_no', 'work_type', '派单时间', '接单时间', '维修时间', '验收时间', 'count')
        queryset = chain(data1, data2)

        res = [{
            'equip_no': item['equip_no'],
            'work_type': item['work_type'],
            '派单时间': round(item['派单时间'].total_seconds() / item['count'] / 60, 2),
            '接单时间': round(item['接单时间'].total_seconds() / item['count'] / 60, 2),
            '维修时间': round(item['维修时间'].total_seconds() / item['count'] / 60, 2),
            '验收时间': round(item['验收时间'].total_seconds() / item['count'] / 60, 2),
        } for item in queryset]
        return Response(res)


@method_decorator([api_recorder], name='dispatch')
class EquipUserStatementView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        s_time = self.request.query_params.get('s_time')
        e_time = self.request.query_params.get('e_time')
        username = self.request.query_params.get('username', '')
        work_type = self.request.query_params.get('work_type', '')
        time_range = {}
        if s_time:
            time_range = {'created_date__range': [s_time, e_time]}
        queryset1 = EquipApplyOrder.objects.filter(**time_range, status='已验收', receiving_user__icontains=username, work_type__icontains=work_type)
        data1 = queryset1.values('receiving_user', 'work_type').annotate(
            派单时间=OSum(F('assign_datetime') - F('created_date')),
            接单时间=OSum(F('receiving_datetime') - F('assign_datetime')),
            维修时间=OSum(F('repair_end_datetime') - F('repair_start_datetime')),
            验收时间=OSum(F('accept_datetime') - F('repair_end_datetime')),
            count=Count('id')
        ).values('receiving_user', 'work_type', '派单时间', '接单时间', '维修时间', '验收时间', 'count')
        queryset2 = EquipInspectionOrder.objects.filter(**time_range, status='已完成', receiving_user__icontains=username, work_type__icontains=work_type)

        data2 = queryset2.values('receiving_user', 'work_type').annotate(
            派单时间=OSum(F('assign_datetime') - F('created_date')),
            接单时间=OSum(F('receiving_datetime') - F('assign_datetime')),
            维修时间=OSum(F('repair_end_datetime') - F('repair_start_datetime')),
            验收时间=OSum(F('repair_end_datetime') - F('repair_end_datetime')),
            count=Count('id')
        ).values('receiving_user', 'work_type', '派单时间', '接单时间', '维修时间', '验收时间', 'count')
        queryset = chain(data1, data2)

        res = [{
            'receiving_user': item['receiving_user'],
            'work_type': item['work_type'],
            '派单时间': round(item['派单时间'].total_seconds() / item['count'] / 60, 2),
            '接单时间': round(item['接单时间'].total_seconds() / item['count'] / 60, 2),
            '维修时间': round(item['维修时间'].total_seconds() / item['count'] / 60, 2),
            '验收时间': round(item['验收时间'].total_seconds() / item['count'] / 60, 2),
        } for item in queryset]
        return Response(res)


@method_decorator([api_recorder], name='dispatch')
class EquipPeriodStatementView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_result(self, queryset):
        data = queryset.values('work_type').annotate(
            派单时间=OSum(F('assign_datetime') - F('created_date')),
            接单时间=OSum(F('receiving_datetime') - F('assign_datetime')),
            维修时间=OSum(F('repair_end_datetime') - F('repair_start_datetime')),
            验收时间=OSum(F('repair_end_datetime') - F('repair_end_datetime')),
            count=Count('id'),
        ).values('work_type', '派单时间', '接单时间', '维修时间', '验收时间', 'count')

        return data

    def get(self, request):
        work_type = self.request.query_params.get('work_type')
        time = self.request.query_params.get('time')
        type = self.request.query_params.get('type')

        now = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if time:
            now = dt.datetime.strptime(time, '%Y-%m-%d')
        # 本周第一天和最后一天
        this_week_start = now - dt.timedelta(days=now.weekday())
        this_week_end = now + dt.timedelta(days=6 - now.weekday())
        # 本月第一天和最后一天
        days = calendar.monthrange(now.year, now.month)[1]
        this_month_start = dt.datetime(now.year, now.month, 1)
        this_month_end = dt.datetime(now.year, now.month, 1) + dt.timedelta(days=days-1)
        # 本年第一天和最后一天
        this_year_start = dt.datetime(now.year, 1, 1)
        this_year_end = dt.datetime(now.year + 1, 1, 1) - dt.timedelta(days=1)

        kwargs = {
            'day': {'begin_time': now, 'end_time': now + dt.timedelta(days=1)},
            'week': {'begin_time': this_week_start, 'end_time': this_week_end},
            'month': {'begin_time': this_month_start, 'end_time': this_month_end},
            'year': {'begin_time': this_year_start, 'end_time': this_year_end},
        }

        if not work_type:
            queryset1 = EquipApplyOrder.objects.filter(equip_condition='停机', status__in=['已完成', '已验收'],
                                                       last_updated_date__range=(
                                                           kwargs.get(type).get('begin_time'),
                                                           kwargs.get(type).get('end_time'))
                                                           )
            queryset2 = EquipInspectionOrder.objects.filter(equip_condition='停机', status='已完成',
                                                            last_updated_date__range=(
                                                            kwargs.get(type).get('begin_time'),
                                                            kwargs.get(type).get('end_time'))
                                                            )
            data = chain(self.get_result(queryset1), self.get_result(queryset2))

        else:
            if work_type == '巡检':
                queryset = EquipInspectionOrder.objects.filter(work_type=work_type, equip_condition='停机', status='已完成',
                                                               # fault_datetime__range=(kwargs.get(type).get('begin_time'), kwargs.get(type).get('end_time')),
                                                               last_updated_date__range=(kwargs.get(type).get('begin_time'), kwargs.get(type).get('end_time'))
                                                               )
                data = self.get_result(queryset)
            else:
                queryset = EquipApplyOrder.objects.filter(work_type=work_type, equip_condition='停机', status__in=['已完成', '已验收'],
                                                          # fault_datetime__range=(kwargs.get(type).get('begin_time'), kwargs.get(type).get('end_time')),
                                                          last_updated_date__range=(kwargs.get(type).get('begin_time'), kwargs.get(type).get('end_time'))
                                                          )
                data = self.get_result(queryset)

        if type == 'day':
            time = time
        elif type == 'week':
            time = f"{kwargs.get(type).get('begin_time')}~{kwargs.get(type).get('end_time')}"
        elif type == 'month':
            time = kwargs.get(type).get('begin_time').strftime('%Y-%m')
        elif type == 'year':
            time = kwargs.get(type).get('begin_time').strftime('%Y')
        res = [{
            'time': time,
            'work_type': item['work_type'],
            '派单时间': round(item['派单时间'].total_seconds() / 60 / item['count'], 2),
            '接单时间': round(item['接单时间'].total_seconds() / 60 / item['count'], 2),
            '维修时间': round(item['维修时间'].total_seconds() / 60 / item['count'], 2),
            '验收时间': round(item['验收时间'].total_seconds() / 60 / item['count'], 2),
        } for item in data]
        return Response(res)


@method_decorator([api_recorder], name='dispatch')
class EquipFinishingRateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        s_time = self.request.query_params.get('s_time')
        e_time = self.request.query_params.get('e_time')
        time_range = {}
        if s_time:
            time_range = {'created_date__range': [s_time, e_time]}
        res = []
        key_words = ['巡检', '保养', '润滑', '标定', '维修']
        for key_word in key_words:
            data = {'work_type': key_word, 'total_orders': 0, 'completed_in_time': 0, 'completed_overtime': 0,
                    'uncompleted': 0, 'rate': 0, 'in_time_rate': 0}
            query_set = EquipInspectionOrder.objects.filter(
                **time_range) if key_word == '巡检' else EquipApplyOrder.objects.filter(Q(work_type=key_word),
                                                                                      **time_range)
            if query_set:
                data = self.compute(key_word, query_set)
            res.append(data)
        return Response(res)

    @classmethod
    def compute(cls, work_type, query_set):
        completed = query_set.filter(status__in=['已完成', '已验收'])
        total_orders = query_set.count()  # 总工单数
        uncompleted = total_orders - completed.count()  # 未完成工单数
        completed_in_time, completed_overtime = 0, 0
        new_query_set = completed.annotate(completed_time=ExpressionWrapper(F('repair_end_datetime') - F('repair_start_datetime'), output_field=DurationField()))
        for i in new_query_set:
            if work_type == '巡检':
                if not i.equip_repair_standard:
                    completed_in_time += 1
                    continue
            else:
                if not i.equip_repair_standard or not i.equip_repair_standard or not i.equip_maintenance_standard:   # 没有维护作业标准的，按照 按时完成统计
                    completed_in_time += 1
                    continue
            spend_time = round(i.completed_time.total_seconds() / 60, 2)
            if i.equip_repair_standard:
                operation_time = i.equip_repair_standard.operation_time
                operation_time_unit = i.equip_repair_standard.operation_time_unit
            elif i.equip_maintenance_standard:
                operation_time = i.equip_maintenance_standard.operation_time
                operation_time_unit = i.equip_maintenance_standard.operation_time_unit
            else:
                operation_time = i.result_repair_standard.operation_time
                operation_time_unit = i.result_repair_standard.operation_time_unit
            if operation_time_unit == '日':
                standard_time = operation_time * 24 * 60
            elif operation_time_unit == '小时':
                standard_time = operation_time * 60
            elif operation_time_unit == '分钟':
                standard_time = operation_time
            elif operation_time_unit == '秒':
                standard_time = operation_time / 60
            else:
                standard_time = spend_time
            if 0 < spend_time <= standard_time:
                completed_in_time += 1
            else:
                completed_overtime += 1
        data = {'work_type': work_type, 'total_orders': total_orders, 'completed_in_time': completed_in_time,
                'completed_overtime': completed_overtime, 'uncompleted': uncompleted,
                'rate': round(completed.count() / total_orders * 100, 2),
                'in_time_rate': round(completed_in_time / total_orders * 100, 2)}
        return data


@method_decorator([api_recorder], name='dispatch')
class EquipOldRateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        s_time = self.request.query_params.get('s_time')
        e_time = self.request.query_params.get('e_time')
        time_range = {}
        if s_time:
            time_range = {'created_date__range': (s_time, e_time)}
        queryset = EquipRepairMaterialReq.objects.filter(**time_range).values('equip_spare__equip_component_type').annotate(
            count=Count('id'),
            apply_count=Sum('apply'),  # 申请数量
            old_count=Sum('apply', distinct=True, filter=Q(submit_old_flag=True))  # 交旧数量
        ).values('equip_spare__equip_component_type__component_type_code',
                 'equip_spare__equip_component_type__component_type_name',
                 'count', 'apply_count', 'old_count')
        res = [{
            'component_type_code': item['equip_spare__equip_component_type__component_type_code'],
            'component_type_name': item['equip_spare__equip_component_type__component_type_name'],
            'count': item['count'],
            'apply_count': item['apply_count'],
            'old_count': item['old_count'],
            'old_rate': format(item['old_count'] / item['apply_count'], '.2%') if item['old_count'] else 0
        } for item in queryset]
        return Response(res)


@method_decorator([api_recorder], name='dispatch')
class GetSpare(APIView):
    @atomic
    def get(self, request, *args, **kwargs):
        last = EquipSpareErp.objects.filter(sync_date__isnull=False).order_by('sync_date').last()  # 第一次先在数据库插入一条假数据
        last_time = (last.sync_date + dt.timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')
        url = 'http://10.1.10.136/zcxjws_web/zcxjws/pc/jc/getbjwlxx.io'
        try:
            res = requests.post(url=url, json={"syncDate": last_time}, timeout=10)
        except Exception:
            raise ValidationError("网络异常")
        if res.status_code != 200:
            raise ValidationError("请求失败")
        data = json.loads(res.content)
        if not data.get('flag'):
            raise ValidationError(data.get('message'))
        ret = data.get('obj')
        for item in ret:
            equip_component_type = EquipComponentType.objects.filter(component_type_name=item['wllb']).first()
            if not equip_component_type:
                code = EquipComponentType.objects.order_by('component_type_code').last().component_type_code
                component_type_code = code[0:4] + '%03d' % (int(code[-3:]) + 1) if code else '001'
                equip_component_type = EquipComponentType.objects.create(component_type_code=component_type_code,
                                                                         component_type_name=item['wllb'], use_flag=True)
            if item['state'] != '启用':
                continue
            if EquipSpareErp.objects.filter(spare_code=item['wlbh']).exists():
                continue
            EquipSpareErp.objects.update_or_create(
                defaults={"spare_code": item['wlbh'],
                          "spare_name": item['wlmc'],
                          "equip_component_type": equip_component_type,
                          "specification": item['gg'],
                          "unit": item['bzdwmc'],
                          "unique_id": item['wlxxid'],
                          "sync_date": dt.datetime.now()
                          }, **{"unique_id": item['wlxxid']}
                # spare_code=item['wlbh'],
                # spare_name=item['wlmc'],
                # equip_component_type=equip_component_type,
                # specification=item['gg'],
                # unit=item['bzdwmc'],
                # unique_id=item['wlxxid'],
                # sync_date=dt.datetime.now()
            )
        return Response('同步完成')


@method_decorator([api_recorder], name='dispatch')
class GetSpareOrder(APIView):
    @atomic
    def get(self, request):
        # 获取最新的单据
        last = EquipWarehouseOrder.objects.filter(processing_time__isnull=False).order_by('processing_time').last()  # 第一次先在数据库插入一条假数据
        last_time = (last.processing_time + dt.timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')
        json_data = {"ztmc": "zcaj", "clsj": last_time, 'djbh': None}

        url = 'http://10.1.10.136/zcxjws_web/zcxjws/pc/zc/getkclld.io'
        try:
            res = requests.post(url=url, json=json_data, timeout=10)
        except Exception:
            raise ValidationError("网络异常")
        if res.status_code != 200:
            raise ValidationError("请求失败")
        data = json.loads(res.content)
        if not data.get('flag'):
            raise ValidationError(data.get('message'))
        lst = data.get('obj')
        for dic in lst:
            order = dic.get('lld')
            if order.get('llDeptname') != '中策安吉炼胶分厂':
                continue
            order_detail = dic.get('lldmx')  # list
            if EquipWarehouseOrder.objects.filter(barcode=order.get('djbh')):
                continue
            res = EquipWarehouseOrder.objects.filter(created_date__gt=dt.date.today(), status__in=[1, 2, 3]).last()
            if res:
                order_id = res.order_id[:10] + str('%04d' % (int(res.order_id[11:]) + 1))
            else:
               order_id = 'RK' + str(dt.date.today().strftime('%Y%m%d')) + '0001'
            order = EquipWarehouseOrder.objects.create(
                order_id=order_id,
                submission_department='设备科',
                status=1,
                barcode=order.get('djbh'),
                processing_time=order.get('clsj'),
                lluser=order.get('llUser', None)
            )
            for spare in order_detail:
                equip_spare = EquipSpareErp.objects.filter(unique_id=spare.get('wlxxid')).first()
                if not equip_spare:
                    equip_spare = EquipSpareErp.objects.create(unique_id=spare.get('wlxxid'))
                    # raise ValidationError('调用库存领料单接口失败，单据中备件不存在，请先去同步erp备件')
                kwargs = {'equip_warehouse_order': order,
                          'equip_spare': equip_spare,
                          'plan_in_quantity': spare.get('cksl')}
                EquipWarehouseOrderDetail.objects.create(**kwargs)
        return Response('请求成功')


@method_decorator([api_recorder], name='dispatch')
class EquipOrderEntrustView(APIView):
    """
    工单查询加委托
    """
    permission_classes = (IsAuthenticated, PermissionClass({'view': ['charge_d_equip_apply_order', 'begin_d_equip_apply_order'],
                                                            'add': ['charge_d_equip_apply_order', 'begin_d_equip_apply_order']}))

    def get(self, request):
        oper_type = self.request.query_params.get('oper_type')
        user_name = self.request.user.username
        if oper_type == '维修':
            apply_order = EquipApplyOrder.objects.filter(Q(entrust_to_user=user_name) | Q(receiving_user=user_name, entrust_to_user__isnull=True), status__in=['已开始', '已接单']).order_by('entrust_to_user')
            data = EquipApplyOrderSerializer(apply_order, many=True).data
        else:
            apply_order = EquipApplyOrder.objects.filter(accept_user=user_name, status='已完成')
            data = EquipApplyOrderSerializer(apply_order, many=True).data
        res = sorted(data, key=lambda x: x['created_date'], reverse=True)
        return Response({"results": res})

    @atomic()
    def post(self, request):
        pks = self.request.data.get('pks')
        oper_type = self.request.data.get('oper_type')
        entrust_to_user = self.request.data.get('entrust_to_user')
        ding_api = DinDinAPI()
        now_date = str(datetime.now().replace(microsecond=0))
        if oper_type == '验收':
            entrust_num = EquipApplyOrder.objects.filter(~Q(status='已完成'), id__in=pks).count()
            if entrust_num != 0:
                raise ValidationError('存在非已完成状态的订单, 请刷新订单!')
            data = {'entrust_datetime': now_date, 'accept_user': entrust_to_user}
        else:
            entrust_num = EquipApplyOrder.objects.filter(~Q(status__in=['已接单', '已开始']), id__in=pks).count()
            if entrust_num != 0:
                raise ValidationError('存在非已开始状态的订单, 请刷新订单!')
            data = {'entrust_to_user': entrust_to_user, 'entrust_datetime': now_date}
        EquipApplyOrder.objects.filter(id__in=pks).update(**data)
        instance_list = EquipApplyOrder.objects.filter(id__in=pks)
        # 发送消息给受委托人和上级
        user_ids = get_ding_uids_by_name(entrust_to_user, all_user='1,2')
        for order_id in pks:
            instance = instance_list.filter(id=order_id).first()
            # 添加履历
            EquipOrderEntrust.objects.create(**{'work_order_no': instance.work_order_no, 'entrust_type': oper_type,
                                                'entrust_user': self.request.user.username,
                                                'entrust_datetime': now_date, 'entrust_to_user': entrust_to_user})
            content = {"title": f"{oper_type}委托工单成功",
                       "form": [
                           {"key": "工单编号:", "value": instance.work_order_no},
                           {"key": "机台:", "value": instance.equip_no},
                           {"key": "重要程度:", "value": instance.importance_level},
                           {"key": "受委托人:", "value": entrust_to_user},
                           {"key": "委托时间:", "value": now_date}]}
            ding_api.send_message(user_ids, content, order_id)

        return Response('委托操作成功')


@method_decorator([api_recorder], name='dispatch')
class EquipIndexView(APIView):
    authentication_classes = ()

    @staticmethod
    def get_current_factory_date():
        # 获取当前时间的工厂日期，开始、结束时间
        now = datetime.now()
        current_work_schedule_plan = WorkSchedulePlan.objects.filter(
            start_time__lte=now,
            end_time__gte=now,
            plan_schedule__work_schedule__work_procedure__global_name='密炼'
        ).first()
        date_now = str(now.date())
        if current_work_schedule_plan:
            date_now = str(current_work_schedule_plan.plan_schedule.day_time)
            st = current_work_schedule_plan.plan_schedule.work_schedule_plan.filter(
                classes__global_name='早班').first()
            et = current_work_schedule_plan.plan_schedule.work_schedule_plan.filter(
                classes__global_name='夜班').first()
            if st:
                begin_time = str(st.start_time)
            else:
                begin_time = date_now + ' 00:00:01'
            if et:
                end_time = str(et.end_time)
            else:
                end_time = date_now + ' 23:59:59'
        else:
            begin_time = date_now + ' 00:00:01'
            end_time = date_now + ' 23:59:59'

        return date_now, begin_time, end_time

    def get(self, request):
        now_time = datetime.now()
        factory_date, begin_time, end_time = self.get_current_factory_date()

        # 设备
        equips = Equip.objects.filter(
            category__equip_type__global_name__in=("密炼设备", "称量设备")
        ).order_by('equip_no')

        # 当日理论工作总时间
        total_time = (now_time - datetime.strptime(begin_time, '%Y-%m-%d %H:%M:%S')).total_seconds()//60
        # 密炼时间
        mixin_time_dict = dict(TrainsFeedbacks.objects.filter(
            factory_date=factory_date
        ).values('equip_no').annotate(t=OSum((F('end_time') - F('begin_time')))).values_list('equip_no', 't'))

        # 当日计划与实际数据(密炼设备)
        plan_data = dict(ProductClassesPlan.objects.filter(
            work_schedule_plan__plan_schedule__day_time=factory_date,
            delete_flag=False).values('equip__equip_no').annotate(plan_trains=Sum('plan_trains')).values_list(
            'equip__equip_no', 'plan_trains'))
        actual_data = dict(TrainsFeedbacks.objects.filter(
            factory_date=factory_date).values('equip_no').annotate(actual_trains=Count('id')).values_list(
            'equip_no', 'actual_trains'))
        # 维修工单数据
        apply_data = EquipApplyOrder.objects.filter(
            status__in=('已生成', '已指派', '已接单', '已开始', '已完成')
        ).values('equip_no', 'status').annotate(num=Count('id'))
        apply_data_dict = {'{}-{}'.format(i['equip_no'], i['status']): i['num'] for i in apply_data}

        ret = {
            'equip_data': [],
            'incharge_user': '',
            'repair_user': '',
            'responsor_user': ''
        }
        # ding_api = DinDinAPI()
        # result = get_staff_status(ding_api, '设备科')
        result = []
        if result:
            ret['incharge_user'] = result[0].get('username')
            ret['repair_user'] = result[0].get('username')
            ret['responsor_user'] = result[0].get('username')
        for equip in equips:
            last_running_time = None
            current_product = ''
            equip_no = equip.equip_no
            equip_cat = equip.category.equip_type.global_name
            if equip_cat == '密炼设备':
                # 实际生产车次
                actual_trains = actual_data.get(equip_no, 0) if equip_no != 'Z04' else actual_data.get(equip_no, 0)//2
                # 计划车次
                plan_trains = plan_data.get(equip_no, 0)
                # 总停机时间：工厂日期开始到当前总时间减去密炼生产时间
                # TODO 还需减去投料时的间隔时间（生产车次总和*该规格投料间隔时间）
                t0 = int(mixin_time_dict.get(equip_no).total_seconds() / 60) if mixin_time_dict.get(equip_no) else 0
                halt_time = int(total_time - t0)
                last_trains_feedback = TrainsFeedbacks.objects.filter(equip_no=equip_no, factory_date=factory_date).order_by('id').last()
                if last_trains_feedback:
                    last_running_time = last_trains_feedback.end_time
                    current_product = '({}/{}) {}'.format(last_trains_feedback.actual_trains,
                                                          last_trains_feedback.plan_trains,
                                                          last_trains_feedback.product_no)
            else:
                actual_trains = plan_trains = halt_time = 0
                try:
                    plan_actual_data = Plan.objects.using(equip_no).filter(
                        date_time=factory_date).aggregate(plan_trains=Sum('setno'),
                                                          actual_trains=Sum('actno'))
                    # 称量实际车次
                    actual_trains = plan_actual_data['actual_trains'] if plan_actual_data['actual_trains'] else 0
                    # 称量计划车次
                    plan_trains = plan_actual_data['plan_trains'] if plan_actual_data['plan_trains'] else 0
                    # 计算所有计划开始结束时间累加
                    plan_list = Plan.objects.using(equip_no).filter(
                        date_time=factory_date,
                        actno__gt=0).values('starttime', 'stoptime', 'actno', 'state', 'recipe', 'setno')
                    time_consume = 0
                    try:
                        last_running_time = max([datetime.strptime(i['stoptime'], '%Y-%m-%d %H:%M:%S') for i in filter(lambda x: x['stoptime'], plan_list)])
                    except:
                        pass
                    for item in plan_list:
                        try:
                            finish_no = int(item['actno'])
                        except Exception:
                            continue
                        if item['state'] == '运行中':
                            last_running_time = now_time
                            if finish_no > 0:
                                current_product = '({}/{}) {}'.format(item['actno'],
                                                                      item['setno'],
                                                                      item['recipe'])
                        if not item['starttime']:
                            continue
                        if finish_no > 0:
                            if not item['stoptime'] and item['starttime'] and item['state'] == '运行中':
                                time_consume += (now_time -
                                                 datetime.strptime(item['starttime'], '%Y-%m-%d %H:%M:%S')
                                                 ).total_seconds()
                            elif all([item['starttime'], item['stoptime']]):
                                time_consume += (datetime.strptime(item['stoptime'], '%Y-%m-%d %H:%M:%S') -
                                                 datetime.strptime(item['starttime'], '%Y-%m-%d %H:%M:%S')
                                                 ).total_seconds()
                    halt_time = int(total_time - time_consume/60)
                except Exception:
                    pass
            # 待指派数量
            unassigned_order_num = apply_data_dict.get('{}-{}'.format(equip_no, '已生成'), 0)
            # 待接单数量
            assigned_order_num = apply_data_dict.get('{}-{}'.format(equip_no, '已指派'), 0)
            # 待执行数量
            to_executed_order_num = apply_data_dict.get('{}-{}'.format(equip_no, '已接单'), 0)
            # 待验收数量
            to_check_order_num = apply_data_dict.get('{}-{}'.format(equip_no, '已完成'), 0)
            is_repairing = False

            # 取最后一条报修单
            last_apply_order = EquipApplyOrder.objects.filter(
                # equip_condition='停机',
                # work_type='维修',
                status__in=('已生成', '已指派', '已接单', '已开始'),
                equip_no=equip_no).order_by('id').last()
            if not last_apply_order:
                repair_plan_id = ()
                state = '运行中'
                error_reason = ''
                breakdown_time = 0
                error_continue_minutes = 0
                if last_running_time:
                    cm = (now_time - last_running_time).total_seconds() / 60
                    if cm > 15:
                        state = '生产停机'
                        error_continue_minutes = int(cm)
                    else:
                        halt_time -= round(cm, 0)
                else:
                    state = '生产停机'
                    error_continue_minutes = total_time
            else:
                repair_plan_id = (last_apply_order.id, last_apply_order.plan_id)
                breakdown_time = 0
                state = '设备故障'
                error_reason = last_apply_order.result_fault_cause
                fault_time = last_apply_order.fault_datetime or last_apply_order.created_date
                error_continue_minutes = int((now_time - fault_time).total_seconds() / 60)
                if last_running_time:
                    cm = (now_time - last_running_time).total_seconds() / 60
                    if cm <= 15:
                        repair_plan_id = ()
                        state = '运行中'
                        error_reason = ''
                        error_continue_minutes = 0
                        halt_time -= round(cm, 0)
                else:
                    if last_apply_order.status == '已开始':
                        is_repairing = True
                    if last_apply_order.equip_condition == '停机':
                        state = '故障停机'
                    # 设备故障停机时间
                    orders = EquipApplyOrder.objects.filter(
                        equip_no=equip_no,
                        equip_condition='停机',
                        repair_start_datetime__isnull=False).filter(
                        Q(repair_end_datetime__isnull=True) |
                        Q(repair_end_datetime__gt=begin_time)
                    )
                    bk_st = []
                    bk_et = []
                    for order in orders:
                        if order.repair_start_datetime <= datetime.strptime(begin_time, '%Y-%m-%d %H:%M:%S'):
                            down_st = datetime.strptime(begin_time, '%Y-%m-%d %H:%M:%S')
                        else:
                            down_st = last_apply_order.repair_start_datetime
                        if not order.repair_end_datetime:
                            down_et = now_time
                        else:
                            down_et = order.repair_end_datetime
                        bk_st.append(down_st)
                        bk_et.append(down_et)
                    if bk_st and bk_et:
                        breakdown_time = int((max(bk_et) - min(bk_st)).total_seconds()/60)
            if halt_time < 0:
                halt_time = 0
                breakdown_time = 0
            data = {
                'equip_no': equip_no,  # 机台
                'equip_catetory': equip_cat,  # 设备类型
                'breakdown_time': breakdown_time,  # 故障时间
                'halt_time': halt_time,  # 停机时间
                'downtime': '{}/{}'.format(breakdown_time, halt_time),  # 故障时间/停机时间
                'plan_actual_data': '{}/{}'.format(actual_trains, plan_trains),  # 实际/计划车次
                'apply_orders': '{}-{}-{}-{}'.format(unassigned_order_num,
                                                     assigned_order_num,
                                                     to_executed_order_num,
                                                     to_check_order_num),  # 未指派/已指派/待执行/待验收工单数量
                'state': state,  # 运行状态（运行中、生产停机、故障停机、设备故障）
                'error_reason': error_reason,  # 故障原因
                'is_repairing': is_repairing,  # 是否正在维修
                'error_minutes': error_continue_minutes,  # 故障/停机持续时间
                'current_product': current_product,  # 当前生产物料
                'repair_plan_id': repair_plan_id  # 工单编号（查看维修工单详情时使用）
            }
            ret['equip_data'].append(data)
        return Response(ret)