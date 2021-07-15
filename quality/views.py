import datetime
import json
import os
from decimal import Decimal

from suds.client import Client
from django.db import connection
from django.forms import model_to_dict
from django.utils import timezone
from datetime import timedelta
from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet

from basics.models import GlobalCodeType
from basics.serializers import GlobalCodeSerializer
import uuid
from mes import settings
from mes.common_code import CommonDeleteMixin, date_range, get_template_response
from mes.paginations import SinglePageNumberPagination
from mes.derorators import api_recorder
from mes.permissions import PermissionClass
from production.models import PalletFeedbacks, TrainsFeedbacks
from quality.deal_result import receive_deal_result
from quality.filters import TestMethodFilter, DataPointFilter, \
    MaterialTestMethodFilter, MaterialDataPointIndicatorFilter, MaterialTestOrderFilter, MaterialDealResulFilter, \
    DealSuggestionFilter, PalletFeedbacksTestFilter, UnqualifiedDealOrderFilter, MaterialExamineTypeFilter, \
    ExamineMaterialFilter, MaterialEquipFilter, MaterialExamineResultFilter, MaterialReportEquipFilter, \
    MaterialReportValueFilter, ProductReportEquipFilter, ProductReportValueFilter
from quality.models import TestIndicator, MaterialDataPointIndicator, TestMethod, MaterialTestOrder, \
    MaterialTestMethod, TestType, DataPoint, DealSuggestion, MaterialDealResult, LevelResult, MaterialTestResult, \
    LabelPrint, TestDataPoint, BatchMonth, BatchDay, BatchProductNo, BatchEquip, BatchClass, UnqualifiedDealOrder, \
    MaterialExamineResult, MaterialExamineType, MaterialExamineRatingStandard, ExamineValueUnit, ExamineMaterial, \
    DataPointStandardError, MaterialSingleTypeExamineResult, MaterialEquipType, MaterialEquip, \
    UnqualifiedMaterialProcessMode, QualifiedRangeDisplay, IgnoredProductInfo, MaterialReportEquip, MaterialReportValue, \
    ProductReportEquip, ProductReportValue

from quality.serializers import MaterialDataPointIndicatorSerializer, \
    MaterialTestOrderSerializer, MaterialTestOrderListSerializer, \
    MaterialTestMethodSerializer, TestMethodSerializer, TestTypeSerializer, DataPointSerializer, \
    DealSuggestionSerializer, DealResultDealSerializer, MaterialDealResultListSerializer, LevelResultSerializer, \
    TestIndicatorSerializer, LabelPrintSerializer, BatchMonthSerializer, BatchDaySerializer, \
    BatchCommonSerializer, BatchProductNoDaySerializer, BatchProductNoMonthSerializer, \
    UnqualifiedDealOrderCreateSerializer, UnqualifiedDealOrderSerializer, UnqualifiedDealOrderUpdateSerializer, \
    MaterialDealResultListSerializer1, ExamineMaterialSerializer, MaterialExamineTypeSerializer, \
    ExamineValueUnitSerializer, MaterialExamineResultMainSerializer, DataPointStandardErrorSerializer, \
    MaterialEquipTypeSerializer, MaterialEquipSerializer, MaterialEquipTypeUpdateSerializer, \
    ExamineMaterialCreateSerializer, UnqualifiedMaterialProcessModeSerializer, IgnoredProductInfoSerializer, \
    MaterialExamineResultMainCreateSerializer, MaterialReportEquipSerializer, MaterialReportValueSerializer, \
    MaterialReportValueCreateSerializer, ProductReportEquipSerializer, ProductReportValueViewSerializer

from django.db.models import Prefetch
from django.db.models import Q
from quality.utils import print_mdr, get_cur_sheet, get_sheet_data, export_mto
from recipe.models import Material, ProductBatching
from django.db.models import Max, Sum, Avg


@method_decorator([api_recorder], name="dispatch")
class TestIndicatorViewSet(ModelViewSet):
    """试验指标列表"""
    queryset = TestIndicator.objects.filter(delete_flag=False)
    serializer_class = TestIndicatorSerializer

    def list(self, request, *args, **kwargs):
        data = self.queryset.values('id', 'name')
        return Response(data)


@method_decorator([api_recorder], name="dispatch")
class TestTypeViewSet(ModelViewSet):
    """试验类型管理"""
    queryset = TestType.objects.filter(delete_flag=False)
    serializer_class = TestTypeSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('test_indicator',)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'name')
            return Response({'results': data})
        return super().list(self, request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class DataPointViewSet(ModelViewSet):
    """试验类型数据点管理"""
    queryset = DataPoint.objects.filter(delete_flag=False)
    serializer_class = DataPointSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = DataPointFilter
    pagination_class = None

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'name', 'unit')
            return Response({'results': data})
        return super().list(self, request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class DataPointStandardErrorViewSet(ModelViewSet):
    """数据点误差(不合格pass指标管理)"""
    queryset = DataPointStandardError.objects.filter(delete_flag=False)
    serializer_class = DataPointStandardErrorSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('data_point_id',)
    pagination_class = None


@method_decorator([api_recorder], name="dispatch")
class DataPointLabelHistoryView(APIView):
    """标记历史记录"""

    def get(self, request):
        return Response(set(DataPointStandardError.objects.values_list('label', flat=True)))


@method_decorator([api_recorder], name="dispatch")
class TestMethodViewSet(ModelViewSet):
    """试验方法管理"""
    queryset = TestMethod.objects.filter(delete_flag=False)
    serializer_class = TestMethodSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = TestMethodFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'name')
            return Response({'results': data})
        return super().list(self, request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class TestIndicatorDataPointListView(ListAPIView):
    """获取试验指标及其所有的试验方法数据点"""
    queryset = TestIndicator.objects.filter(delete_flag=False)

    def list(self, request, *args, **kwargs):
        ret = []
        test_indicators_names = ['门尼', '比重', '硬度', '流变', '钢拔']
        for name in test_indicators_names:
            test_indicator = TestIndicator.objects.filter(name__icontains=name).first()
            if test_indicator:
                data_indicator_detail = []
                data_names = DataPoint.objects.filter(
                    test_type__test_indicator=test_indicator).order_by('name').values_list('name', flat=True)
                for data_name in data_names:
                    if data_name not in data_indicator_detail:
                        data_indicator_detail.append(data_name)
                data = {'test_type_id': test_indicator.id,
                        'test_type_name': test_indicator.name,
                        'data_indicator_detail': data_indicator_detail
                        }
                ret.append(data)
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class MaterialTestIndicatorMethods(APIView):
    """获取原材料指标试验方法"""

    def get(self, request):
        material_no = self.request.query_params.get('material_no')
        try:
            material = Material.objects.get(material_no=material_no)
        except Exception:
            raise ValidationError('该胶料不存在')
        ret = {}
        test_indicator_names = TestIndicator.objects.values_list('name', flat=True)
        test_methods = TestMethod.objects.all()
        for test_method in test_methods:
            indicator_name = test_method.test_type.test_indicator.name
            allowed = True
            data_points = None
            mat_test_method = MaterialTestMethod.objects.filter(
                material=material,
                test_method=test_method).first()
            if not mat_test_method:
                allowed = False
            else:
                if not MaterialDataPointIndicator.objects.filter(material_test_method=mat_test_method).exists():
                    allowed = False
                else:
                    data_points = mat_test_method.data_point.values('id', 'name', 'unit')
            if indicator_name not in ret:
                data = {
                    'test_indicator': indicator_name,
                    'methods': [
                        {'id': test_method.id,
                         'name': test_method.name,
                         'allowed': allowed,
                         'data_points': data_points}
                    ]
                }
                ret[indicator_name] = data
            else:
                ret[indicator_name]['methods'].append(
                    {'id': test_method.id, 'name': test_method.name, 'allowed': allowed, 'data_points': data_points})

        for item in test_indicator_names:
            if item not in ret:
                ret[item] = {'test_indicator': item, 'methods': []}
        return Response(ret.values())


@method_decorator([api_recorder], name="dispatch")
class MaterialTestOrderViewSet(mixins.CreateModelMixin,
                               mixins.ListModelMixin,
                               GenericViewSet):
    """
    list:
        列表展示
    create:
        手工录入数据
    """
    queryset = MaterialTestOrder.objects.filter(
        delete_flag=False).prefetch_related(
        'order_results').order_by('-production_factory_date',
                                  '-production_class',
                                  'production_equip_no',
                                  'product_no',
                                  'actual_trains')
    serializer_class = MaterialTestOrderSerializer
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (IsAuthenticated,)
    filter_class = MaterialTestOrderFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return MaterialTestOrderSerializer
        else:
            return MaterialTestOrderListSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        if not isinstance(data, list):
            raise ValidationError('参数错误')
        for item in data:
            s = MaterialTestOrderSerializer(data=item, context={'request': request})
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        return Response('新建成功')


@method_decorator([api_recorder], name="dispatch")
class MaterialTestMethodViewSet(ModelViewSet):
    """物料试验方法"""
    queryset = MaterialTestMethod.objects.filter(delete_flag=False)
    serializer_class = MaterialTestMethodSerializer
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (IsAuthenticated,)
    filter_class = MaterialTestMethodFilter


@method_decorator([api_recorder], name="dispatch")
class MaterialDataPointIndicatorViewSet(ModelViewSet):
    """物料数据点评判指标"""
    queryset = MaterialDataPointIndicator.objects.filter(delete_flag=False)
    serializer_class = MaterialDataPointIndicatorSerializer
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (IsAuthenticated,)
    filter_class = MaterialDataPointIndicatorFilter
    pagination_class = None


@method_decorator([api_recorder], name="dispatch")
class ProductBatchingMaterialListView(ListAPIView):
    """胶料原材料列表，（可根据生产信息过滤）"""
    queryset = Material.objects.filter(delete_flag=False)

    def list(self, request, *args, **kwargs):
        m_type = self.request.query_params.get('type', '1')  # 1胶料  2原材料
        factory_date = self.request.query_params.get('factory_date')  # 工厂日期
        equip_no = self.request.query_params.get('equip_no')  # 设备编号
        classes = self.request.query_params.get('classes')  # 班次

        batching_no = set(ProductBatching.objects.values_list('stage_product_batch_no', flat=True))
        if m_type == '1':
            kwargs = {}
            if factory_date:
                kwargs['factory_date'] = factory_date
            if equip_no:
                kwargs['equip_no'] = equip_no
            if classes:
                kwargs['classes'] = classes
            if kwargs:
                batching_no = TrainsFeedbacks.objects.filter(**kwargs).values_list('product_no', flat=True)
            material_data = self.queryset.filter(
                material_no__in=batching_no).values('id', 'material_no', 'material_name')
        elif m_type == '2':
            material_data = self.queryset.exclude(
                material_no__in=batching_no).values('id', 'material_no', 'material_name')
        else:
            raise ValidationError('参数错误')
        return Response(material_data)


@method_decorator([api_recorder], name="dispatch")
class DealSuggestionViewSet(CommonDeleteMixin, ModelViewSet):
    """处理意见
        list: 查询处理意见列表
        retrive: 查询处理意见详情
        post: 新增处理意见
        put: 修改处理意见
    """
    queryset = DealSuggestion.objects.filter(delete_flag=False)
    serializer_class = DealSuggestionSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = DealSuggestionFilter
    pagination_class = SinglePageNumberPagination


@method_decorator([api_recorder], name="dispatch")
class MaterialDealResultViewSet(CommonDeleteMixin, ModelViewSet):
    """胶料处理结果
    list: 查询胶料处理结果列表
    post: 创建胶料处理结果
    put: 创建胶料处理结果
    """
    queryset = MaterialDealResult.objects.filter(~Q(deal_result="一等品")).filter(~Q(status="复测")).filter(
        delete_flag=False)
    serializer_class = DealResultDealSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialDealResulFilter


@method_decorator([api_recorder], name="dispatch")
class MaterialDealStatusListView(APIView):
    """胶料状态列表"""

    def get(self, request):
        filter_set = MaterialDealResult.objects.filter(delete_flag=False).values("status").annotate()
        return Response(filter_set)


@method_decorator([api_recorder], name="dispatch")
class DealTypeView(APIView):
    # 创建处理类型
    def post(self, request):
        data = request.data
        gct = GlobalCodeType.objects.filter(type_name="处理类型").first()
        if not gct:
            raise ValidationError("请先在基础信息管理下的公用代码管理内启用/创建'处理类型'")
        data.update(global_type=gct.id)
        serializer = GlobalCodeSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "ok"}, status=status.HTTP_201_CREATED)


