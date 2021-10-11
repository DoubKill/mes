import copy
import datetime as dt
import uuid

from django.db.models import F, Min, Max, Sum, Avg
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
    EquipFaultSignalFilter, EquipMachineHaltTypeFilter, EquipMachineHaltReasonFilter, EquipOrderAssignRuleFilter
from equipment.models import EquipFaultType, EquipFault, PropertyTypeNode, Property, PlatformConfig, EquipProperty, \
    EquipSupplier, EquipAreaDefine, EquipPartNew, EquipComponentType, EquipComponent, ERPSpareComponentRelation, \
    EquipSpareErp, EquipTargetMTBFMTTRSetting
from equipment.serializers import *
from equipment.task import property_template, property_import
from mes.common_code import OMin, OMax, OSum, CommonDeleteMixin
from mes.derorators import api_recorder
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.response import Response
from django.db.transaction import atomic
from rest_framework.decorators import action

# Create your views here.

from rest_framework.viewsets import ModelViewSet

from basics.models import Equip, GlobalCode
from equipment.serializers import EquipRealtimeSerializer
from mes.paginations import SinglePageNumberPagination


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
    queryset = EquipSupplier.objects.filter(delete_flag=False).order_by('-id')
    serializer_class = EquipSupplierSerializer
    # permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipSupplierFilter


@method_decorator([api_recorder], name="dispatch")
class EquipPropertyViewSet(CommonDeleteMixin, ModelViewSet):
    """设备固定资产台账"""
    queryset = EquipProperty.objects.filter(delete_flag=False).order_by('-id')
    serializer_class = EquipPropertySerializer
    # permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipPropertyFilter

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


@method_decorator([api_recorder], name='dispatch')
class EquipAreaDefineViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipAreaDefine.objects.filter(delete_flag=False).order_by('-id')
    serializer_class = EquipAreaDefineSerializer
    # permission_classes = (IsAuthenticated)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipAreaDefineFilter


@method_decorator([api_recorder], name="dispatch")
class EquipPartNewViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipPartNew.objects.all().order_by('-id')
    serializer_class = EquipPartNewSerializer
    # permission_classes = (IsAuthenticated)
    filter_backends = (DjangoFilterBackend, )
    filter_class = EquipPartNewFilter


@method_decorator([api_recorder], name="dispatch")
class EquipComponentTypeViewSet(CommonDeleteMixin, ModelViewSet):
    """设备部件分类"""
    queryset = EquipComponentType.objects.all()
    serializer_class = EquipComponentTypeSerializer
    # permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipComponentTypeFilter


@method_decorator([api_recorder], name='dispatch')
class EquipComponentViewSet(ModelViewSet):
    """
    list:
        展示所有设备部件定义
    create:
        新建部件定义
    update:
        修改部件定义
    """
    queryset = EquipComponent.objects.all()
    pagination_class = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)

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
            filter_kwargs['equip_part__equip_type__category_name__icontains'] = equip_type
        if equip_part:
            filter_kwargs['equip_part__part_name__icontains'] = equip_part
        if equip_component_type:
            filter_kwargs['equip_component_type__component_type_name__icontains'] = equip_component_type
        if component_name:
            filter_kwargs['component_name__icontains'] = component_name
        if is_binding:
            filter_kwargs['equip_components__isnull'] = False if is_binding == 'Y' else True
        if use_flag:
            filter_kwargs['use_flag'] = use_flag
        query_set = self.queryset.filter(**filter_kwargs)
        return query_set

    def get_serializer_class(self):
        if self.action == 'list':
            return EquipComponentListSerializer
        return EquipComponentCreateSerializer


@method_decorator([api_recorder], name='dispatch')
class ERPSpareComponentRelationViewSet(ModelViewSet):
    """
    list:
        部件erp备件关系
    create:
        新增部件与备件erp绑定关系
    """
    queryset = ERPSpareComponentRelation.objects.all()
    pagination_class = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ERPSpareComponentRelationFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return ERPSpareComponentRelationCreateSerializer
        return ERPSpareComponentRelationListSerializer


@method_decorator([api_recorder], name='dispatch')
class EquipSpareErpViewSet(ModelViewSet):
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
    pagination_class = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipSpareErpFilter

    def get_serializer_class(self):
        if self.action == 'list':
            return EquipSpareErpListSerializer
        return EquipSpareErpCreateSerializer


# @method_decorator([api_recorder], name='dispatch')
# class EquipBomViewSet(ModelViewSet):
#     """
#         list:
#             设备bom信息
#         create:
#             新建备件代码定义
#         update:
#             编辑、停用备件代码定义
#         retrieve:
#             备件代码定义详情
#         """
#     queryset = EquipBom.objects.all()
#     # pagination_class = (IsAuthenticated,)
#     filter_backends = (DjangoFilterBackend,)
#     filter_class = EquipBomFilter


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
    filter_backends = (DjangoFilterBackend,)
    pagination_class = SinglePageNumberPagination
    filter_class = EquipFaultCodeFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.filter(use_flag=1, equip_fault_type__use_flag=1).values('id', 'fault_code', 'fault_name',
                                                                                    'equip_fault_type__fault_type_name')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)

    def get_permissions(self):
        if self.request.query_params.get('all'):
            return ()
        else:
            return (IsAuthenticated(),)


@method_decorator([api_recorder], name="dispatch")
class EquipFaultSignalViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipFaultSignal.objects.all()
    serializer_class = EquipFaultSignalSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipFaultSignalFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'signal_name', 'signal_code')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)


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
    queryset = EquipMachineHaltReason.objects.order_by("id")
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


@method_decorator([api_recorder], name="dispatch")
class EquipTargetMTBFMTTRSettingView(APIView):

    def get(self, request):
        return Response(EquipTargetMTBFMTTRSetting.objects.values('id', 'equip', 'equip__equip_no', 'equip__equip_name', 'target_mtb', 'target_mttr'))

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
class EquipMaintenanceAreaSettingViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = EquipMaintenanceAreaSetting.objects.filter(delete_flag=False).order_by("id")
    serializer_class = EquipMaintenanceAreaSettingSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('maintenance_user_id', )
