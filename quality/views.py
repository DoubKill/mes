import datetime
import json
import ast
import os
import re
from decimal import Decimal

import requests
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
from mes.conf import WMS_URL
from mes.paginations import SinglePageNumberPagination
from mes.derorators import api_recorder
from mes.permissions import PermissionClass
from plan.models import ProductClassesPlan
from production.models import PalletFeedbacks, TrainsFeedbacks
from quality.deal_result import receive_deal_result
from quality.filters import TestMethodFilter, DataPointFilter, \
    MaterialTestMethodFilter, MaterialDataPointIndicatorFilter, MaterialTestOrderFilter, MaterialDealResulFilter, \
    DealSuggestionFilter, PalletFeedbacksTestFilter, UnqualifiedDealOrderFilter, MaterialExamineTypeFilter, \
    ExamineMaterialFilter, MaterialEquipFilter, MaterialExamineResultFilter, MaterialReportEquipFilter, \
    MaterialReportValueFilter, ProductReportEquipFilter, ProductReportValueFilter, ProductTestResumeFilter
from quality.models import TestIndicator, MaterialDataPointIndicator, TestMethod, MaterialTestOrder, \
    MaterialTestMethod, TestType, DataPoint, DealSuggestion, MaterialDealResult, LevelResult, MaterialTestResult, \
    LabelPrint, TestDataPoint, BatchMonth, BatchDay, BatchProductNo, BatchEquip, BatchClass, UnqualifiedDealOrder, \
    MaterialExamineResult, MaterialExamineType, MaterialExamineRatingStandard, ExamineValueUnit, ExamineMaterial, \
    DataPointStandardError, MaterialSingleTypeExamineResult, MaterialEquipType, MaterialEquip, \
    QualifiedRangeDisplay, IgnoredProductInfo, MaterialReportEquip, MaterialReportValue, \
    ProductReportEquip, ProductReportValue, ProductTestPlan, ProductTestPlanDetail, RubberMaxStretchTestResult, \
    LabelPrintLog

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
    ExamineMaterialCreateSerializer, IgnoredProductInfoSerializer, \
    MaterialExamineResultMainCreateSerializer, MaterialReportEquipSerializer, MaterialReportValueSerializer, \
    MaterialReportValueCreateSerializer, ProductReportEquipSerializer, ProductReportValueViewSerializer, \
    ProductTestPlanSerializer, ProductTEstResumeSerializer, ReportValueSerializer, RubberMaxStretchTestResultSerializer, \
    UnqualifiedPalletFeedBackSerializer, LabelPrintLogSerializer, ProductTestPlanDetailSerializer, \
    ProductTestPlanDetailBulkCreateSerializer

from django.db.models import Prefetch
from django.db.models import Q
from quality.utils import print_mdr, get_cur_sheet, get_sheet_data, export_mto
from recipe.models import Material, ProductBatching
from django.db.models import Max, Sum, Avg, Count


@method_decorator([api_recorder], name="dispatch")
class TestIndicatorViewSet(ModelViewSet):
    """试验指标列表"""
    queryset = TestIndicator.objects.filter(delete_flag=False)
    serializer_class = TestIndicatorSerializer

    def list(self, request, *args, **kwargs):
        data = self.queryset.values('id', 'name')
        return Response(data)


@method_decorator([api_recorder], name="dispatch")
class DataPointListView(APIView):
    """数据点列表"""

    def get(self, request):
        ret = []
        indicator_names = {'门尼': 1, '硬度': 2, '比重': 3, '流变': 4, '钢拔': 5, '物性': 6}
        for indicator_name in indicator_names:
            data_points = DataPoint.objects.filter(
                test_type__test_indicator__name=indicator_name).order_by('name').values_list('name', flat=True)
            for data_point in data_points:
                if data_point not in ret:
                    ret.append(data_point)
        return Response(ret)


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
        test_indicators_names = ['门尼', '比重', '硬度', '流变', '钢拔', '物性']
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
    queryset = MaterialDealResult.objects.filter(delete_flag=False).order_by('factory_date', 'classes',
                                                                             'equip_no', 'product_no',
                                                                             'begin_trains')
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
        # schedule_name = self.request.query_params.get('schedule_name', None)
        is_print = self.request.query_params.get('is_print', None)
        filter_dict = {'delete_flag': False}
        # pfb_filter = {}
        if day_time:
            filter_dict['factory_date'] = day_time
        if equip_no:
            filter_dict['equip_no'] = equip_no
        if product_no:
            filter_dict['product_no'] = product_no
        if classes:
            filter_dict['classes'] = classes
        # if pfb_filter:
        #     pfb_product_list = MaterialTestOrder.objects.filter(**pfb_filter).values_list('lot_no', flat=True)
        #     filter_dict['lot_no__in'] = list(pfb_product_list)
        if is_print == "已打印":
            filter_dict['print_time__isnull'] = False
        elif is_print == "未打印":
            filter_dict['print_time__isnull'] = True
        pfb_queryset = MaterialDealResult.objects.filter(
            **filter_dict).exclude(status='复测').order_by('factory_date', 'classes', 'equip_no',
                                                          'product_no', 'begin_trains')
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
            LabelPrint.objects.create(label_type=2, lot_no=lot_no, status=0, data=data)
            try:
                LabelPrintLog.objects.create(result=MaterialDealResult.objects.filter(lot_no=lot_no).first(),
                                             created_user=self.request.user.username,
                                             location='快检')
            except Exception:
                pass
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
        instance = self.get_queryset().filter(label_type=station_dict.get(station), status=0).order_by('id').first()
        if instance:
            instance.status = 2
            instance.save()
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
        st_ct = instance.created_date - datetime.timedelta(minutes=1)
        et_ct = instance.created_date + datetime.timedelta(minutes=1)
        LabelPrint.objects.filter(
            lot_no=instance.lot_no,
            label_type=instance.label_type
        ).filter(Q(created_date__gt=st_ct) | Q(created_date__lt=et_ct)).update(status=1)
        return Response("打印完成")