@method_decorator([api_recorder], name="dispatch")
class MaterialDealResultUpdateValidTime(APIView):
    # 快检信息综合管理修改有效时间
    @atomic()
    def post(self, request):
        id = self.request.data.get('id', None)
        valid_time = self.request.data.get('valid_time', None)
        if not id or not valid_time:
            raise ValidationError('id或有效时间必传')
        MaterialDealResult.objects.filter(id=id).update(valid_time=valid_time)
        return Response('修改成功')


@method_decorator([api_recorder], name="dispatch")
class PalletFeedbacksTestListView(ModelViewSet):
    # 快检信息综合管里
    queryset = MaterialDealResult.objects.filter(delete_flag=False).order_by('lot_no')
    serializer_class = MaterialDealResultListSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = PalletFeedbacksTestFilter
    permission_classes = (IsAuthenticated, )

    def get_serializer_class(self):
        if self.action == 'list':
            return MaterialDealResultListSerializer1
        elif self.action == "retrieve":
            return MaterialDealResultListSerializer
        else:
            raise ValidationError('本接口只提供查询功能')

    def get_queryset(self):
        equip_no = self.request.query_params.get('equip_no', None)
        product_no = self.request.query_params.get('product_no', None)
        day_time = self.request.query_params.get('day_time', None)
        classes = self.request.query_params.get('classes', None)
        schedule_name = self.request.query_params.get('schedule_name', None)
        is_print = self.request.query_params.get('is_print', None)
        filter_dict = {'delete_flag': False}
        pfb_filter = {}
        if day_time:
            pfb_filter['production_factory_date'] = day_time
        # if schedule_name:
        #     pcp_filter['work_schedule_plan__plan_schedule__work_schedule__schedule_name'] = schedule_name
        # if pcp_filter:
        #     pcp_uid_list = ProductClassesPlan.objects.filter(**pcp_filter).values_list('plan_classes_uid', flat=True)
        #     pfb_filter['plan_classes_uid__in'] = list(pcp_uid_list)

        if equip_no:
            pfb_filter['production_equip_no'] = equip_no
        if product_no:
            pfb_filter['product_no'] = product_no
        if classes:
            pfb_filter['production_class'] = classes
        if pfb_filter:
            pfb_product_list = MaterialTestOrder.objects.filter(**pfb_filter).values_list('lot_no', flat=True)
            filter_dict['lot_no__in'] = list(pfb_product_list)
        if is_print == "已打印":
            filter_dict['print_time__isnull'] = False
        elif is_print == "未打印":
            filter_dict['print_time__isnull'] = True
        pfb_queryset = MaterialDealResult.objects.filter(**filter_dict).exclude(status='复测').order_by('lot_no')
        return pfb_queryset


