import copy
import datetime
import datetime as dt
import json
import re
import uuid
from io import BytesIO

import xlrd
import xlwt
from django.db.models import F, Min, Max, Sum, Avg, Q
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from basics.filters import GlobalCodeTypeFilter
from equipment.filters import EquipDownTypeFilter, EquipDownReasonFilter, EquipPartFilter, EquipMaintenanceOrderFilter, \
    PropertyFilter, PlatformConfigFilter, EquipMaintenanceOrderLogFilter, EquipCurrentStatusFilter, EquipSupplierFilter, \
    EquipPropertyFilter, EquipAreaDefineFilter, EquipPartNewFilter, EquipComponentTypeFilter, \
    EquipSpareErpFilter, EquipFaultTypeFilter, EquipFaultCodeFilter, ERPSpareComponentRelationFilter, \
    EquipFaultSignalFilter, EquipMachineHaltTypeFilter, EquipMachineHaltReasonFilter, EquipOrderAssignRuleFilter, \
    EquipBomFilter, EquipJobItemStandardFilter, EquipMaintenanceStandardFilter, EquipRepairStandardFilter
from equipment.models import EquipFaultType, EquipFault, PropertyTypeNode, Property, PlatformConfig, EquipProperty, \
    EquipSupplier, EquipAreaDefine, EquipPartNew, EquipComponentType, EquipComponent, ERPSpareComponentRelation, \
    EquipSpareErp, EquipTargetMTBFMTTRSetting, EquipBom, EquipJobItemStandard, EquipMaintenanceStandard, \
    EquipMaintenanceStandardMaterials, EquipRepairStandard, EquipRepairStandardMaterials
from equipment.serializers import *
from equipment.task import property_template, property_import
from equipment.utils import gen_template_response
from mes.common_code import OMin, OMax, OSum, CommonDeleteMixin
from mes.derorators import api_recorder
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.response import Response
from django.db.transaction import atomic
from rest_framework.decorators import action

# Create your views here.

from rest_framework.viewsets import ModelViewSet