@method_decorator([api_recorder], name="dispatch")
class LabelPrintLogView(ListAPIView):
    """打印履历"""
    queryset = LabelPrintLog.objects.all()
    serializer_class = LabelPrintLogSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('result_id',)
    pagination_class = None


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
        queryset = UnqualifiedDealOrder.objects.order_by('-id')
        t_deal = self.request.query_params.get('t_solved')
        c_deal = self.request.query_params.get('c_solved')
        if t_deal == 'Y':  # 技术部门已处理
            queryset = queryset.filter(t_deal_user__isnull=False)
        elif t_deal == 'N':  # 技术部门未处理
            queryset = queryset.filter(t_deal_user__isnull=True)
        if c_deal == 'Y':  # 检查部门已处理
            queryset = queryset.filter(c_deal_user__isnull=False)
        elif c_deal == 'N':  # 检查部门未处理
            queryset = queryset.filter(c_deal_user__isnull=True)
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return UnqualifiedDealOrderCreateSerializer
        elif self.action == 'retrieve':
            return UnqualifiedDealOrderCreateSerializer
        elif self.action in ('update', 'partial_update'):
            return UnqualifiedDealOrderUpdateSerializer
        else:
            return UnqualifiedDealOrderSerializer


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
    permission_classes = (IsAuthenticated, )

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
                   '伸长率%': 17,
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
                                                                    'test_method__test_type__test_indicator__name',
                                                                    'is_judged')[0]
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
                if j not in pallet_trains_map:
                    pallet_trains_map[j] = {'lot_no': [pallet['lot_no']],
                                            'plan_classes_uid': pallet['plan_classes_uid']}
                else:
                    pallet_trains_map[j]['lot_no'].append(pallet['lot_no'])

        del j, data_points, pallet_data, production_data, reverse_dict

        for item in data:
            try:
                actual_trains = int(item[6])
            except Exception:
                raise ValidationError('车次数据错误！')
            if not pallet_trains_map.get(actual_trains):  # 未找到收皮条码
                continue
            for lot_no in pallet_trains_map[actual_trains]['lot_no']:
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
                    is_judged = method['is_judged']
                    try:
                        point_value = Decimal(item[by_dict[data_point_name]]).quantize(Decimal('0.000'))
                    except Exception:
                        raise ValidationError('检测值{}数据错误'.format(item[by_dict[data_point_name]]))
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
                                   'is_judged': is_judged,
                                   'created_user': self.request.user
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
        instance = MaterialDealResult.objects.filter(lot_no=lot_no).first()
        if not instance:
            return Response({})
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
    queryset = ProductReportEquip.objects.order_by('no')
    serializer_class = ProductReportEquipSerializer
    # permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductReportEquipFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if request.query_params.get('all'):
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # 更新设备的状态
        if request.data.get('equip'):
            data = request.data.get('data')
            for item in data:
                equip_obj = ProductReportEquip.objects.filter(ip=item['machine']).first()
                if equip_obj:
                    equip_obj.status = 1 if item['status'] else 2
                    equip_obj.save()
            return Response('ok')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


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
        deal_status = self.request.query_params.get('deal_status')
        if deal_status == '未处理':
            queryset = queryset.filter(qualified=False)
        if self.request.query_params.get('all'):
            data = queryset.values("id", "name", 'sample_name', 'batch', 'supplier')
            return Response({'results': data})
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['post'], detail=False)
    def disqualification(self, request):
        material_ids = self.request.data.get('material_ids')
        desc = self.request.data.get('desc')
        deal_result = self.request.data.get('deal_result')
        materials = ExamineMaterial.objects.filter(id__in=material_ids)
        materials.update(
            deal_status='已处理',
            deal_result=deal_result,
            desc=desc,
            deal_username=self.request.user.username,
            deal_time=datetime.datetime.now(),
            status=1
        )
        if deal_result == '放行':
            url = WMS_URL + '/MESApi/UpdateTestingResult'
            for m in materials:
                data = {
                    "TestingType": 2,
                    "SpotCheckDetailList": [{
                        "BatchNo": m.batch,
                        "MaterialCode": m.wlxxid,
                        "CheckResult": 1
                    }]
                }
                headers = {"Content-Type": "application/json ;charset=utf-8"}
                try:
                    r = requests.post(url, json=data, headers=headers, timeout=5)
                    r = r.json()
                except Exception:
                    continue
                resp_status = r.get('state')
                m.status = 2 if resp_status == 1 else 3
                m.save()
        return Response('成功')


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
        ret['mode'] = {'mode': material.desc,
                       'created_username': material.deal_username,
                       'create_time': material.deal_time.strftime('%Y-%m-%d %H:%M:%S') if material.deal_time else None}
        return Response(ret)


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


@method_decorator([api_recorder], name="dispatch")
class ProductTestPlanViewSet(ModelViewSet):

    """门尼检测计划"""
    queryset = ProductTestPlan.objects.prefetch_related(
        Prefetch('product_test_plan_detail', queryset=ProductTestPlanDetail.objects.order_by('id')),
    ).order_by('-id')
    serializer_class = ProductTestPlanSerializer
    permission_classes = (IsAuthenticated, )
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'test_equip', 'status')

    def perform_destroy(self, instance):
        """结束检测"""
        instance.status = 4
        ProductTestPlanDetail.objects.filter(test_plan=instance, status=1).update(status=4)
        instance.save()


@method_decorator([api_recorder], name="dispatch")
class ProductTestPlanDetailViewSet(ModelViewSet):
    """门尼检测计划详情"""
    queryset = ProductTestPlanDetail.objects.all()
    serializer_class = ProductTestPlanDetailSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)

    def perform_destroy(self, instance):
        if instance.value:
            raise ValidationError('该数据已检测，无法删除！')
        return super().perform_destroy(instance)

    @action(methods=['post'], detail=False)
    def bulk_create(self, request):
        serializer = ProductTestPlanDetailBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response('ok')


@method_decorator([api_recorder], name="dispatch")
class ProductTestResumeViewSet(mixins.ListModelMixin, GenericViewSet):
    """门尼检测履历"""
    queryset = ProductTestPlanDetail.objects.order_by('-id')
    serializer_class = ProductTEstResumeSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductTestResumeFilter


@method_decorator([api_recorder], name="dispatch")
class TestDataView(APIView):
    """设备监控"""
    def get(self, request):
        data = ProductTestPlanDetail.objects.filter(test_plan__test_time__year=datetime.datetime.now().year,
                                                    test_plan__test_time__month=datetime.datetime.now().month,
                                                    test_plan__test_time__day=datetime.datetime.now().day
                                                    ).values('raw_value')
        return Response(data)