@method_decorator([api_recorder], name="dispatch")
class LevelResultViewSet(ModelViewSet):
    """等级和结果"""
    queryset = LevelResult.objects.filter(delete_flag=False)
    serializer_class = LevelResultSerializer
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (IsAuthenticated,)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        mdp_set = MaterialDataPointIndicator.objects.filter(level=instance.level, result=instance.deal_result,
                                                            delete_flag=False)
        if mdp_set:
            raise ValidationError('该等级已被使用，不能删除')
        instance.delete_flag = True
        instance.last_updated_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'deal_result', 'level')
            return Response({'results': data})
        return super().list(self, request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        deal_result = self.request.data.get('deal_result', None)
        level = self.request.data.get('level', None)
        if not deal_result or not level:
            raise ValidationError('等级和检测结果必传')
        lr_obj = LevelResult.objects.filter(deal_result=deal_result, level=level, delete_flag=False).first()
        if lr_obj:
            raise ValidationError('不可重复新建')
        lr_obj = LevelResult.objects.filter(deal_result=deal_result, level=level, delete_flag=True).first()
        if lr_obj:
            lr_obj.delete_flag = False
            lr_obj.save()
            return Response('新建成功')
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


@method_decorator([api_recorder], name="dispatch")
class ProductDayStatistics(APIView):
    """胶料日合格率统计"""

    def get(self, request, *args, **kwargs):
        params = request.query_params
        month_time = params.get('ym_time', datetime.datetime.now()).month
        year_time = params.get('ym_time', datetime.datetime.now()).year
        pass_type = params.get('pass_type', '1')  # 1:综合合格率  2：一次合格率  3：流变合格率
        pass_dict = {'1': ['门尼', '比重', '硬度', '流变'], '2': ['门尼', '比重', '硬度'], '3': ['流变']}
        test_indicator_name_dict = pass_dict[pass_type]
        product_no_list = MaterialTestOrder.objects.filter(delete_flag=False,
                                                           production_factory_date__year=year_time,
                                                           production_factory_date__month=month_time).values(
            'product_no').annotate().distinct()
        ruturn_pass = []
        for product_no_dict in product_no_list:
            return_dict = {}
            return_dict['product_no'] = product_no_dict['product_no']
            for day_time in range(1, int(datetime.datetime.now().day) + 1):
                lot_no_list = MaterialTestOrder.objects.filter(delete_flag=False,
                                                               production_factory_date__year=year_time,
                                                               production_factory_date__month=month_time,
                                                               production_factory_date__day=day_time,
                                                               **product_no_dict).values('lot_no').annotate().distinct()

                # mto_count = lot_no_list.count()
                mto_count = 0  # 粒度比等级综合判定更细，是基于每一车的。而不是每一托的
                if lot_no_list.count() == 0:
                    continue
                pass_count = 0

                for lot_no_dict in lot_no_list:
                    mto_set = MaterialTestOrder.objects.filter(delete_flag=False,
                                                               production_factory_date__year=year_time,
                                                               production_factory_date__month=month_time,
                                                               production_factory_date__day=day_time,
                                                               **product_no_dict, **lot_no_dict).all()
                    if not mto_set:
                        continue
                    mto_count += mto_set.count()
                    for mto_obj in mto_set:
                        level_list = []

                        mrt_list = mto_obj.order_results.filter(
                            test_indicator_name__in=test_indicator_name_dict).all().values('data_point_name').annotate(
                            max_test_time=Max('test_times'))
                        for mrt_dict in mrt_list:
                            mrt_dict_obj = MaterialTestResult.objects.filter(material_test_order=mto_obj,
                                                                             data_point_name=mrt_dict[
                                                                                 'data_point_name'],
                                                                             test_times=mrt_dict[
                                                                                 'max_test_time']).last()
                            level_list.append(mrt_dict_obj)
                        quality_sign = True
                        for mtr_obj in level_list:
                            if not mtr_obj.mes_result:  # mes没有数据
                                if not mtr_obj.result:  # 快检也没有数据
                                    quality_sign = False
                                elif mtr_obj.result != '一等品':
                                    quality_sign = False

                            elif mtr_obj.mes_result == '一等品':
                                if mtr_obj.result not in ['一等品', None]:
                                    quality_sign = False

                            elif mtr_obj.mes_result != '一等品':
                                quality_sign = False

                        if quality_sign:
                            pass_count += 1
                percent_of_pass = str((pass_count / mto_count) * 100) + '%'
                return_dict[f'{month_time}-{day_time}'] = percent_of_pass
            ruturn_pass.append(return_dict)
        return Response(ruturn_pass)


@method_decorator([api_recorder], name="dispatch")
class LabelPrintViewSet(mixins.CreateModelMixin,
                        mixins.UpdateModelMixin,
                        GenericViewSet):
    """
    list: 获取一条打印标签
    create: 存储一条打印标签
    """
    queryset = LabelPrint.objects.all()
    serializer_class = LabelPrintSerializer
    # permission_classes = (IsAuthenticated, )

    def create(self, request, *args, **kwargs):
        lot_no_list = request.data.get('lot_no')
        if not isinstance(lot_no_list, list):
            raise ValidationError('数据格式错误！')
        for lot_no in lot_no_list:
            data = receive_deal_result(lot_no)
            data = json.loads(data)
            data['test']['test_user'] = self.request.user.username
            LabelPrint.objects.create(label_type=2, lot_no=lot_no, status=2, data=json.dumps(data))
        return Response('打印任务已下发')

    def list(self, request, *args, **kwargs):
        station_dict = {
            "收皮": 1,
            "快检": 2,
            "一层前端": 3,
            "一层后端": 4,
            "二层前端": 5,
            "二层后端": 6,
            "炼胶#出库口#1": 7,
            "炼胶#出库口#2": 8,
            "炼胶#出库口#3": 9,
            "帘布#出库口#0": 10
        }
        station = request.query_params.get("station")
        instance = self.get_queryset().filter(label_type=station_dict.get(station), status=2).order_by('id').first()
        if instance:
            serializer = self.get_serializer(instance)
            data = serializer.data
        else:
            data = {}
        if data:
            data["data"] = json.loads(data.get("data"))
        return Response(data)

    @atomic()
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data if request.data else {"status": 1}
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        MaterialDealResult.objects.filter(lot_no=instance.lot_no).update(print_time=datetime.datetime.now())
        return Response("打印完成")


@method_decorator([api_recorder], name="dispatch")
class DealSuggestionView(APIView):
    """处理意见展示"""

    def get(self, request, *args, **kwargs):
        queryset = DealSuggestion.objects.filter(delete_flag=False).values('suggestion_desc').annotate().distinct()
        return Response(queryset.values_list('suggestion_desc', flat=True))


@method_decorator([api_recorder], name="dispatch")
class MaterialTestResultHistoryView(APIView):
    """试验结果数据展开列表， 参数：?test_order_id=检测单id"""

    def get(self, request):
        test_order_id = self.request.query_params.get('test_order_id')
        try:
            test_order = MaterialTestOrder.objects.get(id=test_order_id)
        except Exception:
            raise ValidationError('参数错误')
        data = MaterialTestResult.objects.filter(material_test_order=test_order).all()
        max_test_times = MaterialTestResult.objects.filter(material_test_order=test_order
                                                           ).aggregate(max_time=Max('test_times'))['max_time']
        ret = {i: {} for i in range(1, max_test_times + 1)}

        for item in data:
            indicator_name = item.test_indicator_name
            data_point_name = item.data_point_name
            test_times = item.test_times
            test_result = {
                'value': item.value,
                'result': item.result,
                'mes_result': item.mes_result,
                'machine_name': item.machine_name,
                'level': item.level,
                'test_times': item.test_times
            }
            if indicator_name not in ret[test_times]:
                ret[test_times][indicator_name] = {data_point_name: test_result}
            else:
                ret[test_times][indicator_name][data_point_name] = test_result
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class ProductDayDetail(APIView):
    """胶料日合格率详细信息统计"""

    # 伪代码
    def get(self, request, *args, **kwargs):
        params = request.query_params
        month_time = params.get('ym_time', datetime.datetime.now()).month
        year_time = params.get('ym_time', datetime.datetime.now()).year
        product_no = params.get('product_no', 'C-FM-UC109-001')
        pass_dict = {'1': ['门尼', '比重', '硬度', '流变'], '2': ['门尼', '比重', '硬度'], '3': ['流变']}
        name_dict = {'1': '综合合格率', '2': '一次合格率', '3': '流变合格率'}

        ruturn_pass = []
        return_dict = {}

        for day_time in range(1, int(datetime.datetime.now().day) + 1):
            # 1、胶料编码
            return_dict['product_no'] = product_no
            lot_no_list = MaterialTestOrder.objects.filter(delete_flag=False,
                                                           production_factory_date__year=year_time,
                                                           production_factory_date__month=month_time,
                                                           production_factory_date__day=day_time,
                                                           product_no=product_no).values('lot_no').annotate().distinct()

            mto_count = lot_no_list.count()
            if mto_count == 0:
                continue
            return_dict = {}
            # 2、当天的日期也要返回给前端
            return_dict['day_time'] = str(year_time) + '-' + str(month_time) + '-' + str(day_time)
            # 3、计算产量 车次
            plan_classes_uid_list = MaterialTestOrder.objects.filter(delete_flag=False,
                                                                     production_factory_date__year=year_time,
                                                                     production_factory_date__month=month_time,
                                                                     production_factory_date__day=day_time,
                                                                     product_no=product_no).values(
                'plan_classes_uid').annotate().distinct().values_list('plan_classes_uid', flat=True)
            tfb_train_list = TrainsFeedbacks.objects.filter(end_time__year=year_time, end_time__month=month_time,
                                                            end_time__day=day_time,
                                                            plan_classes_uid__in=plan_classes_uid_list).values(
                'plan_classes_uid').annotate(max_train=Max('actual_trains')).aggregate(sum_train=Sum('max_train'))
            return_dict['sum_train'] = tfb_train_list['sum_train']

            # 4、 循环三种指标类型，得到合格率
            for tin_key in pass_dict.keys():
                pass_count = 0
                test_indicator_name_dict = pass_dict[tin_key]

                for lot_no_dict in lot_no_list:
                    mto_set = MaterialTestOrder.objects.filter(delete_flag=False,
                                                               production_factory_date__year=year_time,
                                                               production_factory_date__month=month_time,
                                                               production_factory_date__day=day_time,
                                                               product_no=product_no, **lot_no_dict).all()
                    if not mto_set:
                        continue
                    level_list = []
                    for mto_obj in mto_set:
                        mrt_list = mto_obj.order_results.filter(
                            test_indicator_name__in=test_indicator_name_dict).all().values('data_point_name').annotate(
                            max_test_time=Max('test_times'))
                        for mrt_dict in mrt_list:
                            mrt_dict_obj = MaterialTestResult.objects.filter(material_test_order=mto_obj,
                                                                             data_point_name=mrt_dict[
                                                                                 'data_point_name'],
                                                                             test_times=mrt_dict[
                                                                                 'max_test_time']).last()
                            level_list.append(mrt_dict_obj)
                    quality_sign = True
                    for mtr_obj in level_list:
                        if not mtr_obj.mes_result:  # mes没有数据
                            if not mtr_obj.result:  # 快检也没有数据
                                quality_sign = False
                            elif mtr_obj.result != '一等品':
                                quality_sign = False

                        elif mtr_obj.mes_result == '一等品':
                            if mtr_obj.result not in ['一等品', None]:
                                quality_sign = False

                        elif mtr_obj.mes_result != '一等品':
                            quality_sign = False

                    if quality_sign:
                        pass_count += 1
                percent_of_pass = str((pass_count / mto_count) * 100) + '%'
                return_dict[name_dict[tin_key]] = percent_of_pass

            # 5、计算每个数据点超出的上下限
            point_count = {}
            point_upper = {}
            point_lower = {}
            for lot_no_dict in lot_no_list:
                mto_set = MaterialTestOrder.objects.filter(delete_flag=False,
                                                           production_factory_date__year=year_time,
                                                           production_factory_date__month=month_time,
                                                           production_factory_date__day=day_time,
                                                           product_no=product_no, **lot_no_dict).all()
                if not mto_set:
                    continue

                for mto_obj in mto_set:
                    mrt_list = mto_obj.order_results.filter().all().values('data_point_name').annotate(
                        max_test_time=Max('test_times'))

                    for mrt_dict in mrt_list:
                        level_list = []
                        mtr_obj = MaterialTestResult.objects.filter(material_test_order=mto_obj,
                                                                    data_point_name=mrt_dict[
                                                                        'data_point_name'],
                                                                    test_times=mrt_dict[
                                                                        'max_test_time']).last()
                        if not mtr_obj.data_point_indicator:
                            continue
                        if mrt_dict['data_point_name'] not in point_count.keys():
                            point_count[mrt_dict['data_point_name']] = 0
                        point_count[mrt_dict['data_point_name']] += 1
                        mdp_obj = MaterialDataPointIndicator.objects.filter(
                            material_test_method=mtr_obj.data_point_indicator.material_test_method,
                            data_point=mtr_obj.data_point_indicator.data_point, result='一等品').first()

                        if mtr_obj.data_point_indicator:
                            if mtr_obj.value > mdp_obj.upper_limit:
                                if mrt_dict['data_point_name'] not in point_upper.keys():
                                    point_upper[mrt_dict['data_point_name']] = 0
                                point_upper[mrt_dict['data_point_name']] += 1
                            elif mtr_obj.value < mdp_obj.lower_limit:
                                if mrt_dict['data_point_name'] not in point_lower.keys():
                                    point_lower[mrt_dict['data_point_name']] = 0
                                point_lower[mrt_dict['data_point_name']] += 1

            for point in point_count.keys():
                return_dict[point] = {}
                if point in point_upper.keys():
                    return_dict[point]['+'] = point_upper[point]
                    return_dict[point]['+%'] = str((point_upper[point] / point_count[point]) * 100) + '%'
                if point in point_lower.keys():
                    return_dict[point]['-'] = point_lower[point]
                    return_dict[point]['-%'] = str((point_lower[point] / point_count[point]) * 100) + '%'
            ruturn_pass.append(return_dict)
        return Response(ruturn_pass)


@method_decorator([api_recorder], name="dispatch")
class PrintMaterialDealResult(APIView):
    """不合格品打印功能"""

    def get(self, request, *args, **kwargs):
        day = self.request.query_params.get('day', None)
        status = self.request.query_params.get('status', None)
        filter_dict = {}
        if day:
            filter_dict['production_factory_date__icontains'] = day
        if status:
            filter_dict['status'] = status
        MaterialDealResult.objects.filter()
        mdr_set = MaterialDealResult.objects.filter(~Q(deal_result="一等品")).filter(~Q(status="复测")).filter(**filter_dict,
                                                                                                          delete_flag=False)
        return print_mdr("results", mdr_set)


# 1天
CACHE_TIME_TIMEOUT = 60 * 60 * 24


class AllMixin:

    # @cache_response(timeout=60 * 10, cache='default')
    def list(self, request, *args, **kwargs):
        if 'all' in self.request.query_params:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return super().list(request, *args, **kwargs)


def get_statics_query_dates(query_params):
    start_time = query_params.get('start_time')
    end_time = query_params.get('end_time')
    try:
        start_time = datetime.datetime.strptime(start_time, '%Y-%m') \
            if start_time else timezone.now() - timedelta(days=365)
        end_time = datetime.datetime.strptime(end_time, '%Y-%m') \
            if end_time else timezone.now()
    except ValueError:
        raise ValidationError('日期格式:yyyy-mm')
    return start_time, end_time


@method_decorator([api_recorder, cache_page(timeout=60 * 60 * 24 * 30, cache='default')], name="dispatch")
class BatchMonthStatisticsView(AllMixin, ReadOnlyModelViewSet):
    queryset = BatchMonth.objects.all()
    serializer_class = BatchMonthSerializer

    @action(detail=False)
    def statistic_headers(self, request):
        result = {
            'points': TestDataPoint.objects.values_list('name', flat=True).distinct(),
            'equips': BatchEquip.objects.values_list('production_equip_no', flat=True).distinct(),
            'classes': BatchClass.objects.values_list('production_class', flat=True).distinct()
        }
        return Response(result)

    def get_queryset(self):
        start_time, end_time = get_statics_query_dates(self.request.query_params)
        batches = BatchMonth.objects.filter(date__gte=start_time,
                                            date__lte=end_time)
        if batches:
            batches = BatchCommonSerializer.batch_annotate(batches)
            batches = batches.order_by('date')
        return batches


def get_statics_query_date(query_params):
    date = query_params.get('date')
    try:
        date = datetime.datetime.strptime(date, '%Y-%m') if date else timezone.now()
    except ValueError:
        raise ValidationError('日期格式:yyyy-mm')
    return date


@method_decorator([api_recorder, cache_page(timeout=CACHE_TIME_TIMEOUT, cache='default')], name="dispatch")
class BatchDayStatisticsView(AllMixin, ReadOnlyModelViewSet):
    queryset = BatchDay.objects.all()
    serializer_class = BatchDaySerializer

    def get_queryset(self):
        date = get_statics_query_date(self.request.query_params)
        batches = BatchDay.objects.filter(date__year=date.year,
                                          date__month=date.month)
        if batches:
            batches = BatchCommonSerializer.batch_annotate(batches)
            batches = batches.order_by('date')

        return batches


@method_decorator([api_recorder, cache_page(timeout=CACHE_TIME_TIMEOUT, cache='default')], name="dispatch")
class BatchProductNoDayStatisticsView(AllMixin, ReadOnlyModelViewSet):
    queryset = BatchProductNo.objects.all()
    serializer_class = BatchProductNoDaySerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ['product_no']

    def get_serializer_context(self):
        date = get_statics_query_date(self.request.query_params)
        context = super().get_serializer_context()
        context['date'] = date
        return context

    def get_queryset(self):
        date = get_statics_query_date(self.request.query_params)
        return BatchProductNo.objects.filter(
            batch__batch_month__date__year=date.year,
            batch__batch_month__date__month=date.month).distinct()


@method_decorator([api_recorder, cache_page(timeout=60 * 60 * 24 * 30, cache='default')], name="dispatch")
class BatchProductNoMonthStatisticsView(AllMixin, ReadOnlyModelViewSet):
    queryset = BatchProductNo.objects.all()
    serializer_class = BatchProductNoMonthSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ['product_no']

    def get_serializer_context(self):
        start_time, end_time = get_statics_query_dates(self.request.query_params)
        context = super().get_serializer_context()
        context['start_time'] = start_time
        context['end_time'] = end_time
        return context

    def get_queryset(self):
        start_time, end_time = get_statics_query_dates(self.request.query_params)
        return BatchProductNo.objects.filter(
            batch__batch_month__date__gte=start_time,
            batch__batch_month__date__lte=end_time).distinct()


@method_decorator([api_recorder], name="dispatch")
class UnqualifiedOrderTrains(APIView):
    """不合格车次汇总列表"""

    def get(self, request, *args, **kwargs):
        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.oracle':
            engine = 1
        else:
            engine = 2
        if engine == 2:
            where_str = 'where mtr.level>1'
        else:
            where_str = 'where mtr."LEVEL">1'
        st = self.request.query_params.get('st')
        if st:
            if engine == 2:
                where_str += " and date(mto.production_factory_date)>='{}'".format(st)
            else:
                where_str += " and to_char(mto.PRODUCTION_FACTORY_DATE, 'yyyy-mm-dd') >= '{}'".format(st)
        et = self.request.query_params.get('et')
        if et:
            if engine == 2:
                where_str += " and date(mto.production_factory_date)<='{}'".format(et)
            else:
                where_str += " and to_char(mto.PRODUCTION_FACTORY_DATE, 'yyyy-mm-dd') <= '{}'".format(st)

        classes = self.request.query_params.get('classes')
        if classes:
            where_str += " and mto.production_class='{}'".format(classes)
        product_no = self.request.query_params.get('product_no')
        if product_no:
            where_str += " and mto.product_no='{}'".format(product_no)
        if engine == 2:
            sql = """
            select
                   mto.production_factory_date,
                   mto.production_class,
                   mto.production_equip_no,
                   mto.product_no,
                   mto.actual_trains,
                   mtr.test_indicator_name,
                   mtr.data_point_name,
                   mtr.value,
                   mtr.material_test_order_id,
                   udod.id
            from material_test_result mtr
            inner join (select
                   material_test_order_id,
                   test_indicator_name,
                   data_point_name,
                    max(test_times) max_times
                from material_test_result
                group by test_indicator_name, data_point_name, material_test_order_id
                ) tmp on tmp.material_test_order_id=mtr.material_test_order_id
                             and tmp.data_point_name=mtr.data_point_name
                             and tmp.test_indicator_name=mtr.test_indicator_name
                             and tmp.max_times=mtr.test_times
            inner join material_test_order mto on mtr.material_test_order_id = mto.id
            left join unqualified_deal_order_detail udod on mto.id = udod.material_test_order_id
            {};""".format(where_str)
        else:
            sql = """
            select
                   mto.PRODUCTION_FACTORY_DATE,
                   mto.PRODUCTION_CLASS,
                   mto.PRODUCTION_EQUIP_NO,
                   mto.PRODUCT_NO,
                   mto.ACTUAL_TRAINS,
                   mtr.TEST_INDICATOR_NAME,
                   mtr.DATA_POINT_NAME,
                   mtr.VALUE,
                   mtr.MATERIAL_TEST_ORDER_ID,
                   udod.ID
            from MATERIAL_TEST_RESULT mtr
            inner join (
                select
                    MATERIAL_TEST_ORDER_ID,
                    TEST_INDICATOR_NAME,
                    DATA_POINT_NAME,
                    max(TEST_TIMES) as max_times
                from
                     MATERIAL_TEST_RESULT
                group by TEST_INDICATOR_NAME, DATA_POINT_NAME, MATERIAL_TEST_ORDER_ID
                ) tmp on tmp.MATERIAL_TEST_ORDER_ID=mtr.MATERIAL_TEST_ORDER_ID
                             and tmp.DATA_POINT_NAME=mtr.DATA_POINT_NAME
                             and tmp.TEST_INDICATOR_NAME=mtr.TEST_INDICATOR_NAME
                             and tmp.max_times=mtr.TEST_TIMES
            inner join MATERIAL_TEST_ORDER mto on mtr.MATERIAL_TEST_ORDER_ID = mto.ID
            left join UNQUALIFIED_DEAL_ORDER_DETAIL udod on mto.ID = udod.MATERIAL_TEST_ORDER_ID
            {};""".format(where_str)
        cursor = connection.cursor()
        cursor.execute(sql)
        data = cursor.fetchall()
        ret = {}
        form_head_data = set()
        for item in data:
            if item[-1]:
                continue
            item_key = datetime.datetime.strftime(item[0], '%Y-%m-%d') + '-' + item[1] + '-' + item[2] + '-' + item[3]
            data_point_key = item[6] if item[5] == '流变' else item[5]
            form_head_data.add(data_point_key)
            if item_key not in ret:
                ret[item_key] = {
                    'date': datetime.datetime.strftime(item[0], '%Y-%m-%d'),
                    'classes': item[1],
                    'equip_no': item[2],
                    'product_no': item[3],
                    'actual_trains': {item[4]},
                    'indicator_data': {data_point_key: [item[7]]},
                    'order_ids': {item[8]}
                }
            else:
                ret[item_key]['actual_trains'].add(item[4])
                ret[item_key]['order_ids'].add(item[8])
                if data_point_key not in ret[item_key]['indicator_data']:
                    ret[item_key]['indicator_data'][data_point_key] = [item[7]]
                else:
                    ret[item_key]['indicator_data'][data_point_key].append(item[7])
        return Response({'form_head_data': form_head_data,
                         'ret': ret.values()})


@method_decorator([api_recorder], name="dispatch")
class UnqualifiedDealOrderViewSet(ModelViewSet):
    """不合格处置"""
    queryset = UnqualifiedDealOrder.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filter_class = UnqualifiedDealOrderFilter

    def get_queryset(self):
        queryset = self.queryset
        reason = self.request.query_params.get('reason')
        t_deal_suggestion = self.request.query_params.get('t_deal_suggestion')
        c_deal_suggestion = self.request.query_params.get('c_deal_suggestion')
        if reason == 'true':  # 未处理
            queryset = queryset.filter(reason__isnull=True)
        elif reason == 'false':  # 已处理
            queryset = queryset.filter(reason__isnull=False)
        if t_deal_suggestion == 'true':  # 未处理
            queryset = queryset.filter(t_deal_suggestion__isnull=True)
        elif t_deal_suggestion == 'false':  # 已处理
            queryset = queryset.filter(t_deal_suggestion__isnull=False)
        if c_deal_suggestion == 'true':  # 未处理
            queryset = queryset.filter(c_deal_suggestion__isnull=True)
        elif c_deal_suggestion == 'false':  # 已处理
            queryset = queryset.filter(c_deal_suggestion__isnull=False)
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return UnqualifiedDealOrderCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UnqualifiedDealOrderUpdateSerializer
        else:
            return UnqualifiedDealOrderSerializer

    def retrieve(self, request, *args, **kwargs):
        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.oracle':
            engine = 1
        else:
            engine = 2
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        serializer_data = serializer.data
        order_ids = instance.deal_details.values_list('material_test_order_id', flat=True)
        create_data = datetime.datetime.strftime(instance.created_date, '%Y-%m-%d %H:%M:%S')
        if engine == 2:
            sql = """
                select
                       mto.production_factory_date,
                       mto.production_class,
                       mto.production_equip_no,
                       mto.product_no,
                       mto.actual_trains,
                       mtr.test_indicator_name,
                       mtr.data_point_name,
                       mtr.value,
                       mtr.material_test_order_id
                from material_test_result mtr
                inner join (select
                       material_test_order_id,
                       test_indicator_name,
                       data_point_name,
                        max(test_times) max_times
                    from material_test_result
                    where created_date<='{}'
                    group by test_indicator_name, data_point_name, material_test_order_id
                    ) tmp on tmp.material_test_order_id=mtr.material_test_order_id
                                 and tmp.data_point_name=mtr.data_point_name
                                 and tmp.test_indicator_name=mtr.test_indicator_name
                                 and tmp.max_times=mtr.test_times
                inner join material_test_order mto on mtr.material_test_order_id = mto.id
                where mtr.level>1 and mto.id in ({});
                """.format(create_data, ','.join([str(i) for i in order_ids]))
        else:
            sql = """
            select
                   mto.PRODUCTION_FACTORY_DATE,
                   mto.PRODUCTION_CLASS,
                   mto.PRODUCTION_EQUIP_NO,
                   mto.PRODUCT_NO,
                   mto.ACTUAL_TRAINS,
                   mtr.TEST_INDICATOR_NAME,
                   mtr.DATA_POINT_NAME,
                   mtr.VALUE
            from MATERIAL_TEST_RESULT mtr
            inner join (
                select
                    MATERIAL_TEST_ORDER_ID,
                    TEST_INDICATOR_NAME,
                    DATA_POINT_NAME,
                    max(TEST_TIMES) as max_times
                from
                     MATERIAL_TEST_RESULT
                where to_char(CREATED_DATE, 'yyyy-mm-dd HH24:mi:ss')<='{}'
                group by TEST_INDICATOR_NAME, DATA_POINT_NAME, MATERIAL_TEST_ORDER_ID
                ) tmp on tmp.MATERIAL_TEST_ORDER_ID=mtr.MATERIAL_TEST_ORDER_ID
                             and tmp.DATA_POINT_NAME=mtr.DATA_POINT_NAME
                             and tmp.TEST_INDICATOR_NAME=mtr.TEST_INDICATOR_NAME
                             and tmp.max_times=mtr.TEST_TIMES
            inner join MATERIAL_TEST_ORDER mto on mtr.MATERIAL_TEST_ORDER_ID = mto.ID
            where mtr."LEVEL">1 and mto.ID in ({});""".format(create_data, ','.join([str(i) for i in order_ids]))
        cursor = connection.cursor()
        cursor.execute(sql)
        data = cursor.fetchall()
        ret = {}
        form_head_data = set()
        for item in data:
            item_key = datetime.datetime.strftime(item[0], '%Y-%m-%d') + '-' + item[1] + '-' + item[2] + '-' + item[3]
            data_point_key = item[6] if item[5] == '流变' else item[5]
            form_head_data.add(data_point_key)
            if item_key not in ret:
                ret[item_key] = {
                    'date': datetime.datetime.strftime(item[0], '%Y-%m-%d'),
                    'classes': item[1],
                    'equip_no': item[2],
                    'product_no': item[3],
                    'actual_trains': {item[4]},
                    'indicator_data': {data_point_key: [item[7]]},
                }
            else:
                ret[item_key]['actual_trains'].add(item[4])
                if data_point_key not in ret[item_key]['indicator_data']:
                    ret[item_key]['indicator_data'][data_point_key] = [item[7]]
                else:
                    ret[item_key]['indicator_data'][data_point_key].append(item[7])
        serializer_data['form_head_data'] = form_head_data
        serializer_data['deal_details'] = ret.values()
        return Response(serializer_data)


@method_decorator([api_recorder], name="dispatch")
class DealMethodHistoryView(APIView):

    def get(self, request):
        return Response(set(UnqualifiedDealOrder.objects.filter(
            deal_method__isnull=False).values_list('deal_method', flat=True)))


@method_decorator([api_recorder], name="dispatch")
class TestDataPointCurveView(APIView):
    """胶料数据点检测值曲线"""

    def get(self, request):
        st = self.request.query_params.get('st')
        et = self.request.query_params.get('et')
        product_no = self.request.query_params.get('product_no')
        if not all([st, et, product_no]):
            raise ValidationError('参数缺失')
        try:
            days = date_range(datetime.datetime.strptime(st, '%Y-%m-%d'),
                              datetime.datetime.strptime(et, '%Y-%m-%d'))
        except Exception:
            raise ValidationError('参数错误')
        ret = MaterialTestResult.objects.filter(material_test_order__production_factory_date__gte=st,
                                                material_test_order__production_factory_date__lte=et,
                                                material_test_order__product_no=product_no
                                                ).values('material_test_order__production_factory_date',
                                                         'data_point_name').annotate(avg_value=Avg('value'))

        data_point_names = [item['data_point_name'] for item in ret]
        y_axis = {
            data_point_name: {
                'name': data_point_name,
                'type': 'line',
                'data': [0] * len(days)}
            for data_point_name in data_point_names
        }
        for item in ret:
            factory_date = item['material_test_order__production_factory_date'].strftime("%Y-%m-%d")
            data_point_name = item['data_point_name']
            avg_value = round(item['avg_value'], 2)
            y_axis[data_point_name]['data'][days.index(factory_date)] = avg_value
        indicators = {}
        for data_point_name in data_point_names:
            indicator = MaterialDataPointIndicator.objects.filter(
                data_point__name=data_point_name,
                material_test_method__material__material_name=product_no,
                level=1).first()
            if indicator:
                indicators[data_point_name] = [indicator.lower_limit, indicator.upper_limit]
        return Response(
            {'x_axis': days, 'y_axis': y_axis.values(), 'indicators': indicators}
        )


@method_decorator([api_recorder], name="dispatch")
class ImportAndExportView(APIView):
    """快检数据导入，一次只能导入同一批生产数据"""

    def get(self, request, *args, **kwargs):
        """快检数据导入模板"""
        return export_mto()

    @atomic()
    def post(self, request, *args, **kwargs):
        """快检数据导入"""
        file = request.FILES.get('file')
        cur_sheet = get_cur_sheet(file)
        data = get_sheet_data(cur_sheet, start_row=2)
        by_dict = {'MH': 7,
                   'ML': 8,
                   'TC10': 9,
                   'TC50': 10,
                   'TC90': 11,
                   '比重值': 12,
                   'ML(1+4)': 13,
                   '硬度值': 14,
                   'M300': 15,
                   '扯断强度': 16,
                   '伸长率': 17,
                   '焦烧': 18,
                   '钢拔': 19}
        # 取第一行数据
        try:
            production_data = data[0]
        except Exception:
            raise ValidationError('请填入检测数据后再导入！')
        # 胶料
        product_no = production_data[0].strip()
        # 密炼日期
        try:
            delta = datetime.timedelta(days=production_data[2])
            date_1 = datetime.datetime.strptime('1899-12-30', '%Y-%m-%d') + delta
            factory_date = datetime.datetime.strftime(date_1, '%Y-%m-%d')
        except Exception:
            raise ValidationError('密炼日期格式错误！')
        # 班次
        classes = production_data[3].strip() + '班'
        # 机台
        equip_no = production_data[4].strip()
        # 取数据点
        reverse_dict = {value: key for key, value in by_dict.items()}
        data_points = [reverse_dict.get(i) for i in range(7, 20) if production_data[i]]
        if not data_points:
            raise ValidationError('请填入检测数据后再导入！')
        data_point_method_map = {}
        for data_point_name in data_points:
            mtm = MaterialTestMethod.objects.filter(material__material_no=product_no,
                                                    data_point__name=data_point_name)
            if not mtm:
                raise ValidationError('该胶料{}不存在数据点{}试验方法！'.format(product_no, data_point_name))
            if mtm.count() > 1:
                raise ValidationError('该胶料{}存在多种数据点{}试验方法，请联系管理员！'.format(product_no, data_point_name))
            else:
                data_point_method_map[data_point_name] = mtm.values('id',
                                                                    'test_method__name',
                                                                    'test_method__test_type__test_indicator__name')[0]
                indicator = MaterialDataPointIndicator.objects.filter(
                    material_test_method=mtm.first(),
                    data_point__name=data_point_name,
                    data_point__test_type__test_indicator__name=mtm.first().test_method.test_type.test_indicator.name,
                    level=1
                ).first()
                if indicator:
                    data_point_method_map[data_point_name]['qualified_range'] = [indicator.lower_limit,
                                                                                 indicator.upper_limit]
        pallet_data = PalletFeedbacks.objects.filter(equip_no=equip_no,
                                                     factory_date=factory_date,
                                                     classes=classes,
                                                     product_no=product_no
                                                     ).values('lot_no', 'begin_trains',
                                                              'end_trains', 'plan_classes_uid')
        if not pallet_data:
            raise ValidationError('未找到该批次生产数据：【{}】-【{}】-【{}】-【{}】！！'.format(factory_date, classes, equip_no, product_no))
        pallet_trains_map = {}  # 车次与收皮条码map数据
        for pallet in pallet_data:
            for j in range(pallet['begin_trains'], pallet['end_trains']+1):
                pallet_trains_map[j] = {'lot_no': pallet['lot_no'],
                                        'plan_classes_uid': pallet['plan_classes_uid']}

        del j, data_points, pallet_data, production_data, reverse_dict

        for item in data:
            try:
                actual_trains = int(item[6])
            except Exception:
                raise ValidationError('车次数据错误！')
            if not pallet_trains_map.get(actual_trains):  # 未找到收皮条码
                continue
            lot_no = pallet_trains_map[actual_trains]['lot_no']
            plan_classes_uid = pallet_trains_map[actual_trains]['plan_classes_uid']
            test_order = MaterialTestOrder.objects.filter(lot_no=lot_no,
                                                          actual_trains=actual_trains
                                                          ).first()
            if test_order:
                instance = test_order
                created = False
            else:
                validated_data = dict()
                validated_data['material_test_order_uid'] = uuid.uuid1()
                validated_data['actual_trains'] = actual_trains
                validated_data['lot_no'] = lot_no
                validated_data['product_no'] = product_no
                validated_data['plan_classes_uid'] = plan_classes_uid
                validated_data['production_class'] = classes
                validated_data['production_equip_no'] = equip_no
                validated_data['production_factory_date'] = factory_date
                instance = MaterialTestOrder.objects.create(**validated_data)
                created = True
            for data_point_name, method in data_point_method_map.items():
                test_method_name = method['test_method__name']
                test_indicator_name = method['test_method__test_type__test_indicator__name']
                point_value = Decimal(item[by_dict[data_point_name]]).quantize(Decimal('0.000'))
                if not point_value:
                    continue
                result_data = {'material_test_order': instance,
                               'test_factory_date': datetime.datetime.now(),
                               'value': point_value,
                               'data_point_name': data_point_name,
                               'test_method_name': test_method_name,
                               'test_indicator_name': test_indicator_name,
                               'mes_result': '三等品',
                               'result': '三等品',
                               'level': 2,
                               }
                if method.get('qualified_range'):
                    if method['qualified_range'][0] <= point_value <= method['qualified_range'][1]:
                        result_data['mes_result'] = '一等品'
                        result_data['result'] = '一等品'
                        result_data['level'] = 1
                if created:
                    result_data['test_times'] = 1
                else:
                    last_test_result = MaterialTestResult.objects.filter(
                        material_test_order=instance,
                        test_indicator_name=test_indicator_name,
                        data_point_name=data_point_name,
                    ).order_by('-test_times').first()
                    if last_test_result:
                        result_data['test_times'] = last_test_result.test_times + 1
                    else:
                        result_data['test_times'] = 1
                MaterialTestResult.objects.create(**result_data)
        return Response('导入成功')


@method_decorator([api_recorder], name="dispatch")
class BarCodePreview(APIView):
    # 条码追溯中的条码预览接口
    def get(self, request):
        lot_no = request.query_params.get("lot_no")
        # try:
        instance = MaterialDealResult.objects.get(lot_no=lot_no)
        serializer = MaterialDealResultListSerializer(instance)
        return Response(serializer.data)
        # except Exception as e:
        #     raise ValidationError(f"该条码无快检结果:{e}")


@method_decorator([api_recorder], name="dispatch")
class ShowQualifiedRange(APIView):

    def get(self, request):
        instance = QualifiedRangeDisplay.objects.first()
        if instance:
            return Response({'is_showed': instance.is_showed})
        return Response({'is_showed': False})

    def post(self, request):
        is_showed = self.request.data.get('is_showed')
        if not isinstance(is_showed, bool):
            raise ValidationError('参数错误')
        instance = QualifiedRangeDisplay.objects.first()
        if not instance:
            QualifiedRangeDisplay.objects.create(is_showed=is_showed)
        else:
            instance.is_showed = is_showed
            instance.save()
        return Response('设置成功！')


@method_decorator([api_recorder], name="dispatch")
class IgnoredProductInfoViewSet(viewsets.GenericViewSet,
                                mixins.ListModelMixin,
                                mixins.CreateModelMixin,
                                mixins.DestroyModelMixin):
    """不做pass章的判定胶种"""
    queryset = IgnoredProductInfo.objects.all()
    serializer_class = IgnoredProductInfoSerializer
    permission_classes = (IsAuthenticated,)


@method_decorator([api_recorder], name="dispatch")
class ProductReportEquipViewSet(mixins.CreateModelMixin,
                                mixins.UpdateModelMixin,
                                mixins.ListModelMixin,
                                viewsets.GenericViewSet):
    """胶料上报设备管理"""
    queryset = ProductReportEquip.objects.all()
    serializer_class = ProductReportEquipSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductReportEquipFilter


@method_decorator([api_recorder], name="dispatch")
class ProductReportValueViewSet(mixins.CreateModelMixin,
                                mixins.ListModelMixin,
                                viewsets.GenericViewSet):
    """胶料设备数据上报"""
    permission_classes = (IsAuthenticated,)
    queryset = ProductReportValue.objects.filter(is_binding=False)
    serializer_class = ProductReportValueViewSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductReportValueFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        value_data = queryset.values('id', 'ip', 'value', 'created_date')
        equip_data = ProductReportEquip.objects.values('ip', 'data_point__test_type', 'no',
                                                       'data_point', 'data_point__name')
        equip_data_dict = {item['ip']: item for item in equip_data}
        ret = []
        for item in value_data:
            item['created_date'] = datetime.datetime.strftime(item['created_date'], '%Y-%m-%d %H:%M:%S')
            if item['ip'] in equip_data_dict:
                item['data_point_name'] = equip_data_dict[item['ip']]['data_point__name']
                item['test_type'] = equip_data_dict[item['ip']]['data_point__test_type']
                item['data_point'] = equip_data_dict[item['ip']]['data_point']
                item['report_equip_no'] = equip_data_dict[item['ip']]['no']
            ret.append(item)
        return Response(ret)

    def create(self, request, *args, **kwargs):
        data = request.data
        if not isinstance(data, list):
            raise ValidationError('参数错误')
        for item in data:
            s = ProductReportValueViewSerializer(data=item, context={'request': request})
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        return Response('新建成功！')


"""新原材料快检"""


@method_decorator([api_recorder], name="dispatch")
class ExamineValueUnitViewSet(viewsets.GenericViewSet,
                              mixins.ListModelMixin,
                              mixins.CreateModelMixin,
                              mixins.RetrieveModelMixin):
    """
    list:
        检测值单位列表
    create:
        新建检测值单位
    """
    queryset = ExamineValueUnit.objects.all()
    serializer_class = ExamineValueUnitSerializer
    pagination_class = SinglePageNumberPagination


class MaterialEquipTypeViewSet(viewsets.GenericViewSet,
                               mixins.ListModelMixin,
                               mixins.CreateModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.UpdateModelMixin):
    """
    list:
        检测设备类型列表
    create:
        创建检测设备类型
    update:
        修改检测设备类型
    """
    queryset = MaterialEquipType.objects.all()
    serializer_class = MaterialEquipTypeSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    pagination_class = None

    def get_serializer_class(self):
        if self.action == 'update':
            return MaterialEquipTypeUpdateSerializer
        return MaterialEquipTypeSerializer


class MaterialEquipViewSet(viewsets.GenericViewSet,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin):
    """
    list:
        检测设备列表
    create:
        创建检测设备
    update:
        修改检测设备
    """
    queryset = MaterialEquip.objects.all()
    serializer_class = MaterialEquipSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialEquipFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        examine_type_id = self.request.query_params.get('examine_type')
        if examine_type_id:
            try:
                examine_type = MaterialExamineType.objects.get(id=examine_type_id)
            except Exception:
                raise ValidationError('参数错误')
            data = queryset.filter(equip_type__examine_type=examine_type).values('id', 'equip_name')
            return Response({'results': data})
        return super().list(request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class MaterialExamineTypeViewSet(viewsets.GenericViewSet,
                                 mixins.ListModelMixin,
                                 mixins.CreateModelMixin,
                                 mixins.RetrieveModelMixin,
                                 mixins.UpdateModelMixin):
    """
    list:
        原材料检测类型列表
    create:
        创建原材料检测类型
    update:
        修改原材料检测类型
    """
    queryset = MaterialExamineType.objects.all().select_related("unit").prefetch_related('standards')
    serializer_class = MaterialExamineTypeSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialExamineTypeFilter
    titles = ["比值类型", "检测类型", "边界值", "单位", "上限值", "下限值", "级别"]
    description = "比值类型填 上下限, <=, >=, 外观确认"
    permission_classes = ()

    def get_permissions(self):
        if self.request.query_params.get('all'):  # 检测类型列表
            return ()
        elif self.request.query_params.get('types'):  # 比值类型列表
            return ()
        else:
            return (IsAuthenticated(),)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values("id", "name", 'interval_type', 'limit_value')
            for item in data:
                if item['interval_type'] == 1:
                    standard = MaterialExamineRatingStandard.objects.filter(level=1, examine_type=item['id']).first()
                    if standard:
                        item['qualified_range'] = [standard.lower_limiting_value, standard.upper_limit_value]
                elif item['interval_type'] == 2:
                    item['qualified_range'] = [None, item['limit_value']]
                elif item['interval_type'] == 3:
                    item['qualified_range'] = [item['limit_value'], None]
            return Response({'results': data})
        elif self.request.query_params.get('types'):
            qs = [{"id": x[0], "value": x[1]} for x in MaterialExamineType.INTERVAL_TYPES]
            return Response({'results': qs})
        else:
            return super().list(request, *args, **kwargs)

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated], url_path='export-template',
            url_name='export-template')
    def export_template(self, request):
        """资产导入模板"""

        filename = '原材料检测指标导入模板'
        return get_template_response(self.titles, filename=filename, description="比值类型填: 上下限, <=, >=, 外观确认")

    @action(methods=['post'], detail=False, permission_classes=[IsAuthenticated], url_path='import-data',
            url_name='import-data')
    def import_data(self, request):
        file = request.FILES.get('file')
        cur_sheet = get_cur_sheet(file)
        data = get_sheet_data(cur_sheet, start_row=2)
        interval_dict = {x[1]: x[0] for x in MaterialExamineType.INTERVAL_TYPES}
        for x in data:
            if x[3]:
                unit, tag = ExamineValueUnit.objects.get_or_create(name=x[3])
            else:
                unit = None
            temp = {
                "interval_type": interval_dict[x[0]],
                "limit_value": float(x[2]) if x[2] else None,
                "unit": unit
            }
            instance = MaterialExamineType.objects.get_or_create(defaults=temp, **{"name": x[1]})[0]
            if str(x[0]) == "上下限":
                MaterialExamineRatingStandard.objects.create(examine_type=instance, upper_limit_value=float(x[4]),
                                                             lower_limiting_value=float(x[5]), level=x[6])
        return Response("导入成功")