from basics.models import Equip, GlobalCode, EquipCategoryAttribute
from equipment.serializers import EquipRealtimeSerializer
from mes.paginations import SinglePageNumberPagination
from quality.utils import get_cur_sheet, get_sheet_data


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
        # print(temp_dict)
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
    # permission_classes = (IsAuthenticated,)
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
    # permission_classes = (IsAuthenticated,)
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
    # permission_classes = (IsAuthenticated,)
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
    # permission_classes = (IsAuthenticated,)
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
        print(data)
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
        print(data)
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
        data = get_sheet_data(cur_sheet, start_row=1)
        area_list = []
        for item in data:
            obj = EquipSupplier.objects.filter(Q(supplier_code=item[0]) | Q(supplier_name=item[1])).first()
            if not obj:
                if item[5] not in ['普通供应商', '集采供应商']:
                    raise ValidationError('该供应商类别不存在')
                if not isinstance(item[4], float):
                    raise ValidationError('联系号码输入有误！')
                area_list.append({"supplier_code": item[0],
                                  "supplier_name": item[1],
                                  "region": item[2],
                                  "contact_name": item[3],
                                  "contact_phone": str(int(item[4])),
                                  "supplier_type": item[5],
                                  })
        s = EquipSupplierSerializer(data=area_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            s.save()
        else:
            raise ValidationError('供应商或编号已存在！')
        return Response('导入成功')

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
    serializer_class = EquipPropertySerializer
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
        data = get_sheet_data(cur_sheet)
        area_list = []
        for item in data:
            obj = EquipProperty.objects.filter(property_no=item[0]).first()
            if not obj:
                status_dict = {'使用中': 1, '废弃': 2, '限制': 3}
                equip_type = EquipCategoryAttribute.objects.filter(category_no=item[3], use_flag=True).first()
                equip_supplier = EquipSupplier.objects.filter(supplier_name=item[6], use_flag=True).first()
                if not equip_type:
                    raise ValidationError('导入的设备型号{}不存在'.format(item[3]))
                # 设备供应商
                if not equip_supplier:
                    raise ValidationError('设备制造商{}不存在'.format(item[6]))
                area_list.append({"property_no": int(item[0]) if isinstance(item[0], float) else item[0],
                                  "src_no": int(item[1]) if isinstance(item[1], float) else item[1],
                                  "financial_no": int(item[2]) if isinstance(item[2], float) else item[2],
                                  "equip_type": equip_type.id,
                                  "equip_no": item[4],
                                  "equip_name": item[5],
                                  "equip_supplier": equip_supplier.id,
                                  "capacity": item[7],
                                  "price": item[8],
                                  "status": status_dict.get(item[9]),
                                  "equip_type_name": item[10],
                                  "leave_factory_no": item[11],
                                  "leave_factory_date": item[12],
                                  "use_date": item[13]
                                  })
        s = EquipPropertySerializer(data=area_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response('导入成功')


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
            obj = EquipAreaDefine.objects.filter(Q(area_code=item[0]) | Q(area_name=item[1])).first()
            if not obj:
                area_list.append({"area_code": item[0],
                                  "area_name": item[1],
                                  "inspection_line_no": int(item[2]) if item[2] else None,
                                  "desc": item[3]})
        s = EquipAreaDefineSerializer(data=area_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response('导入成功')

    def list(self, request, *args, **kwargs):
        export = self.request.query_params.get('export')
        queryset = self.filter_queryset(self.get_queryset())
        if export:
            data = self.get_serializer(queryset, many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
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
    filter_backends = (DjangoFilterBackend, )
    filter_class = EquipPartNewFilter
    FILE_NAME = '设备部位信息'
    EXPORT_FIELDS_DICT = {"所属主设备种类": "category_no",
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
        data = get_sheet_data(cur_sheet)
        parts_list = []
        for item in data:
            equip_type = EquipCategoryAttribute.objects.filter(category_no=item[0]).first()
            global_part_type = GlobalCode.objects.filter(global_name=item[1]).first()
            if not equip_type:
                raise ValidationError('主设备种类{}不存在'.format(item[0]))
            if not global_part_type:
                raise ValidationError('部位分类{}不存在'.format(item[1]))
            obj = EquipPartNew.objects.filter(Q(part_code=item[2]) | Q(part_name=item[3])).first()
            if not obj:
                parts_list.append({"equip_type": equip_type.id,
                                   "global_part_type": global_part_type.id,
                                   "part_code": item[2],
                                   "part_name": item[3]})
        s = EquipPartNewSerializer(data=parts_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response('导入成功')

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
    queryset = EquipComponentType.objects.all()
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
        data = get_sheet_data(cur_sheet)
        parts_list = []
        for item in data:
            obj = EquipComponentType.objects.filter(Q(component_type_code=item[0]) |
                                                    Q(component_type_name=item[1])).first()
            if not obj:
                parts_list.append({"component_type_code": item[0],
                                   "component_type_name": item[1]})
        s = EquipComponentTypeSerializer(data=parts_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response('导入成功')


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
        "所属主设备种类": "equip_type_name",
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
        equip_type = query_params.get('equip_type')
        equip_part = query_params.get('equip_part')
        equip_component_type = query_params.get('equip_component_type')
        component_name = query_params.get('component_name')
        is_binding = query_params.get('is_binding')
        use_flag = query_params.get('use_flag')
        filter_kwargs = {}
        if equip_type:
            filter_kwargs['equip_part__equip_type_id'] = equip_type
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
        data = get_sheet_data(cur_sheet)
        parts_list = []
        for item in data:
            equip_type = EquipCategoryAttribute.objects.filter(category_no=item[0]).first()
            global_part_type = GlobalCode.objects.filter(global_name=item[1]).first()
            equip_component_type = EquipComponentType.objects.filter(component_type_name=item[2]).first()
            if not equip_type:
                raise ValidationError('主设备种类{}不存在'.format(item[0]))
            if not global_part_type:
                raise ValidationError('部位分类{}不存在'.format(item[1]))
            if not equip_component_type:
                raise ValidationError('部件分类{}不存在'.format(item[2]))
            equip_part = EquipPartNew.objects.filter(equip_type=equip_type.id,
                                                     global_part_type=global_part_type.id).first()
            obj = EquipComponent.objects.filter(Q(component_code=item[3]) | Q(component_name=item[4])).first()
            if not obj:
                parts_list.append({"equip_part": equip_part.id,
                                   "equip_component_type": equip_component_type.id,
                                   "component_code": item[3],
                                   "component_name": item[4],
                                   "use_flag": 1 if item[6] == 'Y' else 0})
        s = EquipComponentCreateSerializer(data=parts_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response('导入成功')


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
        data = get_sheet_data(cur_sheet)
        parts_list = []
        for item in data:
            equip_component_type = EquipComponentType.objects.filter(component_type_name=item[2]).first()
            if not equip_component_type:
                raise ValidationError('备件分类{}不存在'.format(item[2]))
            obj = EquipSpareErp.objects.filter(Q(spare_code=item[0]) | Q(spare_name=item[1])).first()
            if not obj:
                parts_list.append({"spare_code": item[0],
                                   "spare_name": item[1],
                                   "equip_component_type": equip_component_type.id,
                                   "specification": item[3],
                                   "technical_params": item[4],
                                   "unit": item[5],
                                   "key_parts_flag": 1 if item[6] == '是' else 0,
                                   "lower_stock": item[7],
                                   "upper_stock": item[8],
                                   "cost": item[9],
                                   "texture_material": item[10],
                                   "period_validity": item[11],
                                   "supplier_name": item[12],
                                   "use_flag": 1 if item[13] == 'Y' else 0,
                                   "info_source": "ERP"})
        s = EquipSpareErpImportCreateSerializer(data=parts_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response('导入成功')


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
    # permission_classes = (IsAuthenticated,)
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
                equip_property_type_name = section.property_type_node
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
                index_tree[section.id] = dict({"id": section.id, "factory_id": section.factory_id,
                                               "level": section.level, "children": [],
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
            else:  # 没有节点则加入
                index_tree[section.parent_flag_id] = dict(
                    {"id": section.parent_flag_id, "factory_id": section.parent_flag.factory_id,
                     "level": section.parent_flag.level, "children": [], "equip_category_id": equip_category_id,
                     "equip_part_id": equip_part_id, "equip_component_id": equip_component_id,
                     'equip_info_id': equip_info_id, 'equip_property_type_id': equip_property_type_id,
                     "equip_property_type_name": equip_property_type_name, "equip_component_name": equip_component_code,
                     "equip_part_name": equip_part_code, "equip_info_name": equip_info_code})
                index_tree[section.parent_flag_id]["children"].append(index_tree[section.id])
        return Response({'results': data})

    @atomic
    def create(self, request, *args, **kwargs):
        def add_parent(instance, children):
            # 当前节点数据
            for child in children:
                child_current_data = EquipBom.objects.filter(id=child['id']).values().first()
                child_current_data.pop('id')
                child_current_data['parent_flag_id'] = instance.id
                if child_current_data['level'] == 2:
                    child_current_data.update({'property_type_id': child_current_data['property_type_id'],
                                               'property_type_node': child_current_data['property_type_node']})
                elif child_current_data['level'] == 3:
                    child_current_data.update({'property_type_id': instance.property_type_id,
                                               'property_type_node': instance.property_type_node,
                                               'equip_no': child_current_data['equip_no'],
                                               'equip_name': child_current_data['equip_name'],
                                               'equip_status': child_current_data['equip_status'],
                                               'equip_type': child_current_data['equip_type'],
                                               'equip_info_id': child_current_data['equip_info_id']})
                elif child_current_data['level'] == 4:
                    child_current_data.update({'property_type_id': instance.property_type_id,
                                               'property_type_node': instance.property_type_node,
                                               'equip_no': instance.equip_no, 'equip_name': instance.equip_name,
                                               'equip_status': instance.equip_status,
                                               'equip_info_id': instance.equip_info_id,
                                               'equip_type': instance.equip_type})
                elif child_current_data['level'] == 5:
                    child_current_data.update({'property_type_id': instance.property_type_id,
                                               'property_type_node': instance.property_type_node,
                                               'equip_no': instance.equip_no, 'equip_name': instance.equip_name,
                                               'equip_status': instance.equip_status,
                                               'equip_info_id': instance.equip_info_id,
                                               'equip_type': instance.equip_type,
                                               'part_id': instance.part_id, 'part_name': instance.part_name})
                else:
                    pass
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
                equip_property_type = GlobalCode.objects.filter(id=curr_label_obj_id).first()
                if children_of_parent.filter(property_type=equip_property_type.id):
                    raise ValidationError('设备类型已经存在')
                curr_data.update({'level': 2, 'property_type': equip_property_type.id,
                                  'property_type_node': equip_property_type.global_name})
            elif parent_flag_info.level == 2:
                equip = Equip.objects.filter(id=curr_label_obj_id).first()
                if children_of_parent.filter(equip_info=equip.id):
                    raise ValidationError('设备已经存在')
                curr_data.update({'property_type': parent_flag_info.property_type_id,
                                  'property_type_node': parent_flag_info.factory_id, 'equip_no': equip.equip_no,
                                  'equip_name': equip.equip_name, 'equip_status': '启用' if equip.use_flag else '停用',
                                  'level': 3, 'equip_type': equip.category.category_name,
                                  'equip_info': curr_label_obj_id})
            elif parent_flag_info.level == 3:
                equip_part = EquipPartNew.objects.filter(id=curr_label_obj_id).first()
                if children_of_parent.filter(part=equip_part.id):
                    raise ValidationError('设备部位已经存在')
                curr_data.update({'property_type': parent_flag_info.property_type_id,
                                  'property_type_node': parent_flag_info.property_type_node,
                                  'equip_no': parent_flag_info.equip_no, 'equip_name': parent_flag_info.equip_name,
                                  'equip_status': parent_flag_info.equip_status,
                                  'equip_info': parent_flag_info.equip_info_id,
                                  'equip_type': parent_flag_info.equip_type, 'level': 4,
                                  'part': curr_label_obj_id, 'part_name': equip_part.part_name})
            else:
                equip_component = EquipComponent.objects.filter(id=curr_label_obj_id).first()
                if children_of_parent.filter(component=equip_component.id):
                    raise ValidationError('设备部件已经存在')
                curr_data.update({'property_type': parent_flag_info.property_type_id,
                                  'property_type_node': parent_flag_info.property_type_node,
                                  'equip_no': parent_flag_info.equip_no, 'equip_name': parent_flag_info.equip_name,
                                  'equip_status': parent_flag_info.equip_status,
                                  'equip_info': parent_flag_info.equip_info_id,
                                  'equip_type': parent_flag_info.equip_type, 'level': 5,
                                  'part': parent_flag_info.part_id, 'part_name': parent_flag_info.part_name,
                                  'component': curr_label_obj_id, 'component_name': equip_component.component_name})
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
            equip_property_type = GlobalCode.objects.filter(id=curr_label_obj_id).first()
            current_data.update(
                {'property_type_id': curr_label_obj_id, 'property_type_node': equip_property_type.global_name})
        elif current_data['level'] == 3:
            if children_of_parent.filter(equip_info=curr_label_obj_id):
                raise ValidationError('设备已经存在')
            equip = Equip.objects.filter(id=curr_label_obj_id).first()
            current_data.update({'equip_info_id': curr_label_obj_id, 'equip_no': equip.equip_no,
                                 'equip_name': equip.equip_name, 'equip_type': equip.category.category_name,
                                 'equip_status': '启用' if equip.use_flag else '停用'})
        elif current_data['level'] == 4:
            if children_of_parent.filter(part=curr_label_obj_id):
                raise ValidationError('设备部位已经存在')
            equip_part = EquipPartNew.objects.filter(id=curr_label_obj_id).first()
            current_data.update({'part_id': curr_label_obj_id, 'part_name': equip_part.part_name})
        else:
            if children_of_parent.filter(component=curr_label_obj_id):
                raise ValidationError('设备部件已经存在')
            equip_component = EquipComponent.objects.filter(id=curr_label_obj_id).first()
            current_data.update({'component_id': curr_label_obj_id, 'component_name': equip_component.component_name})
        current_data.pop('id')
        current_data['factory_id'] = factory_id
        current_data['parent_flag_id'] = parent_flag
        instance = EquipBom.objects.create(**current_data)
        if children:
            add_parent(instance, children)
        return Response('添加成功')


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
    # permission_classes = (IsAuthenticated,)
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
    # permission_classes = (IsAuthenticated,)
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
        data = get_sheet_data(cur_sheet)
        signal_list = []
        for item in data:
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
                                    "signal_variable_name": str(item[6]),
                                    "signal_variable_type": item[7],
                                    "alarm_signal_minvalue": item[8],
                                    "alarm_signal_maxvalue": item[9],
                                    "alarm_signal_duration": item[10],
                                    "alarm_signal_down_flag": True if item[11] == 'Y' else False,
                                    "alarm_signal_desc": item[12],
                                    "fault_signal_minvalue": item[13],
                                    "fault_signal_maxvalue": item[14],
                                    "fault_signal_duration": item[15],
                                    "fault_signal_down_flag": True if item[16] == 'Y' else False,
                                    "fault_signal_desc": item[17],
                                    "equip": equip.id,
                                    "equip_part": equip_part.id if equip_part else None,
                                    "equip_component": equip_component.id if equip_component else None,
                                    })
        s = EquipFaultSignalSerializer(data=signal_list, many=True, context={'request': request})
        if s.is_valid():
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response('导入成功')

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
        data = get_sheet_data(cur_sheet)
        signal_list = []
        for item in data:
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
                                    "receive_interval": item[6],
                                    "receive_warning_times": item[7],
                                    "start_interval": item[8],
                                    "start_warning_times": item[9],
                                    "accept_interval": item[10],
                                    "accept_warning_times": item[11],
                                    })
        s = EquipOrderAssignRuleSerializer(data=signal_list, many=True, context={'request': request})
        if s.is_valid():
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response('导入成功')

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
        return Response(EquipTargetMTBFMTTRSetting.objects.values('id', 'equip', 'equip__equip_no', 'equip__equip_name',
                                                                  'target_mtb', 'target_mttr'))

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
    # permission_classes = (IsAuthenticated,)
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
            standard = {i.split('、')[0]: i.split('、')[1] for i in check_standard_desc_column.split('；')[:-1]}
            type = {i.split('、')[0]: i.split('、')[1] for i in check_standard_type_column.split('；')[:-1]}
            for i in work_details_column.split('；')[:-1]:
                seq, content = i.split('、')
                data = {"sequence": seq, "content": content, "check_standard_desc": standard.get(seq),
                        "check_standard_type": type.get(seq)}
                work_details.append(data)
            return work_details

        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        data = get_sheet_data(cur_sheet)
        parts_list = []
        for item in data:
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
            s.save()
        else:
            raise ValidationError('导入的数据类型有误')
        return Response('导入成功')


@method_decorator([api_recorder], name="dispatch")
class EquipMaintenanceStandardViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipMaintenanceStandard.objects.order_by('id')
    serializer_class = EquipMaintenanceStandardSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipMaintenanceStandardFilter
    FILE_NAME = '设备维护作业标准定义'
    EXPORT_FIELDS_DICT = {
                          "作业类型": "work_type",
                          "标准编号": "standard_code",
                          "标准名称": "standard_name",
                          "设备种类": "equip_type_name",
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
                          "所需物料名称": "spare_list_str",
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
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            obj = EquipMaintenanceStandard.objects.create(**serializer.validated_data, created_user=self.request.user)
            if spare_list:
                for item in spare_list:
                    EquipMaintenanceStandardMaterials.objects.create(equip_maintenance_standard=obj,
                                                                     equip_spare_erp_id=item['equip_spare_erp__id'], quantity=item['quantity'])
            return Response('新建成功')

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        id = int(kwargs.get('pk'))
        spare_list = request.data.get('spare_list', None)
        if spare_list:
            EquipMaintenanceStandardMaterials.objects.filter(equip_maintenance_standard_id=id).delete()
            for item in spare_list:
                EquipMaintenanceStandardMaterials.objects.create(equip_maintenance_standard_id=id,
                                                                equip_spare_erp_id=item['equip_spare_erp__id'], quantity=item['quantity'])
        else:
            EquipMaintenanceStandardMaterials.objects.filter(equip_maintenance_standard_id=id).delete()

        self.perform_update(serializer)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).distinct()
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
        data = get_sheet_data(cur_sheet)
        signal_list = []
        for item in data:
            equip_type = EquipCategoryAttribute.objects.filter(category_no=item[3]).first()
            equip_part = EquipPartNew.objects.filter(part_name=item[4]).first()
            equip_component = EquipComponent.objects.filter(component_name=item[5]).first()
            equip_job_item_standard = EquipJobItemStandard.objects.filter(standard_name=item[8]).first()
            if not equip_type:
                raise ValidationError(f'设备种类{item[3]}不存在')
            if not equip_part:
                raise ValidationError(f'部位名称{item[4]}不存在')
            if not equip_job_item_standard:
                raise ValidationError(f'作业项目{item[8]}不存在')
            try:
                if item[9]:
                    start_time = dt.date(*map(int, item[9].split('-'))) if isinstance(item[9], str) else datetime.date(xlrd.xldate.xldate_as_datetime(item[9], 0))
            except: raise ValidationError('导入的开始时间格式有误')

            lst = [i[1] for i in data]
            if lst.count(item[1]) > 1:
                raise ValidationError('导入的物料编码不能重复')

            if not EquipMaintenanceStandard.objects.filter(Q(Q(standard_code=item[1]) | Q(standard_name=item[2]))).exists():
                signal_list.append({"work_type": item[0],
                                    "standard_code": item[1],
                                    "standard_name": item[2],
                                    "equip_type": equip_type.id,
                                    "equip_part": equip_part.id,
                                    "equip_component": equip_component.id if equip_component else None,
                                    "equip_condition": item[6],
                                    "important_level": item[7],
                                    "equip_job_item_standard": equip_job_item_standard.id,
                                    "start_time": start_time if item[9] else None,
                                    "maintenance_cycle": item[10] if item[10] else None,
                                    "cycle_unit": item[11] if item[11] else None,
                                    "cycle_num": item[12] if item[12] else None,
                                    "cycle_person_num": item[13] if item[13] else None,
                                    "operation_time": item[14] if item[14] else None,
                                    "operation_time_unit": item[15] if item[15] else None,
                                    "remind_flag1": True,
                                    "remind_flag2": True,
                                    "remind_flag3": False,
                                    "spares": item[16] if item[16] else 'no',  # '清洁剂'
                                    })

        serializer = EquipMaintenanceStandardImportSerializer(data=signal_list, many=True, context={'request': request})
        if serializer.is_valid(raise_exception=True):
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
        return Response('导入成功')

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
        except: pass
        kwargs = {'巡检': 'XJBZ0001',
                  '保养': 'BYBZ0001',
                  '标定': 'BDBZ0001',
                  '润滑': 'RHBZ0001'}
        return Response({'results': kwargs[rule_code]})


@method_decorator([api_recorder], name="dispatch")
class EquipRepairStandardViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipRepairStandard.objects.order_by('id')
    serializer_class = EquipRepairStandardSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipRepairStandardFilter
    FILE_NAME = '设备维修作业标准定义'
    EXPORT_FIELDS_DICT = {
                          "标准编号": "standard_code",
                          "标准名称": "standard_name",
                          "设备种类": "equip_type_name",
                          "部位名称": "equip_part_name",
                          "部件名称": "equip_component_name",
                          "设备条件": "equip_condition",
                          "重要程度": "important_level",
                          "故障分类": "equip_fault_name",
                          "作业项目": "equip_job_item_standard_name",
                          "所需人数": "cycle_person_num",
                          "作业时间": "operation_time",
                          "作业时间单位": "operation_time_unit",
                          "所需物料名称": "spare_list_str",
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
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            obj = EquipRepairStandard.objects.create(**serializer.validated_data, created_user=self.request.user)
            if spare_list:
                for item in spare_list:
                    EquipRepairStandardMaterials.objects.create(equip_repair_standard=obj,
                                                                     equip_spare_erp_id=item['equip_spare_erp__id'], quantity=item['quantity'])
            return Response('新建成功')

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        id = int(kwargs.get('pk'))
        spare_list = request.data.get('spare_list', None)
        if spare_list:
            EquipRepairStandardMaterials.objects.filter(equip_repair_standard_id=id).delete()
            for item in spare_list:
                EquipRepairStandardMaterials.objects.create(equip_repair_standard_id=id,
                                                                 equip_spare_erp_id=item['equip_spare_erp__id'], quantity=item['quantity'])
        else:
            EquipRepairStandardMaterials.objects.filter(equip_repair_standard_id=id).delete()
        self.perform_update(serializer)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).distinct()
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
        data = get_sheet_data(cur_sheet)
        signal_list = []
        for item in data:
            equip_type = EquipCategoryAttribute.objects.filter(category_no=item[2]).first()
            equip_part = EquipPartNew.objects.filter(part_name=item[3]).first()
            equip_component = EquipComponent.objects.filter(component_name=item[4]).first()
            equip_fault = EquipFault.objects.filter(fault_name=item[7]).first()
            equip_job_item_standard = EquipJobItemStandard.objects.filter(standard_name=item[8]).first()
            if not equip_type:
                raise ValidationError(f'设备种类{item[2]}不存在')
            if not equip_part:
                raise ValidationError(f'部位名称{item[3]}不存在')
            if not equip_fault:
                raise ValidationError(f'故障分类{item[7]}不存在')
            if not equip_job_item_standard:
                raise ValidationError(f'作业项目{item[8]}不存在')

            lst = [i[0] for i in data]
            if lst.count(item[0]) > 1:
                raise ValidationError('导入的物料编码不能重复')

            if not EquipRepairStandard.objects.filter(Q(Q(standard_code=item[0]) | Q(standard_name=item[1]))).exists():
                signal_list.append({"standard_code": item[0],
                                    "standard_name": item[1],
                                    "equip_type": equip_type.id,
                                    "equip_part": equip_part.id,
                                    "equip_component": equip_component.id if equip_component else None,
                                    "equip_condition": item[5],
                                    "important_level": item[6],
                                    "equip_fault": equip_fault.id,
                                    "equip_job_item_standard": equip_job_item_standard.id,
                                    "cycle_person_num": item[9] if item[9] else None,
                                    "operation_time": item[10] if item[10] else None,
                                    "operation_time_unit": item[11],
                                    "remind_flag1": True,
                                    "remind_flag2": True,
                                    "remind_flag3": False,
                                    "spares": item[12] if item[12] else 'no',  # '清洁剂',
                                    })

        serializer = EquipRepairStandardImportSerializer(data=signal_list, many=True, context={'request': request})
        if serializer.is_valid(raise_exception=True):
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
                obj = EquipRepairStandard.objects.create(**data)
                for spare_obj in spare_obj_list:
                    EquipRepairStandardMaterials.objects.create(equip_repair_standard=obj,
                                                                     equip_spare_erp=spare_obj,
                                                                     quantity=1)  # 默认1
        else:
            raise ValidationError('导入的数据类型有误')
        return Response('导入成功')

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
# class EquipWarehouseAreaViewSet(ModelViewSet):
#     """
#     list: 库区展示
#     create: 添加库区
#     update: 修改库区信息
#     delete: 删除库区
#     """
#     queryset = EquipWarehouseArea.objects.filter(use_flag=1)
#     serializer_class = EquipWarehouseAreaSerializer
#     pagination_class = None
#     permission_classes = (IsAuthenticated,)
#
#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         # 库位有货物时, 不可删除
#         locations = EquipWarehouseLocation.objects.filter(equip_warehouse_area=instance.id)
#
#         if instance.use_flag:
#             instance.use_flag = 0
#         else:
#             instance.use_flag = 1
#         instance.last_updated_user = request.user
#         instance.save()
#         return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name='dispatch')
class GetDefaultCodeView(APIView):
    # permission_classes = (IsAuthenticated, )

    def get(self, request):
        work_type = self.request.query_params.get('work_type')
        if work_type == '部件':
            max_standard_code = EquipComponent.objects.filter(component_code__startswith='BJ').aggregate(max_code=Max('component_code'))['max_code']
            next_standard_code = max_standard_code[:2] + '%04d' % (int(max_standard_code[2:]) + 1) if max_standard_code and max_standard_code[2:].isdigit() else 'BJ0001'
        elif work_type in ['巡检', '维修', '保养', '润滑', '标定']:
            map_dict = {'巡检': 'XJ', '维修': 'WX', '保养': 'BY', '润滑': 'RH', '标定': 'BD'}
            prefix = map_dict.get(work_type)
            max_standard_code = EquipJobItemStandard.objects.filter(work_type=work_type, standard_code__startswith=prefix).aggregate(max_code=Max('standard_code'))['max_code']
            next_standard_code = prefix + '%04d' % (int(max_standard_code[2:]) + 1) if max_standard_code and max_standard_code[2:].isdigit() else prefix + '0001'
        elif work_type == '故障':
            equip_fault_type = self.request.query_params.get('equip_fault_type')
            max_standard_code = EquipFault.objects.filter(equip_fault_type__fault_type_code=equip_fault_type,
                                                          fault_code__startswith=equip_fault_type).aggregate(max_code=Max('fault_code'))['max_code']
            next_standard_code = equip_fault_type + '%04d' % (int(max_standard_code[len(equip_fault_type):]) + 1) if max_standard_code and max_standard_code[len(equip_fault_type):].isdigit() else equip_fault_type + '0001'
        elif work_type == '停机':
            equip_machine_halt_type = self.request.query_params.get('equip_machine_halt_type')
            max_standard_code = EquipMachineHaltReason.objects.filter(equip_machine_halt_type__machine_halt_type_code=equip_machine_halt_type,
                                                                      machine_halt_reason_code__startswith=equip_machine_halt_type).aggregate(
                max_code=Max('machine_halt_reason_code'))['max_code']
            next_standard_code = equip_machine_halt_type + '%04d' % (int(max_standard_code[len(equip_machine_halt_type):]) + 1) if max_standard_code and max_standard_code[len(equip_machine_halt_type):].isdigit() else equip_machine_halt_type + '0001'
        elif work_type == '信号':
            max_standard_code = EquipFaultSignal.objects.filter(signal_code__startswith='IO').aggregate(max_code=Max('signal_code'))['max_code']
            next_standard_code = max_standard_code[:2] + '%04d' % (int(max_standard_code[2:]) + 1) if max_standard_code and max_standard_code[2:].isdigit() else 'IO0001'
        elif work_type == '部位':
            max_standard_code = EquipPartNew.objects.filter(part_code__startswith='BW').aggregate(max_code=Max('part_code'))['max_code']
            next_standard_code = max_standard_code[:2] + '%04d' % (int(max_standard_code[2:]) + 1) if max_standard_code and max_standard_code[2:].isdigit() else 'BW0001'
        else:
            raise ValidationError('该类型默认编码暂未提供')
        return Response(next_standard_code)