@method_decorator([api_recorder], name='dispatch')
class ReportValueView(APIView):
    """
    原材料、胶料检测数据上报，
    {"report_type": 上报类型  1原材料  2胶料，
    "ip": IP地址，
    "value": 检测值{"l_4: 12"},
    "raw_value": ""}
    """

    def post(self, request):
        # 原材料：{"report_type": 1, "ip": "IP地址", "value": {"l_4: 12"}, "raw_value": "机台检测完整数据"}
        # 胶料门尼：{"report_type": 2, "ip": "IP地址", "value": {"l_4: 12"}, "raw_value": "机台检测完整数据"}

        test_type = self.request.data.get('type')
        if not test_type:
            # 门尼数据上报
            s = ReportValueSerializer(data=self.request.data)
            s.is_valid(raise_exception=True)
            data = s.validated_data
            data['value'] = {'ML(1+4)': data['value']['l_4']}
            report_type = data['report_type']
            if report_type == 1:
                # 原材料数据上报
                MaterialReportValue.objects.create(ip=data['ip'],
                                                   created_date=datetime.datetime.now(),
                                                   value=data['value']['ML(1+4)'])
                return Response({'msg': '上报成功', 'success': True})
            else:
                # 胶料数据上报
                equip_test_plan = ProductTestPlan.objects.filter(test_equip__ip=data['ip'], status=1).last()
        else:
            # 钢拔/物性数据上报
            data = self.request.data
            equip_test_plan = ProductTestPlan.objects.filter(test_equip__no=data['test_equip_no'], status=1).last()

        # 获取当前机台正在进行中的检测计划
        if not equip_test_plan:
            return Response({'mes': '未找到该机台正在进行中的计划', 'success': False})

        # 获取当前检测任务
        current_test_detail = ProductTestPlanDetail.objects.filter(test_plan=equip_test_plan,
                                                                   value__isnull=True
                                                                   ).order_by('id').first()
        if not current_test_detail:
            return Response({'msg': '全部检测完成', 'success': True})

        # 如果是钢拔应检测四/五次
        if test_type:
            if equip_test_plan.test_indicator_name == '钢拔' and test_type == '钢拔':
                # 判断有没有
                ordering = RubberMaxStretchTestResult.objects.filter(
                    product_test_plan_detail=current_test_detail).count() + 1
                RubberMaxStretchTestResult.objects.create(product_test_plan_detail=current_test_detail,
                                                          ordering=ordering,
                                                          speed=data['Speed'],
                                                          max_strength=data['MaxF'],
                                                          max_length=data['MaxL'],
                                                          end_strength=data['BF'],
                                                          end_length=data['BL'],
                                                          yield_strength=data['YieldF'],
                                                          yield_length=data['YieldL'],
                                                          test_time=data['DateTime'],
                                                          test_method=data['TestMethod'],
                                                          ds1=data['DS1'],
                                                          ds2=data['DS2'],
                                                          ds3=data['DS3'],
                                                          result=data['Result'])
                if ordering == equip_test_plan.count:
                    current_test_detail.status = 2  # 完成
                    values = RubberMaxStretchTestResult.objects.filter(product_test_plan_detail=current_test_detail).aggregate(钢拔=Avg('max_strength'))
                    values.update({'钢拔': round(values['钢拔'], 3)})
                    current_test_detail.value = json.dumps(values, ensure_ascii=False)
                    current_test_detail.save()
                else:
                    current_test_detail.status = 3  # 检测中
                    current_test_detail.save()
                    return Response('ok')
            # 如果是物性应检测三次
            elif equip_test_plan.test_indicator_name == '物性' and test_type == '物性':
                ordering = RubberMaxStretchTestResult.objects.filter(
                    product_test_plan_detail=current_test_detail).count() + 1
                RubberMaxStretchTestResult.objects.create(product_test_plan_detail=current_test_detail,
                                                          ordering=ordering,
                                                          speed=data['Speed'],
                                                          thickness=data['Thickness'],
                                                          width=data['Width'],
                                                          ds1=data['DS1'],
                                                          ds2=data['DS2'],
                                                          ds3=data['DS3'],
                                                          ds4=data['DS4'],
                                                          max_strength=data['MStrength'],
                                                          max_length=data['MLength'],
                                                          break_strength=data['BSrength'],
                                                          break_length=data['BLength'],
                                                          n1=data['N1'],
                                                          n2=data['N2'],
                                                          n3=data['N3'],
                                                          test_time=data['DateTime'],
                                                          test_method=data['TestMethod'],
                                                          result=data['Result'])
                if ordering == 3:
                    values = RubberMaxStretchTestResult.objects.filter(
                        product_test_plan_detail=current_test_detail).aggregate(扯断强度=Avg('break_strength'),
                                                                                伸长率=Avg('max_length'),
                                                                                M300=Avg('ds2'))
                    values['伸长率%'] = values['伸长率']
                    del values['伸长率']
                    values.update({'扯断强度': round(values['扯断强度'], 3)})
                    values.update({'伸长率%': round(values['伸长率%'], 3)})
                    values.update({'M300': round(values['M300'], 3)})
                    current_test_detail.status = 2  # 完成
                    current_test_detail.value = json.dumps(values, ensure_ascii=False)
                    current_test_detail.save()
                else:
                    current_test_detail.status = 3  # 检测中
                    current_test_detail.save()
                    return Response('ok')
        else:
            current_test_detail.value = json.dumps(data['value'])
            current_test_detail.raw_value = data['raw_value']
            current_test_detail.status = 2
            current_test_detail.save()

        # if equip_test_plan.product_test_plan_detail.filter(
        #         value__isnull=False).count() == equip_test_plan.product_test_plan_detail.count():
        #     equip_test_plan.status = 2
        #     equip_test_plan.save()

        product_no = current_test_detail.product_no  # 胶料编码
        production_class = current_test_detail.production_classes  # 班次
        group = current_test_detail.production_group  # 班组
        equip_no = current_test_detail.equip_no  # 机台
        product_date = current_test_detail.factory_date  # 工厂日期
        method_name = equip_test_plan.test_method_name  # 实验方法名称
        indicator_name = equip_test_plan.test_indicator_name  # 实验指标名称
        test_times = equip_test_plan.test_times  # 检测次数

        if equip_test_plan.test_indicator_name == '门尼':
            data_point_list = ['ML(1+4)']
        elif equip_test_plan.test_indicator_name == '钢拔':
            data_point_list = ['钢拔']
        elif equip_test_plan.test_indicator_name == '物性':
            data_point_list = ['扯断强度', '伸长率%', 'M300']
        else:
            data_point_list = []

        # 根据检测间隔，补充车次相关test_order和test_result表数据
        for train in range(current_test_detail.actual_trains,
                           current_test_detail.actual_trains + equip_test_plan.test_interval):
            pallets = PalletFeedbacks.objects.filter(
                equip_no=equip_no,
                product_no=product_no,
                classes=production_class,
                factory_date=product_date,
                begin_trains__lte=train,
                end_trains__gte=train
            )
            if not pallets:
                continue
            for pallet in pallets:
                lot_no = pallet.lot_no
                test_order = MaterialTestOrder.objects.filter(lot_no=lot_no, actual_trains=train).first()
                if not test_order:
                    test_order = MaterialTestOrder.objects.create(
                        lot_no=lot_no,
                        material_test_order_uid=uuid.uuid1(),
                        actual_trains=train,
                        product_no=product_no,
                        plan_classes_uid=pallet.plan_classes_uid,
                        production_class=production_class,
                        production_group=group,
                        production_equip_no=equip_no,
                        production_factory_date=product_date
                    )

                # 由MES判断检测结果
                material_test_method = MaterialTestMethod.objects.filter(
                    material__material_no=product_no,
                    test_method__name=method_name).first()
                if not material_test_method:
                    continue

                for data_point in data_point_list:
                    data_point_name = data_point
                    try:
                        if equip_test_plan.test_indicator_name == '门尼':
                            test_value = Decimal(list(json.loads(current_test_detail.value).values())[0]).quantize(Decimal('0.000'))
                        else:
                            test_value = json.loads(current_test_detail.value)[data_point_name]
                    except Exception:
                        raise ValidationError('检测值数据错误')

                    indicator = MaterialDataPointIndicator.objects.filter(
                        material_test_method=material_test_method,
                        data_point__name=data_point_name,
                        data_point__test_type__test_indicator__name=indicator_name,
                        upper_limit__gte=test_value,
                        lower_limit__lte=test_value).first()
                    if indicator:
                        mes_result = indicator.result
                        level = indicator.level
                    else:
                        mes_result = '三等品'
                        level = 2

                    MaterialTestResult.objects.create(
                        material_test_order=test_order,
                        test_factory_date=datetime.datetime.now(),
                        value=test_value,
                        test_times=test_times,
                        data_point_name=data_point_name,
                        test_method_name=method_name,
                        test_indicator_name=indicator_name,
                        result=mes_result,
                        mes_result=mes_result,
                        machine_name=equip_test_plan.test_equip.no,
                        test_group=group,
                        level=level,
                        test_class=production_class,
                        is_judged=material_test_method.is_judged,
                        created_user=equip_test_plan.created_user
                    )

        return Response({'msg': '检测完成', 'success': True})


class CheckEquip(APIView):
    """检测设备状态"""
    def get(self, request):
        equip = ProductReportEquip.objects.order_by('-last_updated_date').first()
        last_date = datetime.datetime.timestamp(equip.last_updated_date)
        now_date = datetime.datetime.timestamp(datetime.datetime.now())
        return Response({'status': False} if now_date - last_date > 10 else {'status': True})