@method_decorator([api_recorder], name="dispatch")
class ExamineMaterialViewSet(viewsets.GenericViewSet,
                             mixins.CreateModelMixin,
                             mixins.ListModelMixin,
                             mixins.RetrieveModelMixin):
    """
    list:
        原材料列表
    create:
        创建原材料
    """
    queryset = ExamineMaterial.objects \
        .prefetch_related(Prefetch('examine_results',
                                   queryset=MaterialExamineResult.objects.order_by(
                                       '-examine_date', '-create_time'))
                          ).distinct().order_by('-create_time')
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ExamineMaterialFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return ExamineMaterialCreateSerializer
        return ExamineMaterialSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values("id", "name", 'sample_name', 'batch', 'supplier')
            return Response({'results': data})
        return super().list(request, *args, **kwargs)


class WMSMaterialSearchView(APIView):
    """根据条码号搜索中策总厂wms物料信息，参数:?tmh=BHZ12105311651140001"""

    def get(self, request):
        tmh = self.request.query_params.get('tmh')
        if not tmh:
            raise ValidationError('请输入条码号')
        url = 'http://10.1.10.157:9091/WebService.asmx?wsdl'
        try:
            client = Client(url)
            json_data = {"tofac": "AJ1", "tmh": tmh}
            data = client.service.FindZcdtmList(json.dumps(json_data))
        except Exception:
            raise ValidationError('网络异常！')
        data = json.loads(data)
        ret = data.get('Table')
        if not ret:
            raise ValidationError('未找到该条码对应物料信息！')
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class MaterialExamineResultViewSet(viewsets.GenericViewSet,
                                   mixins.CreateModelMixin,
                                   mixins.ListModelMixin,
                                   mixins.RetrieveModelMixin,
                                   mixins.UpdateModelMixin):
    """
    list:
        原材料检测结果列表
    create:
        创建原材料检测结果
    update:
        修改原材料检测结果
    """
    queryset = MaterialExamineResult.objects.all().select_related(
        "material", "recorder", "sampling_user").prefetch_related("single_examine_results").order_by('-id')
    serializer_class = MaterialExamineResultMainSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialExamineResultFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return MaterialExamineResultMainCreateSerializer
        return MaterialExamineResultMainSerializer

    def get_queryset(self):
        type_id = self.request.query_params.get('type_id')
        if type_id:
            result_ids = MaterialSingleTypeExamineResult.objects.filter(
                type_id=type_id).values_list('material_examine_result_id', flat=True)
            return self.queryset.filter(id__in=result_ids)
        return self.queryset


@method_decorator([api_recorder], name="dispatch")
class MaterialSingleTypeExamineResultView(APIView):
    """批次原材料不合格项，参数：material=原材料id"""

    def get(self, request):
        ret = {}
        material_id = self.request.query_params.get('material')
        if not material_id:
            raise ValidationError('参数缺失！')
        try:
            material = ExamineMaterial.objects.get(id=material_id)
        except Exception:
            raise ValidationError('该原材料不存在！')
        last_examine_result = MaterialExamineResult.objects.filter(material=material, qualified=False).last()
        material_data = model_to_dict(material)
        ret['material_data'] = material_data
        if last_examine_result:
            material_data['re_examine'] = last_examine_result.re_examine
            material_data['recorder_username'] = last_examine_result.recorder.username
            material_data['sampling_username'] = last_examine_result.sampling_user.username
            material_data['examine_date'] = last_examine_result.examine_date
            material_data['transport_date'] = last_examine_result.transport_date
            ret['unqualified_type_data'] = last_examine_result.single_examine_results.filter(
                mes_decide_qualified=False).values('value', 'type__name')
        mode = UnqualifiedMaterialProcessMode.objects.filter(material=material).last()
        if mode:
            ret['mode'] = {'mode': mode.mode,
                           'created_username': mode.create_user.username,
                           'create_time': datetime.datetime.strftime(mode.create_time, '%Y-%m-%d %H:%M:%S')}
        else:
            ret['mode'] = {}
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class UnqualifiedMaterialProcessModeViewSet(viewsets.GenericViewSet,
                                            mixins.CreateModelMixin,
                                            mixins.ListModelMixin):
    """
    list:
        批次原材料不合格项详情
    create:
        新建批次原材料不合格单
    """
    queryset = UnqualifiedMaterialProcessMode.objects.all()
    serializer_class = UnqualifiedMaterialProcessModeSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('material_id',)