class RubberMaxStretchTestResultViewSet(GenericViewSet, mixins.ListModelMixin, mixins.UpdateModelMixin):
    """物性/钢拔检测数据查看"""
    queryset = RubberMaxStretchTestResult.objects.order_by('ordering')
    serializer_class = RubberMaxStretchTestResultSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('product_test_plan_detail_id',)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        avg_value = queryset.aggregate(最大力=Avg('max_strength'),
                                       结束力=Avg('end_strength'),
                                       厚度=Avg('thickness'),
                                       百分之百=Avg('ds1'),
                                       百分之三百=Avg('ds2'),
                                       断裂强力=Avg('break_strength'),
                                       断裂伸长=Avg('break_length'),
                                       )
        for k, v in avg_value.items():
            if avg_value[k]:
                avg_value[k] = round(v, 3)
        return Response({'results': serializer.data, 'avg_value': avg_value})

    def update(self, request, *args, **kwargs):
        if kwargs.get('pk'):
            pk = kwargs.get('pk')
            test_plan_detail_obj = ProductTestPlanDetail.objects.get(test_results__id=pk)
            RubberMaxStretchTestResult.objects.filter(pk=pk).update(**request.data)
            test_plan_obj = ProductTestPlan.objects.filter(product_test_plan_detail=test_plan_detail_obj).first()
            if test_plan_obj.test_indicator_name == '钢拔':
                data_point_list = ['钢拔']
                values = RubberMaxStretchTestResult.objects.filter(product_test_plan_detail=test_plan_detail_obj).aggregate(
                    钢拔=Avg('max_strength'))
                values = {'钢拔': round(values['钢拔'], 3)}
                test_plan_detail_obj.value = values
                test_plan_detail_obj.save()
            elif test_plan_obj.test_indicator_name == '物性':
                data_point_list = ['扯断强度', '伸长率%', 'M300']
                values = RubberMaxStretchTestResult.objects.filter(product_test_plan_detail=test_plan_detail_obj).aggregate(
                                                                            扯断强度=Avg('break_strength'),
                                                                            伸长率=Avg('max_length'),
                                                                            M300=Avg('ds2'))
                values = {'扯断强度': round(values['扯断强度'], 3),
                          '伸长率%': round(values['伸长率'], 3),
                          'M300': round(values['M300'], 3)}
                test_plan_detail_obj.value = values
                test_plan_detail_obj.save()

            for data_point in data_point_list:
                data_point_name = data_point
                test_value = values[data_point_name]
                material_test_method = MaterialTestMethod.objects.filter(
                    material__material_no=test_plan_detail_obj.product_no,
                    test_method__name=test_plan_obj.test_method_name).first()
                if not material_test_method:
                    continue
                indicator = MaterialDataPointIndicator.objects.filter(
                    material_test_method=material_test_method,
                    data_point__name=data_point_name,
                    data_point__test_type__test_indicator__name=test_plan_obj.test_indicator_name,
                    upper_limit__gte=test_value,
                    lower_limit__lte=test_value).first()
                if indicator:
                    mes_result = indicator.result
                    level = indicator.level
                else:
                    mes_result = '三等品'
                    level = 2

                material_test_order_list = MaterialTestOrder.objects.filter(lot_no=test_plan_detail_obj.lot_no,
                                                                            actual_trains=test_plan_detail_obj.actual_trains)
                for material_test_order in material_test_order_list:
                    MaterialTestResult.objects.filter(material_test_order=material_test_order,
                                                      data_point_name=data_point).update(value=test_value,
                                                                                                      result=mes_result,
                                                                                                      mes_result=mes_result,
                                                                                                      level=level)
            return Response('ok')


@method_decorator([api_recorder], name='dispatch')
class UnqualifiedPalletFeedBackListView(ListAPIView):
    """不合格收皮数据列表"""
    queryset = MaterialDealResult.objects.filter(test_result='三等品').order_by('factory_date', 'classes', 'equip_no', 'product_no')
    serializer_class = UnqualifiedPalletFeedBackSerializer
    permission_classes = (IsAuthenticated, )
    filter_backends = (DjangoFilterBackend, )
    filter_fields = ('product_no', 'factory_date', 'classes', 'equip_no', 'is_deal')