@method_decorator([api_recorder], name="dispatch")
class ExamineResultCurveView(APIView):
    """原材料历史检测类型值记录"""

    def get(self, request):
        material_id = self.request.query_params.get('material')
        st = self.request.query_params.get('st')
        et = self.request.query_params.get('et')
        if not all([st, et, material_id]):
            raise ValidationError('参数缺失')

        if not material_id:
            raise ValidationError('参数缺失！')
        try:
            days = date_range(datetime.datetime.strptime(st, '%Y-%m-%d'),
                              datetime.datetime.strptime(et, '%Y-%m-%d'))
            material = ExamineMaterial.objects.get(id=material_id)
        except Exception:
            raise ValidationError('参数错误！')
        last_type_results = MaterialSingleTypeExamineResult.objects.filter(
            material_examine_result__material=material,
            material_examine_result__examine_date__in=days).values(
            'material_examine_result__examine_date',
            'type__name').annotate(max_id=Max('id')).values_list('max_id', flat=True)
        examine_results = MaterialSingleTypeExamineResult.objects.filter(
            id__in=last_type_results)
        type_names = set(examine_results.values_list('type__name', flat=True))
        y_axis = {
            type_name: {
                'name': type_name,
                'type': 'line',
                'data': [0] * len(days)}
            for type_name in type_names
        }
        for item in examine_results:
            date = datetime.datetime.strftime(item.material_examine_result.examine_date, '%Y-%m-%d')
            y_axis[item.type.name]['data'][days.index(date)] = item.value
        return Response({'x_axis': days, 'y_axis': y_axis.values()})


@method_decorator([api_recorder], name='dispatch')
class MaterialReportEquipViewSet(mixins.CreateModelMixin,
                                 mixins.ListModelMixin,
                                 mixins.UpdateModelMixin,
                                 mixins.RetrieveModelMixin,
                                 viewsets.GenericViewSet):
    """
    list:
        原材料上报设备列表
    create:
        新建原材料上报设备
    update：
        修改原材料上报设备
    """
    queryset = MaterialReportEquip.objects.all()
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialReportEquipFilter
    serializer_class = MaterialReportEquipSerializer


@method_decorator([api_recorder], name='dispatch')
class MaterialReportValueViewSet(mixins.CreateModelMixin,
                                 mixins.ListModelMixin,
                                 viewsets.GenericViewSet):
    queryset = MaterialReportValue.objects.filter(is_binding=False)
    permission_classes = (IsAuthenticated,)
    pagination_class = SinglePageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialReportValueFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return MaterialReportValueCreateSerializer
        return MaterialReportValueSerializer

    def create(self, request, *args, **kwargs):
        data = self.request.data
        for item in data:
            s = MaterialReportValueCreateSerializer(data=item, context={'request': self.request})
            s.is_valid(raise_exception=True)
            self.perform_create(s)
        return Response("提交成功")

    def list(self, request, *args, **kwargs):
        # 获取类型判断值
        data = MaterialExamineType.objects.all().select_related("unit").prefetch_related('standards').values("id",
                                                                                                             "name",
                                                                                                             'interval_type',
                                                                                                             'limit_value')
        for item in data:
            if item['interval_type'] == 1:
                standard = MaterialExamineRatingStandard.objects.filter(level=1, examine_type=item['id']).first()
                if standard:
                    item['qualified_range'] = [standard.lower_limiting_value, standard.upper_limit_value]
            elif item['interval_type'] == 2:
                item['qualified_range'] = [None, item['limit_value']]
            elif item['interval_type'] == 3:
                item['qualified_range'] = [item['limit_value'], None]

        # 返回未绑定数据
        queryset = self.filter_queryset(self.get_queryset())
        prepare_data = list(queryset.values())
        for i in prepare_data:
            row = list(MaterialReportEquip.objects.filter(ip=i['ip']).values('no', 'type'))[0]
            for j in data:
                j['type'] = j.pop('id') if 'id' in j else j['type']
                if j['type'] == row['type']:
                    row.update(j)
            i.update(row)
            if None in i['qualified_range']:
                if i['qualified_range'].index(None) == 0:
                    i['qualified'] = 1 if i['value'] <= i['qualified_range'][1] else 0
                else:
                    i['qualified'] = 1 if i['qualified_range'][0] <= i['value'] else 0
            else:
                i['qualified'] = 1 if i['qualified_range'][0] <= i['value'] <= i['qualified_range'][1] else 0
        return Response({'results': prepare_data})


class ReportValueView(APIView):
    """
    原材料、胶料检测数据上报，
    {"report_type": 上报类型  1原材料  2胶料，
    "ip": IP地址，
    "value": 检测值}
    """

    def post(self, request):
        data = self.request.data
        if not isinstance(data, dict):
            raise ValidationError('数据错误')
        report_type = data.pop('report_type', None)
        if report_type not in (1, 2):
            raise ValidationError('上报类型错误')
        data['created_date'] = datetime.datetime.now()
        try:
            if report_type == 1:
                # 原材料数据上报
                MaterialReportValue.objects.create(**data)
            else:
                ProductReportValue.objects.create(**data)
        except Exception:
            raise ValidationError('参数错误')
        return Response('上报成功！')