@method_decorator([api_recorder], name='dispatch')
class ProductTestStaticsView(APIView):
    """胶料别不合格率统计"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        product_segment = self.request.query_params.get('station', '')
        product_standard = self.request.query_params.get('product_type', '')
        production_equip_no = self.request.query_params.get('equip_no', '')
        production_class = self.request.query_params.get('classes', '')
        start_time = self.request.query_params.get('s_time')
        end_time = self.request.query_params.get('e_time')
        diff = datetime.datetime.strptime(end_time, '%Y-%m-%d') - datetime.datetime.strptime(start_time, '%Y-%m-%d')
        if diff.days > 31:
            raise ValidationError('搜索日期跨度不得超过一个月！')
        product_str = ''
        if product_segment:
            product_str += '-{}'.format(product_segment)
        if product_standard:
            product_str += '-{}'.format(product_standard)
        queryset = MaterialTestResult.objects.filter(
            material_test_order__product_no__icontains=product_str,
            material_test_order__production_factory_date__gte=start_time,
            material_test_order__production_factory_date__lte=end_time,
            material_test_order__production_equip_no__icontains=production_equip_no,
            material_test_order__production_class__icontains=production_class
            )
        # 统计不合格中超过和小于标准的数量
        # ---------------- begin ---------------
        dic = {}
        data_point_dic = {}
        data_point_query = MaterialDataPointIndicator.objects.values(
            'material_test_method__material__material_name', 'data_point__name',
            'upper_limit', 'lower_limit')
        for i in data_point_query:
            if data_point_dic.get(i['material_test_method__material__material_name']):
                data_point_dic[i['material_test_method__material__material_name']][i['data_point__name']] = [i['lower_limit'], i['upper_limit']]
            else:
                data_point_dic[i['material_test_method__material__material_name']] = {i['data_point__name']: [i['lower_limit'], i['upper_limit']]}

        res = queryset.values('material_test_order__product_no', 'data_point_name', 'value')
        for j in res:
            if data_point_dic.get(j['material_test_order__product_no']):
                data_point_list = data_point_dic[j['material_test_order__product_no']].get(j['data_point_name'])
                if data_point_list:
                    MH_lower = MH_upper = ML_lower = ML_upper = TC10_lower = TC10_upper = TC50_lower = TC50_upper = TC90_lower = TC90_upper = 0
                    if 'MH' in j['data_point_name']:
                        MH_lower = 1 if j['value'] < data_point_list[0] else 0
                        MH_upper = 1 if j['value'] > data_point_list[1] else 0
                    if 'ML' in j['data_point_name']:
                        ML_lower = 1 if j['value'] < data_point_list[0] else 0
                        ML_upper = 1 if j['value'] > data_point_list[1] else 0
                    if 'TC10' in j['data_point_name']:
                        TC10_lower = 1 if j['value'] < data_point_list[0] else 0
                        TC10_upper = 1 if j['value'] > data_point_list[1] else 0
                    if 'TC50' in j['data_point_name']:
                        TC50_lower = 1 if j['value'] < data_point_list[0] else 0
                        TC50_upper = 1 if j['value'] > data_point_list[1] else 0
                    if 'TC90' in j['data_point_name']:
                        TC90_lower = 1 if j['value'] < data_point_list[0] else 0
                        TC90_upper = 1 if j['value'] > data_point_list[1] else 0

            spe = j['material_test_order__product_no'].split('-')[2]
            if dic.get(spe):
                data = dic.get(spe)
                dic[spe].update({
                    'MH_lower': data['MH_lower'] + MH_lower,
                    'MH_upper': data['MH_upper'] + MH_upper,
                    'ML_lower': data['ML_lower'] + ML_lower,
                    'ML_upper': data['ML_upper'] + ML_upper,
                    'TC10_lower': data['TC10_lower'] + TC10_lower,
                    'TC10_upper': data['TC10_upper'] + TC10_upper,
                    'TC50_lower': data['TC50_lower'] + TC50_lower,
                    'TC50_upper': data['TC50_upper'] + TC50_upper,
                    'TC90_lower': data['TC90_lower'] + TC90_lower,
                    'TC90_upper': data['TC90_upper'] + TC90_upper,
                })
            else:
                dic[spe] = {
                    'MH_lower': MH_lower,
                    'MH_upper': MH_upper,
                    'ML_lower': ML_lower,
                    'ML_upper': ML_upper,
                    'TC10_lower': TC10_lower,
                    'TC10_upper': TC10_upper,
                    'TC50_lower': TC50_lower,
                    'TC50_upper': TC50_upper,
                    'TC90_lower': TC90_lower,
                    'TC90_upper': TC90_upper,
                }
        # --------------- end -----------------
        # 检查数与合格数
        records = queryset.values('material_test_order__product_no').annotate(
            JC=Count('material_test_order_id', distinct=True),
            HG=Count('material_test_order_id', distinct=True, filter=Q(material_test_order__is_qualified=True)))
        if not records:
            return Response([])

        # result = {re.search(r'\w{1,2}\d{3}', j['material_test_order__product_no']).group():
        #               {'product_type': re.search(r'\w{1,2}\d{3}', j['material_test_order__product_no']).group(),
        #                'JC': j['JC'], 'HG': j['HG'], 'MN': 0, 'YD': 0, 'BZ': 0, 'RATE_1': [], 'MH': 0, 'ML': 0,
        #                'TC10': 0, 'TC50': 0, 'TC90': 0, 'RATE_S': [], 'sum_s': 0, 'rate': round(j['HG'] / j['JC'] * 100, 2)} for j in records}
        result = {}
        for j in records:
            product_type = re.search(r'\w{1,2}\d{3}', j['material_test_order__product_no']).group()
            if product_type not in result:
                data = {'product_type': product_type, 'JC': j['JC'], 'HG': j['HG'], 'MN': 0, 'YD': 0, 'BZ': 0,
                        'RATE_1': [], 'MH': 0, 'ML': 0, 'TC10': 0, 'TC50': 0, 'TC90': 0, 'RATE_S': [], 'sum_s': 0,
                        'rate': '%.2f' % (j['HG'] / j['JC'] * 100)}
                result[product_type] = data
            else:
                data = result.get(product_type)
                data.update({'JC': data['JC'] + j['JC'], 'HG': data['HG'] + j['HG']})
                data.update({'rate': round(data['HG'] / data['JC'] * 100, 2)})
        """result {'J260': {'product_type': 'J260', 'JC': 2, 'HG': 1}}"""
        # ---------------- begin ---------------
        for i in result.keys():
            if dic.get(i):
                result[i].update(dic[i])
        """result {'J260': {'product_type': 'J260', 'JC': 2, 'HG': 1, 'MH': 1, 'ML': 1, 'TC10': 1 .....}}"""
        # --------------- end -----------------
        pre_data = queryset.values('material_test_order__product_no', 'test_indicator_name', 'data_point_name')\
            .annotate(num=Count('id', distinct=True, filter=Q(~Q(level=1))))\
            .values('material_test_order_id', 'material_test_order__product_no', 'test_indicator_name', 'data_point_name', 'num', 'test_times')\
            .order_by('test_times')
        # 处理数据
        data = {(str(i['material_test_order_id'])+'_'+re.search(r"\w{1,2}\d{3}", i['material_test_order__product_no']).group()+'_'+i['test_indicator_name']+'_'+i['data_point_name']): [i['num'], i['test_times']] for i in pre_data}
        """{'182_J260_比重_比重值': [2, 1], '182_J260_流变_MH': [2, 1], '182_J260_流变_TC10': [2, 1], '182_J260_流变_TC50': [2, 1], 
        '182_J260_流变_TC90': [2, 1], '182_J260_物性_M300': [2, 1], '182_J260_物性_伸长率%': [2, 1], '182_J260_物性_扯断强度': [2, 1], 
        '182_J260_硬度_硬度值': [2, 1], '182_J260_钢拔_钢拔': [2, 1], '182_J260_门尼_ML(1+4)': [2, 1], '183_J260_门尼_ML(1+4)': [1, 0]}"""
        for k, v in data.items():
            single_data = result.get(k.split('_')[1])
            order_id = k.split('_')[0]
            if 'ML(1+4)' in k:
                single_data['MN'] += v[0]
                if order_id not in single_data['RATE_1'] and v[0] != 0:
                    single_data['RATE_1'].append(order_id)
            elif '硬度值' in k:
                single_data['YD'] += v[0]
                if order_id not in single_data['RATE_1'] and v[0] != 0:
                    single_data['RATE_1'].append(order_id)
            elif '比重值' in k:
                single_data['BZ'] += v[0]
                if order_id not in single_data['RATE_1'] and v[0] != 0:
                    single_data['RATE_1'].append(order_id)
            elif 'MH' in k:
                single_data['MH'] += v[0]
                if order_id not in single_data['RATE_S'] and v[0] != 0:
                    single_data['RATE_S'].append(order_id)
            elif 'ML' in k:
                single_data['ML'] += v[0]
                if order_id not in single_data['RATE_S'] and v[0] != 0:
                    single_data['RATE_S'].append(order_id)
            elif 'TC10' in k:
                single_data['TC10'] += v[0]
                if order_id not in single_data['RATE_S'] and v[0] != 0:
                    single_data['RATE_S'].append(order_id)
            elif 'TC50' in k:
                single_data['TC50'] += v[0]
                if order_id not in single_data['RATE_S'] and v[0] != 0:
                    single_data['RATE_S'].append(order_id)
            elif 'TC90' in k:
                single_data['TC90'] += v[0]
                if order_id not in single_data['RATE_S'] and v[0] != 0:
                    single_data['RATE_S'].append(order_id)
            else:
                continue
        res_data = result.values()
        all = {}
        rate_1, rate_lb, rate_test_all, rate_pass_sum = 0, 0, 0, 0
        for v in res_data:
            v['sum_s'] = len(v.pop('RATE_S'))
            rate_1_pass_sum = v['JC'] - len(v.pop('RATE_1'))
            rate_s_pass_sum = v['JC'] - v['sum_s']
            v['RATE_1_PASS'] = '%.2f' % (rate_1_pass_sum / v['JC'] * 100)
            v['cp_all'] = v['JC'] - v['HG']
            v['RATE_S_PASS'] = '%.2f' % (rate_s_pass_sum / v['JC'] * 100)
            rate_1 += rate_1_pass_sum
            rate_lb += rate_s_pass_sum
            rate_test_all += v['JC']
            rate_pass_sum += v['HG']
        all.update(rate_1='%.2f' % (rate_1 / rate_test_all*100), rate_lb='%.2f' % (rate_lb / rate_test_all*100),
                   rate='%.2f' % (rate_pass_sum / rate_test_all*100))
        return Response({'result': res_data, 'all': all})


@method_decorator([api_recorder], name='dispatch')
class ClassTestStaticsView(APIView):
    """班次别不合格率统计"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        product_segment = self.request.query_params.get('station', '')
        product_standard = self.request.query_params.get('product_type', '')
        production_equip_no = self.request.query_params.get('equip_no', '')
        production_class = self.request.query_params.get('classes', '')
        start_time = self.request.query_params.get('s_time')
        end_time = self.request.query_params.get('e_time')
        diff = datetime.datetime.strptime(end_time, '%Y-%m-%d') - datetime.datetime.strptime(start_time, '%Y-%m-%d')
        if diff.days > 31:
            raise ValidationError('搜索日期跨度不得超过一个月！')
        product_str = ''
        if product_segment:
            product_str += '-{}'.format(product_segment)
        if product_standard:
            product_str += '-{}'.format(product_standard)
        queryset = MaterialTestResult.objects.filter(
            material_test_order__product_no__icontains=product_str,
            material_test_order__production_factory_date__gte=start_time,
            material_test_order__production_factory_date__lte=end_time,
            material_test_order__production_equip_no__icontains=production_equip_no,
            material_test_order__production_class__icontains=production_class
        )
        # 统计不合格中超过和小于标准的数量
        # ---------------- begin ---------------
        dic = {}
        data_point_dic = {}
        data_point_query = MaterialDataPointIndicator.objects.values(
            'material_test_method__material__material_name', 'data_point__name',
            'upper_limit', 'lower_limit')
        for i in data_point_query:
            if data_point_dic.get(i['material_test_method__material__material_name']):
                data_point_dic[i['material_test_method__material__material_name']][i['data_point__name']] = [i['lower_limit'], i['upper_limit']]
            else:
                data_point_dic[i['material_test_method__material__material_name']] = {i['data_point__name']: [i['lower_limit'], i['upper_limit']]}

        res = queryset.values('material_test_order__production_factory_date',
                              'material_test_order__product_no',
                              'material_test_order__production_class',
                              'data_point_name', 'value')
        for j in res:
            if data_point_dic.get(j['material_test_order__product_no']):
                data_point_list = data_point_dic[j['material_test_order__product_no']].get(j['data_point_name'])
                if data_point_list:
                    MH_lower = MH_upper = ML_lower = ML_upper = TC10_lower = TC10_upper = TC50_lower = TC50_upper = TC90_lower = TC90_upper = 0
                    if 'MH' in j['data_point_name']:
                        MH_lower = 1 if j['value'] < data_point_list[0] else 0
                        MH_upper = 1 if j['value'] > data_point_list[1] else 0
                    if 'ML' in j['data_point_name']:
                        ML_lower = 1 if j['value'] < data_point_list[0] else 0
                        ML_upper = 1 if j['value'] > data_point_list[1] else 0
                    if 'TC10' in j['data_point_name']:
                        TC10_lower = 1 if j['value'] < data_point_list[0] else 0
                        TC10_upper = 1 if j['value'] > data_point_list[1] else 0
                    if 'TC50' in j['data_point_name']:
                        TC50_lower = 1 if j['value'] < data_point_list[0] else 0
                        TC50_upper = 1 if j['value'] > data_point_list[1] else 0
                    if 'TC90' in j['data_point_name']:
                        TC90_lower = 1 if j['value'] < data_point_list[0] else 0
                        TC90_upper = 1 if j['value'] > data_point_list[1] else 0

            spe = j['material_test_order__product_no'].split('-')[2]
            if dic.get(spe):
                data = dic.get(spe)
                dic[spe].update({
                    'MH_lower': data['MH_lower'] + MH_lower,
                    'MH_upper': data['MH_upper'] + MH_upper,
                    'ML_lower': data['ML_lower'] + ML_lower,
                    'ML_upper': data['ML_upper'] + ML_upper,
                    'TC10_lower': data['TC10_lower'] + TC10_lower,
                    'TC10_upper': data['TC10_upper'] + TC10_upper,
                    'TC50_lower': data['TC50_lower'] + TC50_lower,
                    'TC50_upper': data['TC50_upper'] + TC50_upper,
                    'TC90_lower': data['TC90_lower'] + TC90_lower,
                    'TC90_upper': data['TC90_upper'] + TC90_upper,
                })
            else:
                dic[spe] = {
                    'MH_lower': MH_lower,
                    'MH_upper': MH_upper,
                    'ML_lower': ML_lower,
                    'ML_upper': ML_upper,
                    'TC10_lower': TC10_lower,
                    'TC10_upper': TC10_upper,
                    'TC50_lower': TC50_lower,
                    'TC50_upper': TC50_upper,
                    'TC90_lower': TC90_lower,
                    'TC90_upper': TC90_upper,
                }
        # --------------- end -----------------
        # 检查数与合格数
        records = queryset.values('material_test_order__production_factory_date',
                                  'material_test_order__production_class').annotate(
            JC=Count('material_test_order_id', distinct=True),
            HG=Count('material_test_order_id', distinct=True, filter=Q(material_test_order__is_qualified=True)))
        if not records:
            return Response([])
        result = {}
        for j in records:
            factory_date = str(j['material_test_order__production_factory_date'])
            production_class = j['material_test_order__production_class']
            result.update({
                factory_date + '_' + production_class: {
                    'date': factory_date,
                    'class': production_class,
                    'JC': j['JC'], 'HG': j['HG'], 'MN': 0, 'YD': 0, 'BZ': 0, 'RATE_1': [], 'MH': 0, 'ML': 0, 'TC10': 0,
                    'TC50': 0, 'TC90': 0, 'RATE_S': [], 'sum_s': 0, 'rate': '%.2f' % (j['HG'] / j['JC'] * 100),
                    'sort_class': 0 if production_class == '早班' else 1
                }
            })
        # ---------------- begin ---------------
        for i in result.keys():
            if dic.get(i):
                result[i].update(dic[i])
        # --------------- end -----------------
        pre_data = queryset.values('material_test_order__production_factory_date',
                                   'material_test_order__production_class', 'test_indicator_name', 'data_point_name') \
            .annotate(num=Count('id', distinct=True, filter=Q(~Q(level=1)))) \
            .values('material_test_order__production_factory_date', 'material_test_order__production_class',
                    'material_test_order_id', 'test_indicator_name', 'data_point_name', 'num', 'test_times') \
            .order_by('test_times')
        # 处理数据
        data = {(str(i['material_test_order_id']) + '_' + str(i['material_test_order__production_factory_date']) + '_'
                 + i['material_test_order__production_class'] + '_' + i['test_indicator_name'] + '_' + i[
                     'data_point_name']): [i['num'], i['test_times']] for i in pre_data}
        for k, v in data.items():
            single_data = result.get(k.split('_')[1] + '_' + k.split('_')[2])
            order_id = k.split('_')[0]
            if 'ML(1+4)' in k:
                single_data['MN'] += v[0]
                if order_id not in single_data['RATE_1'] and v[0] != 0:
                    single_data['RATE_1'].append(order_id)
            elif '硬度值' in k:
                single_data['YD'] += v[0]
                if order_id not in single_data['RATE_1'] and v[0] != 0:
                    single_data['RATE_1'].append(order_id)
            elif '比重值' in k:
                single_data['BZ'] += v[0]
                if order_id not in single_data['RATE_1'] and v[0] != 0:
                    single_data['RATE_1'].append(order_id)
            elif 'MH' in k:
                single_data['MH'] += v[0]
                if order_id not in single_data['RATE_S'] and v[0] != 0:
                    single_data['RATE_S'].append(order_id)
            elif 'ML' in k:
                single_data['ML'] += v[0]
                if order_id not in single_data['RATE_S'] and v[0] != 0:
                    single_data['RATE_S'].append(order_id)
            elif 'TC10' in k:
                single_data['TC10'] += v[0]
                if order_id not in single_data['RATE_S'] and v[0] != 0:
                    single_data['RATE_S'].append(order_id)
            elif 'TC50' in k:
                single_data['TC50'] += v[0]
                if order_id not in single_data['RATE_S'] and v[0] != 0:
                    single_data['RATE_S'].append(order_id)
            elif 'TC90' in k:
                single_data['TC90'] += v[0]
                if order_id not in single_data['RATE_S'] and v[0] != 0:
                    single_data['RATE_S'].append(order_id)
            else:
                continue
        res_data = result.values()
        all = {}
        rate_1, rate_lb, rate_test_all, rate_pass_sum = 0, 0, 0, 0
        for v in res_data:
            v['sum_s'] = len(v.pop('RATE_S'))
            rate_1_pass_sum = v['JC'] - len(v.pop('RATE_1'))
            rate_s_pass_sum = v['JC'] - v['sum_s']
            v['RATE_1_PASS'] = '%.2f' % (rate_1_pass_sum / v['JC'] * 100)
            v['cp_all'] = v['JC'] - v['HG']
            v['RATE_S_PASS'] = '%.2f' % (rate_s_pass_sum / v['JC'] * 100)
            rate_1 += rate_1_pass_sum
            rate_lb += rate_s_pass_sum
            rate_test_all += v['JC']
            rate_pass_sum += v['HG']
        all.update(rate_1='%.2f' % (rate_1 / rate_test_all*100), rate_lb='%.2f' % (rate_lb / rate_test_all*100),
                   rate='%.2f' % (rate_pass_sum / rate_test_all*100))
        return Response({'result': sorted(res_data, key=lambda x: (x['date'], x['sort_class'])), 'all': all})


@method_decorator([api_recorder], name="dispatch")
class UnqialifiedEquipView(APIView):

    def get(self, request):
        station = self.request.query_params.get("station", '')
        product_type = self.request.query_params.get("product_type", '')
        s_time = self.request.query_params.get('s_time')
        e_time = self.request.query_params.get('e_time')
        equip_no = self.request.query_params.get('equip_no', '')
        classes = self.request.query_params.get('classes', '')
        product_str = ''
        if station:
            product_str += '-{}'.format(station)
        if product_type:
            product_str += '-{}'.format(product_type)
        e = datetime.datetime.strptime(e_time, '%Y-%m-%d')
        s = datetime.datetime.strptime(s_time, '%Y-%m-%d')
        delta = e - s
        if delta.days > 31:
            raise ValidationError('搜索日期跨度不得超过一个月！')
        if not s_time and not e_time:
            raise ValidationError('请输入检测时间！')

        queryset = MaterialTestOrder.objects.filter(product_no__icontains=product_str,
                                                    production_factory_date__gte=s_time,
                                                    production_factory_date__lte=e_time,
                                                    production_equip_no__icontains=equip_no,
                                                    production_class__icontains=classes
                                                    )
        material_test_result = MaterialTestResult.objects.filter(material_test_order__product_no__icontains=product_str,
                                                   material_test_order__production_factory_date__gte=s_time,
                                                   material_test_order__production_factory_date__lte=e_time,
                                                   material_test_order__production_equip_no__icontains=equip_no,
                                                   material_test_order__production_class__icontains=classes
                                                   )
        # 统计不合格中超过和小于标准的数量
        # ---------------- begin ---------------
        dic_ = {}
        data_point_dic = {}
        data_point_query = MaterialDataPointIndicator.objects.values(
            'material_test_method__material__material_name', 'data_point__name',
            'upper_limit', 'lower_limit')
        for i in data_point_query:
            if data_point_dic.get(i['material_test_method__material__material_name']):
                data_point_dic[i['material_test_method__material__material_name']][i['data_point__name']] = [i['lower_limit'], i['upper_limit']]
            else:
                data_point_dic[i['material_test_method__material__material_name']] = {i['data_point__name']: [i['lower_limit'], i['upper_limit']]}

        res = material_test_result.values('material_test_order__production_equip_no',
                                          'material_test_order__product_no',
                                          'data_point_name', 'value')
        for j in res:
            if data_point_dic.get(j['material_test_order__product_no']):
                data_point_list = data_point_dic[j['material_test_order__product_no']].get(j['data_point_name'])
                if data_point_list:
                    MH_lower = MH_upper = ML_lower = ML_upper = TC10_lower = TC10_upper = TC50_lower = TC50_upper = TC90_lower = TC90_upper = 0
                    if 'MH' in j['data_point_name']:
                        MH_lower = 1 if j['value'] < data_point_list[0] else 0
                        MH_upper = 1 if j['value'] > data_point_list[1] else 0
                    if 'ML' in j['data_point_name']:
                        ML_lower = 1 if j['value'] < data_point_list[0] else 0
                        ML_upper = 1 if j['value'] > data_point_list[1] else 0
                    if 'TC10' in j['data_point_name']:
                        TC10_lower = 1 if j['value'] < data_point_list[0] else 0
                        TC10_upper = 1 if j['value'] > data_point_list[1] else 0
                    if 'TC50' in j['data_point_name']:
                        TC50_lower = 1 if j['value'] < data_point_list[0] else 0
                        TC50_upper = 1 if j['value'] > data_point_list[1] else 0
                    if 'TC90' in j['data_point_name']:
                        TC90_lower = 1 if j['value'] < data_point_list[0] else 0
                        TC90_upper = 1 if j['value'] > data_point_list[1] else 0

            spe = j['material_test_order__product_no'].split('-')[2]
            if dic_.get(spe):
                data = dic_.get(spe)
                dic_[spe].update({
                    'MH_lower': data['MH_lower'] + MH_lower,
                    'MH_upper': data['MH_upper'] + MH_upper,
                    'ML_lower': data['ML_lower'] + ML_lower,
                    'ML_upper': data['ML_upper'] + ML_upper,
                    'TC10_lower': data['TC10_lower'] + TC10_lower,
                    'TC10_upper': data['TC10_upper'] + TC10_upper,
                    'TC50_lower': data['TC50_lower'] + TC50_lower,
                    'TC50_upper': data['TC50_upper'] + TC50_upper,
                    'TC90_lower': data['TC90_lower'] + TC90_lower,
                    'TC90_upper': data['TC90_upper'] + TC90_upper,
                })
            else:
                dic_[spe] = {
                    'MH_lower': MH_lower,
                    'MH_upper': MH_upper,
                    'ML_lower': ML_lower,
                    'ML_upper': ML_upper,
                    'TC10_lower': TC10_lower,
                    'TC10_upper': TC10_upper,
                    'TC50_lower': TC50_lower,
                    'TC50_upper': TC50_upper,
                    'TC90_lower': TC90_lower,
                    'TC90_upper': TC90_upper,
                }
        # --------------- end -----------------

        # 检查数
        test_all = queryset.values('production_equip_no').annotate(count=Count('product_no')).values(
            'production_equip_no', 'count')
        # 合格数
        test_right = queryset.filter(is_qualified=True).values('production_equip_no').annotate(
            count=Count('product_no'))

        result = material_test_result.values('material_test_order_id', 'data_point_name',
                                                            'test_indicator_name',
                                                            'material_test_order__production_equip_no'
                                                            ).annotate(count=Count('id')).values(
            'material_test_order_id', 'data_point_name', 'test_indicator_name', 'level',
            'material_test_order__production_equip_no', 'test_times').order_by('test_times')
        equip_queryset = MaterialTestOrder.objects.filter(production_equip_no__icontains=equip_no).values(
            'production_equip_no').annotate(sum=Count('production_equip_no')).values('production_equip_no')
        equip_list = [equip['production_equip_no'] for equip in equip_queryset]
        if not equip_no:
            dic = {'Z01': {}, 'Z02': {}, 'Z03': {}, 'Z04': {}, 'Z05': {}, 'Z06': {}, 'Z07': {}, 'Z08': {}, 'Z09': {},
                   'Z10': {}, 'Z11': {}, 'Z12': {}, 'Z13': {}, 'Z14': {}, 'Z15': {}}
        else:
            dic = {}
            for equip in equip_list:
                dic.update({equip: {}})

        if len(test_all) > 0:
            for i in result:
                if dic[i['material_test_order__production_equip_no']].get(
                        f"{i['material_test_order_id']}_{i['test_indicator_name']}_{i['data_point_name']}"):
                    if i['level'] == 1:
                        del dic[i['material_test_order__production_equip_no']][
                            f"{i['material_test_order_id']}_{i['test_indicator_name']}_{i['data_point_name']}"]
                else:
                    if i['level'] == 2:
                        dic[i['material_test_order__production_equip_no']].update({
                                                                                      f"{i['material_test_order_id']}_{i['test_indicator_name']}_{i['data_point_name']}": {
                                                                                          'data_point_name': i[
                                                                                              'data_point_name'],
                                                                                          'test_indicator_name': i[
                                                                                              'test_indicator_name']}})

            results = []
            if not equip_no:
                equip_list = ['Z01', 'Z02', 'Z03', 'Z04', 'Z05', 'Z06', 'Z07', 'Z08', 'Z09', 'Z10', 'Z11', 'Z12', 'Z13',
                              'Z14', 'Z15']

            for equip in equip_list:
                MN = YD = BZ = MH = ML = TC10 = TC50 = TC90 = 0
                RATE_1 = []
                RATE_LB = []

                for i in test_all:
                    if equip == i['production_equip_no']:
                        TEST_ALL = i['count']
                        break
                    else:
                        TEST_ALL = 0
                if len(test_right) > 0:
                    for i in test_right:
                        if equip == i['production_equip_no']:
                            TEST_RIGHT = i['count']
                            break
                        else:
                            TEST_RIGHT = 0
                else:
                    TEST_RIGHT = 0
                for i in dic[equip].keys():
                    if i.split('_')[2] == 'ML(1+4)':
                        MN += 1
                    elif i.split('_')[2] == '硬度值':
                        YD += 1
                    elif i.split('_')[2] == '比重值':
                        BZ += 1
                    elif i.split('_')[2] == 'MH':
                        MH += 1
                    elif i.split('_')[2] == 'ML':
                        ML += 1
                    elif i.split('_')[2] == 'TC10':
                        TC10 += 1
                    elif i.split('_')[2] == 'TC50':
                        TC50 += 1
                    elif i.split('_')[2] == 'TC90':
                        TC90 += 1

                    if i.split('_')[2] == 'ML(1+4)' or i.split('_')[2] == '硬度值' or i.split('_')[2] == '比重值':
                        RATE_1.append(i.split('_')[0])
                    if i.split('_')[2] == 'MH' or i.split('_')[2] == 'ML' or i.split('_')[2] == 'TC10' or i.split('_')[
                        2] == 'TC50' or i.split('_')[2] == 'TC90':
                        RATE_LB.append(i.split('_')[0])
                RATE_1 = len(set(RATE_1))
                RATE_LB = len(set(RATE_LB))
                data = {
                        'equip': equip,
                        'test_all': TEST_ALL,
                        'test_right': TEST_RIGHT,
                        'mn': MN,
                        'yd': YD,
                        'bz': BZ,
                        'rate_1': '%.2f' % (((TEST_ALL - RATE_1) / TEST_ALL) * 100) if TEST_ALL else 0,
                        'MH': MH,
                        'ML': ML,
                        'TC10': TC10,
                        'TC50': TC50,
                        'TC90': TC90,
                        'lb_all': RATE_LB,
                        'rate_lb': '%.2f' % (((TEST_ALL - RATE_LB) / TEST_ALL) * 100) if TEST_ALL else 0,
                        'cp_all': TEST_ALL - TEST_RIGHT,
                        'rate': '%.2f' % ((TEST_RIGHT / TEST_ALL) * 100) if TEST_ALL else 0,
                        'rate_1_sum': TEST_ALL - RATE_1,
                        'rate_s_sum': TEST_ALL - RATE_LB
                    }
                if dic_.get(equip):
                    data.update(dic_[equip])
                results.append(
                    data
                    # {
                    #     'equip': equip,
                    #     'test_all': TEST_ALL,
                    #     'test_right': TEST_RIGHT,
                    #     'mn': MN,
                    #     'yd': YD,
                    #     'bz': BZ,
                    #     'rate_1': '%.2f' % (((TEST_ALL - RATE_1) / TEST_ALL) * 100) if TEST_ALL else 0,
                    #     'MH': MH,
                    #     'ML': ML,
                    #     'TC10': TC10,
                    #     'TC50': TC50,
                    #     'TC90': TC90,
                    #     'lb_all': RATE_LB,
                    #     'rate_lb': '%.2f' % (((TEST_ALL - RATE_LB) / TEST_ALL) * 100) if TEST_ALL else 0,
                    #     'cp_all': TEST_ALL - TEST_RIGHT,
                    #     'rate': '%.2f' % ((TEST_RIGHT / TEST_ALL) * 100) if TEST_ALL else 0,
                    #     'rate_1_sum': TEST_ALL - RATE_1,
                    #     'rate_s_sum': TEST_ALL - RATE_LB
                    # }
                )
            all = {}
            num = rate_1 = rate_lb = test_all = rate_pass_sum = 0
            for i in results:
                if i['test_all'] == 0:
                    pass
                else:
                    num += 1
                    rate_1 += i['rate_1_sum']
                    rate_lb += i['rate_s_sum']
                    test_all += i['test_all']
                    rate_pass_sum += i['test_right']
            if num != 0:
                all.update(rate_1='%.2f' % (rate_1 / test_all*100), rate_lb='%.2f' % (rate_lb / test_all*100), rate='%.2f' % (rate_pass_sum / test_all*100))
        else:
            results = []
            all = {}
        return Response({'results': results, 'all': all})
