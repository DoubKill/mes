import time
import uuid
from datetime import datetime, timedelta
from django.db.models import Q, F
from django.db.models import Count
from django.db.models import FloatField
from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator, UniqueValidator

from django.db.models import Max

from inventory.models import DeliveryPlan, DeliveryPlanStatus
from mes.base_serializer import BaseModelSerializer

from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.models import ProductClassesPlan
from production.models import PalletFeedbacks
from quality.models import TestMethod, MaterialTestOrder, \
    MaterialTestResult, MaterialDataPointIndicator, MaterialTestMethod, TestType, DataPoint, DealSuggestion, \
    TestDataPoint, BatchMonth, BatchDay, BatchEquip, BatchClass, BatchProductNo, MaterialDealResult, LevelResult, \
    TestIndicator, LabelPrint, UnqualifiedDealOrder, \
    UnqualifiedDealOrderDetail, BatchYear, TestTypeRaw, TestIndicatorRaw, TestMethodRaw, DataPointRaw, \
    MaterialTestMethodRaw, MaterialDataPointIndicatorRaw, LevelResultRaw, MaterialTestResultRaw, MaterialTestOrderRaw, \
    UnqualifiedMaterialDealResult, MaterialExamineType, \
    MaterialExamineRatingStandard, ExamineValueUnit, MaterialExamineResult, MaterialSingleTypeExamineResult
from recipe.models import MaterialAttribute


class TestIndicatorSerializer(BaseModelSerializer):
    name = serializers.CharField(help_text='指标名称', validators=[UniqueValidator(queryset=TestIndicator.objects.all(),
                                                                               message='该指标名称已存在！')])

    def create(self, validated_data):
        validated_data['no'] = uuid.uuid1()
        return super().create(validated_data)

    class Meta:
        model = TestIndicator
        fields = ('name',)


class TestMethodSerializer(BaseModelSerializer):
    name = serializers.CharField(help_text='试验方法名称', validators=[UniqueValidator(queryset=TestMethod.objects.all(),
                                                                                 message='该试验方法名称已存在！')])
    test_type_name = serializers.CharField(source='test_type.name', read_only=True)
    test_indicator_name = serializers.CharField(source='test_type.test_indicator.name', read_only=True)

    def create(self, validated_data):
        validated_data['no'] = uuid.uuid1()
        return super(TestMethodSerializer, self).create(validated_data)

    class Meta:
        model = TestMethod
        fields = ('id', 'name', 'test_type', 'test_type_name', 'test_indicator_name')


class TestTypeSerializer(BaseModelSerializer):
    name = serializers.CharField(help_text='试验类型名称', validators=[UniqueValidator(queryset=TestType.objects.all(),
                                                                                 message='该试验类型名称已存在！')])
    test_indicator_name = serializers.CharField(source='test_indicator.name', read_only=True)

    def create(self, validated_data):
        validated_data['no'] = uuid.uuid1()
        return super().create(validated_data)

    class Meta:
        model = TestType
        fields = ('id', 'name', 'test_indicator', 'test_indicator_name')


class DataPointSerializer(BaseModelSerializer):
    test_type_name = serializers.CharField(source='test_type.name', read_only=True)
    test_indicator_name = serializers.CharField(source='test_type.test_indicator.name', read_only=True)

    def create(self, validated_data):
        validated_data['no'] = uuid.uuid1()
        return super().create(validated_data)

    class Meta:
        model = DataPoint
        fields = ('id', 'name', 'unit', 'test_type', 'test_type_name', 'test_indicator_name')
        validators = [
            UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=('name', 'test_type'),
                message="已存在相同数据点，请修改后重试！"
            )
        ]


class MaterialDataPointIndicatorSerializer(BaseModelSerializer):
    # test_data_name = serializers.CharField(source='material_test_data.data_name')
    # test_data_id = serializers.CharField(source='material_test_data.id')
    level = serializers.IntegerField(help_text='等级', min_value=0)
    last_updated_username = serializers.CharField(source='last_updated_user.username', read_only=True, default=None)

    class Meta:
        model = MaterialDataPointIndicator
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialTestResultSerializer(BaseModelSerializer):
    class Meta:
        model = MaterialTestResult
        exclude = ('data_point_indicator', 'material_test_order', 'test_factory_date', 'test_class',
                   'test_group', 'test_times', 'mes_result', 'result')
        extra_kwargs = {'value': {'required': False, 'allow_null': True}}
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialTestOrderSerializer(BaseModelSerializer):
    order_results = MaterialTestResultSerializer(many=True, required=True)
    actual_trains = serializers.IntegerField(min_value=0)

    def create(self, validated_data):
        order_results = validated_data.pop('order_results', None)
        test_order = MaterialTestOrder.objects.filter(lot_no=validated_data['lot_no'],
                                                      actual_trains=validated_data['actual_trains']).first()
        # plan = ProductClassesPlan.objects.filter(plan_classes_uid=validated_data['plan_classes_uid']).first()
        # if not plan:
        #     raise serializers.ValidationError('该计划编号不存在')
        # validated_data['plan_classes_uid'] = plan.work_schedule_plan.group.global_name
        if test_order:
            instance = test_order
            created = False
        else:
            validated_data['material_test_order_uid'] = uuid.uuid1()
            instance = super().create(validated_data)
            created = True

        material_no = validated_data['product_no']
        for item in order_results:
            if not item.get('value'):
                continue
            item['material_test_order'] = instance
            item['test_factory_date'] = datetime.now()
            if created:
                item['test_times'] = 1
            else:
                last_test_result = MaterialTestResult.objects.filter(
                    material_test_order=instance,
                    test_indicator_name=item['test_indicator_name'],
                    data_point_name=item['data_point_name'],
                ).order_by('-test_times').first()
                if last_test_result:
                    item['test_times'] = last_test_result.test_times + 1
                else:
                    item['test_times'] = 1
            material_test_method = MaterialTestMethod.objects.filter(
                material__material_no=material_no,
                test_method__name=item['test_method_name'],
                test_method__test_type__test_indicator__name=item['test_indicator_name'],
                data_point__name=item['data_point_name'],
                data_point__test_type__test_indicator__name=item['test_indicator_name']).first()
            if material_test_method:
                indicator = MaterialDataPointIndicator.objects.filter(
                    material_test_method=material_test_method,
                    data_point__name=item['data_point_name'],
                    data_point__test_type__test_indicator__name=item['test_indicator_name'],
                    upper_limit__gte=item['value'],
                    lower_limit__lte=item['value']).first()
                if indicator:
                    item['mes_result'] = indicator.result
                    item['data_point_indicator'] = indicator
                    item['level'] = indicator.level
                else:
                    item['mes_result'] = '三等品'
                    item['level'] = 2
            else:
                item['mes_result'] = '三等品'
                item['level'] = 2
            item['created_user'] = self.context['request'].user  # 加一个create_user
            item['test_class'] = validated_data['production_class']  # 暂时先这么写吧
            MaterialTestResult.objects.create(**item)
        return instance

    class Meta:
        model = MaterialTestOrder
        exclude = ('material_test_order_uid', 'production_group')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class UnqualifiedDealOrderCreateSerializer(BaseModelSerializer):
    order_ids = serializers.PrimaryKeyRelatedField(help_text='检测单列表', many=True,
                                                   write_only=True, queryset=MaterialTestOrder.objects.all())

    @atomic()
    def create(self, validated_data):
        order_ids = validated_data.pop('order_ids')
        validated_data['unqualified_deal_order_uid'] = uuid.uuid1()
        instance = super().create(validated_data)
        for order_id in order_ids:
            detail = {"unqualified_deal_order": instance,
                      "unqualified_deal_order_detail_uid": uuid.uuid1(),
                      "material_test_order": order_id}
            UnqualifiedDealOrderDetail.objects.create(**detail)
        return instance

    class Meta:
        model = UnqualifiedDealOrder
        exclude = ('unqualified_deal_order_uid',)
        read_only_fields = COMMON_READ_ONLY_FIELDS


class UnqualifiedDealOrderSerializer(BaseModelSerializer):
    class Meta:
        model = UnqualifiedDealOrder
        fields = '__all__'


class UnqualifiedDealOrderUpdateSerializer(BaseModelSerializer):
    class Meta:
        model = UnqualifiedDealOrder
        exclude = ('unqualified_deal_order_uid', 'status')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialTestResultListSerializer(BaseModelSerializer):
    upper_lower = serializers.SerializerMethodField(read_only=True)

    def get_upper_lower(self, obj):
        try:
            mdp_obj = MaterialDataPointIndicator.objects.filter(
                material_test_method__material__material_name=obj.material_test_order.product_no,
                material_test_method__test_method__name=obj.test_method_name,
                material_test_method__data_point__name=obj.data_point_name,
                data_point__name=obj.data_point_name, level=1).first()
            if not mdp_obj:
                return None
            else:
                return f'{mdp_obj.lower_limit}-{mdp_obj.upper_limit}'
        except:
            return None

    class Meta:
        model = MaterialTestResult
        fields = ('test_times', 'value', 'data_point_name', 'test_method_name',
                  'test_indicator_name', 'mes_result', 'result', 'machine_name', 'level', 'upper_lower')


class MaterialTestOrderListSerializer(BaseModelSerializer):
    order_results = MaterialTestResultListSerializer(many=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        order_results = data['order_results']
        ret = {}
        for item in order_results:
            indicator = item['test_indicator_name']
            data_point = item['data_point_name']
            if indicator not in ret:
                ret[indicator] = {}
                ret[indicator][data_point] = item
            else:
                if data_point not in ret[indicator]:
                    ret[indicator][data_point] = item
                else:
                    if ret[indicator][data_point]['test_times'] < item['test_times']:
                        ret[indicator][data_point] = item
        data['order_results'] = ret
        return data

    class Meta:
        model = MaterialTestOrder
        fields = '__all__'


class MaterialTestMethodSerializer(BaseModelSerializer):
    data_points = serializers.SerializerMethodField(read_only=True)
    material_no = serializers.CharField(source='material.material_no', read_only=True)
    test_method_name = serializers.CharField(source='test_method.name', read_only=True)
    test_type_name = serializers.CharField(source='test_method.test_type.name', read_only=True)
    test_indicator_name = serializers.CharField(source='test_method.test_type.test_indicator.name', read_only=True)

    @staticmethod
    def get_data_points(obj):
        return obj.data_point.values('id', 'name')

    class Meta:
        model = MaterialTestMethod
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS
        validators = [
            UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=('material', 'test_method'),
                message="该原材料已存在相同的试验方法，请修改后重试！"
            )
        ]


class DealSuggestionSerializer(BaseModelSerializer):
    """处理意见序列化器"""

    class Meta:
        model = DealSuggestion
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class DealResultDealSerializer(BaseModelSerializer):
    """胶料处理结果序列化器"""
    product_info = serializers.SerializerMethodField(read_only=True)
    material_no = serializers.CharField(max_length=64, write_only=True)
    warehouse_info = serializers.IntegerField(write_only=True)

    def get_product_info(self, obj):
        lot_no = obj.lot_no
        temp = MaterialTestOrder.objects.filter(lot_no=lot_no, delete_flag=False).first()
        result = {}
        if temp:
            result.update(product_no=temp.product_no,
                          production_class=temp.production_class,
                          production_group=temp.production_group,
                          production_equip_no=temp.production_equip_no,
                          production_factory_date=temp.production_factory_date)
        return result

    def update(self, instance, validated_data):
        lot_no = validated_data.get('lot_no', instance.lot_no)
        order_no = time.strftime("%Y%m%d%H%M%S", time.localtime())
        inventory_type = validated_data.get('inventory_type', "指定出库")  # 出库类型
        created_user = self.context['request'].user  # 发起人
        inventory_reason = validated_data.get('reason', "处理意见出库")  # 出库原因
        # 快检针对的是混炼胶/终炼胶库
        warehouse_info_id = validated_data.get('warehouse_info', 1)  # # TODO 混炼胶库暂时写死
        if not warehouse_info_id:
            warehouse_info_id = 1  # TODO 混炼胶库暂时写死
        # TODO 根据胶料编号去判断在终炼胶库还是混炼胶库
        product_info = self.get_product_info(instance)
        if validated_data.get('be_warehouse_out') == True:
            material_no = validated_data.get('material_no')  # 物料编码
            if not material_no:
                raise serializers.ValidationError("material_no为必传参数")
            pfb_obj = PalletFeedbacks.objects.filter(lot_no=lot_no).last()
            if pfb_obj:
                DeliveryPlan.objects.create(order_no=order_no,
                                            inventory_type=inventory_type,
                                            material_no=material_no,
                                            warehouse_info_id=warehouse_info_id,
                                            pallet_no=pfb_obj.pallet_no,
                                            created_user=created_user,
                                            inventory_reason=inventory_reason
                                            )
                DeliveryPlanStatus.objects.create(warehouse_info_id=warehouse_info_id,
                                                  order_no=order_no,
                                                  order_type=inventory_type,
                                                  status=4,
                                                  created_user=created_user,
                                                  )
            else:
                raise serializers.ValidationError('未找到胶料数据')
        if validated_data.get("status") == "待确认":
            instance.deal_user = self.context['request'].user.username
            instance.deal_time = datetime.now()
        elif validated_data.get("status") == "已处理":
            instance.confirm_user = self.context['request'].user.username
            instance.confirm_time = datetime.now()
        else:
            pass
        return super(DealResultDealSerializer, self).update(instance, validated_data)

    class Meta:
        model = MaterialDealResult
        # fields = ("lot_no", "product_no", "production_class", "production_group",
        #           "production_equip_no", "production_factory_date")
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialDealResultListSerializer(BaseModelSerializer):
    suggestion_desc = serializers.CharField(source='deal_opinion.suggestion_desc', read_only=True)
    mtr_list = serializers.SerializerMethodField(read_only=True, )
    deal_suggestion = serializers.CharField(read_only=True, help_text='处理意见', default=None)
    deal_user = serializers.CharField(read_only=True, help_text='处理人', default=None)
    deal_time = serializers.DateTimeField(read_only=True, help_text='处理时间', default=None)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        pallet_data = PalletFeedbacks.objects.filter(lot_no=instance.lot_no).first()
        test_order_data = MaterialTestOrder.objects.filter(lot_no=instance.lot_no).first()
        test_results = MaterialTestResult.objects.filter(material_test_order__lot_no=instance.lot_no)
        ret['day_time'] = str(test_order_data.production_factory_date)  # 工厂日期
        ret['product_no'] = pallet_data.product_no  # 胶料编码
        ret['equip_no'] = pallet_data.equip_no  # 设备编号
        ret['residual_weight'] = None  # 余量
        ret['actual_weight'] = pallet_data.actual_weight  # 收皮重量
        ret['operation_user'] = pallet_data.operation_user  # 操作员
        ret['actual_trains'] = '/'.join(
            [str(i) for i in range(pallet_data.begin_trains, pallet_data.end_trains + 1)])  # 托盘车次
        ret['classes_group'] = test_order_data.production_class + '/' + test_order_data.production_group  # 班次班组
        last_test_result = test_results.last()
        ret['test'] = {'test_status': '复检' if test_results.filter(test_times__gt=1).exists() else '正常',
                       'test_factory_date': str(last_test_result.test_factory_date),
                       'test_class': test_order_data.production_class,
                       'pallet_no': pallet_data.pallet_no,
                       'test_user': None if not test_order_data.created_user else test_order_data.created_user.username}
        product_time = instance.production_factory_date
        material_detail = MaterialAttribute.objects.filter(material__material_no=pallet_data.product_no).first()
        if material_detail:
            unit = material_detail.validity_unit
            if unit in ["天", "days", "day"]:
                param = {"days": material_detail.period_of_validity}
            elif unit in ["小时", "hours", "hour"]:
                param = {"hours": material_detail.period_of_validity}
            else:
                param = {"days": material_detail.period_of_validity}
            expire_time = product_time + timedelta(**param)
            ret['valid_time'] = expire_time  # 有效期
        else:
            ret['valid_time'] = None
        return ret

    def get_mtr_list(self, obj):
        ret = {}
        table_head_top = {}

        test_orders = MaterialTestOrder.objects.filter(lot_no=obj.lot_no).order_by('actual_trains')
        for test_order in test_orders:
            ret[test_order.actual_trains] = []
            max_result_ids = list(test_order.order_results.values(
                'test_indicator_name', 'test_method_name', 'data_point_name'
            ).annotate(max_id=Max('id')).values_list('max_id', flat=True))
            test_results = MaterialTestResult.objects.filter(id__in=max_result_ids)
            for test_result in test_results:
                ret[test_order.actual_trains].append(
                    {
                        'add_subtract': '',
                        'data_point_name': test_result.data_point_name,
                        'max_test_times': test_result.test_times,
                        'result': '一等品' if test_result.level == 1 else '三等品',
                        'test_indicator_name': test_result.test_indicator_name,
                        'value': test_result.value,
                        'status': '1:一等品' if test_order.is_qualified else '3:三等品'
                    }
                )
                test_indicator_name = test_result.test_indicator_name
                if test_indicator_name in table_head_top:
                    table_head_top[test_indicator_name].add(test_result.data_point_name)
                else:
                    table_head_top[test_indicator_name] = {test_result.data_point_name}
        ret['table_head'] = table_head_top
        return ret

    class Meta:
        model = MaterialDealResult
        fields = '__all__'


class LevelResultSerializer(BaseModelSerializer):
    """等级和结果"""

    class Meta:
        model = LevelResult
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class LabelPrintSerializer(serializers.ModelSerializer):
    """标签打印"""
    label_type = serializers.IntegerField(required=False)
    lot_no = serializers.CharField(required=False)
    data = serializers.CharField(required=False)

    class Meta:
        model = LabelPrint
        fields = '__all__'


def to_bfb(n):
    return "%.2f%%" % (n * 100)


class TestDataPointSerializer(serializers.ModelSerializer):
    upper_limit_count = serializers.SerializerMethodField()
    upper_limit_percent = serializers.SerializerMethodField()
    lower_limit_count = serializers.SerializerMethodField()
    lower_limit_percent = serializers.SerializerMethodField()

    class Meta:
        model = TestDataPoint
        fields = ['name',
                  'upper_limit_count',
                  'upper_limit_percent',
                  'lower_limit_count',
                  'lower_limit_percent']

    def get_upper_limit_count(self, obj):
        return obj.upper_limit_count

    def get_upper_limit_percent(self, obj):
        return to_bfb(obj.upper_limit_count / obj.train_count)

    def get_lower_limit_count(self, obj):
        return obj.lower_limit_count

    def get_lower_limit_percent(self, obj):
        return to_bfb(obj.lower_limit_count / obj.train_count)

    @classmethod
    def points_annotate(cls, points):
        points = points.annotate(
            train_count=
            Count('testresult__train', distinct=True))
        points = points.annotate(
            upper_limit_count=
            Count('testresult__train', distinct=True,
                  filter=Q(testresult__qualified=False,
                           testresult__value__gt=F('data_point_indicator__upper_limit'))))
        points = points.annotate(
            lower_limit_count=
            Count('testresult__train', distinct=True,
                  filter=Q(testresult__qualified=False,
                           testresult__value__lt=F('data_point_indicator__lower_limit'))))

        return points


class PercentOfPassSerializer(serializers.Serializer):
    yc_percent_of_pass = serializers.SerializerMethodField()
    lb_percent_of_pass = serializers.SerializerMethodField()
    zh_percent_of_pass = serializers.SerializerMethodField()
    train_count = serializers.SerializerMethodField()

    def get_train_count(self, obj):
        return obj.train_count

    def get_yc_percent_of_pass(self, obj):
        return to_bfb(obj.yc_test_pass_count / obj.yc_train_count) if obj.yc_train_count else None

    def get_lb_percent_of_pass(self, obj):
        return to_bfb(obj.lb_test_pass_count / obj.lb_train_count) if obj.lb_train_count else None

    def get_zh_percent_of_pass(self, obj):
        return to_bfb(obj.zh_test_pass_count / obj.zh_train_count) if obj.zh_train_count else None

    @classmethod
    def batch_annotate(cls, batches):
        yc_train_count = Count('batch__lot__train__testresult', distinct=True,
                               filter=~Q(batch__lot__train__testresult__point__indicator__name='流变'),
                               output_field=FloatField())
        yc_test_pass_count = Count('batch__lot__train__testresult', distinct=True,
                                   filter=
                                   Q(~Q(batch__lot__train__testresult__point__indicator__name='流变') &
                                     Q(batch__lot__train__testresult__qualified=True)),
                                   output_field=FloatField())
        batches = batches.annotate(yc_train_count=yc_train_count) \
            .annotate(yc_test_pass_count=yc_test_pass_count)

        # 流变
        lb_train_count = Count('batch__lot__train__testresult', distinct=True,
                               filter=Q(batch__lot__train__testresult__point__indicator__name='流变'),
                               output_field=FloatField())
        lb_test_pass_count = Count('batch__lot__train__testresult', distinct=True,
                                   filter=
                                   Q(batch__lot__train__testresult__point__indicator__name='流变',
                                     batch__lot__train__testresult__qualified=True),
                                   output_field=FloatField())
        batches = batches.annotate(lb_train_count=lb_train_count) \
            .annotate(lb_test_pass_count=lb_test_pass_count)

        # 综合
        zh_train_count = Count('batch__lot__train__testresult', distinct=True,
                               output_field=FloatField())
        zh_test_pass_count = Count('batch__lot__train__testresult', distinct=True,
                                   filter=Q(batch__lot__train__testresult__qualified=True),
                                   output_field=FloatField())
        batches = batches.annotate(zh_train_count=zh_train_count) \
            .annotate(zh_test_pass_count=zh_test_pass_count)

        train_count = Count('batch__lot__train', distinct=True)
        batches = batches.annotate(train_count=train_count)

        return batches


class BatchEquipSerializer(PercentOfPassSerializer, serializers.ModelSerializer):
    class Meta:
        model = BatchEquip
        fields = [
            'production_equip_no',
            'yc_percent_of_pass',
            'lb_percent_of_pass',
            'zh_percent_of_pass']


class BatchProductNoSerializer(PercentOfPassSerializer, serializers.ModelSerializer):
    points = serializers.SerializerMethodField()

    class Meta:
        model = BatchProductNo
        fields = [
            'product_no',
            'yc_percent_of_pass',
            'lb_percent_of_pass',
            'zh_percent_of_pass',
            'points']

    def get_points(self, obj):
        points = TestDataPoint.objects.filter(testresult__train__lot__batch__batch_product_no=obj)  # TestDataPoint
        points = TestDataPointSerializer.points_annotate(points)
        serializer = TestDataPointSerializer(points, many=True)
        return serializer.data


class BatchClassSerializer(PercentOfPassSerializer, serializers.ModelSerializer):
    class Meta:
        model = BatchClass
        fields = [
            'production_class',
            'yc_percent_of_pass',
            'lb_percent_of_pass',
            'zh_percent_of_pass']


class BatchCommonSerializer(PercentOfPassSerializer, serializers.ModelSerializer):
    points = serializers.SerializerMethodField()
    equips = serializers.SerializerMethodField()
    classes = serializers.SerializerMethodField()
    product_no = serializers.SerializerMethodField()

    class Meta:
        fields = ['id',
                  'date',
                  'train_count',
                  'yc_percent_of_pass',
                  'lb_percent_of_pass',
                  'zh_percent_of_pass',
                  'points',
                  'equips',
                  'classes',
                  'product_no']

    def query_points(self, obj):
        pass

    def get_points(self, obj):
        points = self.query_points(obj)  # TestDataPoint
        points = TestDataPointSerializer.points_annotate(points)
        serializer = TestDataPointSerializer(points, many=True)
        return serializer.data

    def query_equips(self, obj):
        pass

    def get_equips(self, obj):
        return self.percent_of_pass_serialize(
            self.query_equips(obj), BatchEquipSerializer)

    def query_classes(self, obj):
        pass

    def get_classes(self, obj):
        return self.percent_of_pass_serialize(
            self.query_classes(obj), BatchClassSerializer)

    def query_product_no(self, obj):
        pass

    def get_product_no(self, obj):
        return self.percent_of_pass_serialize(
            self.query_product_no(obj), BatchProductNoSerializer)

    @staticmethod
    def percent_of_pass_serialize(objects, serializer_class):
        objects = serializer_class.batch_annotate(objects)
        serializer = serializer_class(objects, many=True)
        return serializer.data


class BatchMonthSerializer(BatchCommonSerializer):
    class Meta(BatchCommonSerializer.Meta):
        model = BatchMonth

    def query_points(self, obj):
        return TestDataPoint.objects.filter(testresult__train__lot__batch__batch_month=obj)

    def query_equips(self, obj):
        return BatchEquip.objects.filter(batch__batch_month=obj)

    def query_classes(self, obj):
        return BatchClass.objects.filter(batch__batch_month=obj)

    def query_product_no(self, obj):
        return BatchProductNo.objects.filter(batch__batch_month=obj)


class BatchDaySerializer(BatchCommonSerializer):
    class Meta(BatchCommonSerializer.Meta):
        model = BatchDay

    def query_points(self, obj):
        return TestDataPoint.objects.filter(testresult__train__lot__batch__batch_day=obj)

    def query_equips(self, obj):
        return BatchEquip.objects.filter(batch__batch_day=obj)

    def query_classes(self, obj):
        return BatchClass.objects.filter(batch__batch_day=obj)

    def query_product_no(self, obj):
        return BatchProductNo.objects.filter(batch__batch_day=obj)


class BatchDateProductNoSerializer(PercentOfPassSerializer, serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        self.batch_product_no_obj = kwargs.pop('batch_product_no_obj', None)
        super().__init__(*args, **kwargs)

    points = serializers.SerializerMethodField()

    class Meta:
        fields = ['date',
                  'train_count',
                  'yc_percent_of_pass',
                  'lb_percent_of_pass',
                  'zh_percent_of_pass',
                  'points']

    def query_points(self, obj):
        pass

    def get_points(self, obj):
        points = self.query_points(obj)
        points = TestDataPointSerializer.points_annotate(points)
        serializer = TestDataPointSerializer(points, many=True)
        return serializer.data


class BatchDayProductNoSerializer(BatchDateProductNoSerializer):
    class Meta(BatchDateProductNoSerializer.Meta):
        model = BatchDay

    def query_points(self, obj):
        return TestDataPoint.objects.filter(testresult__train__lot__batch__batch_day=obj,
                                            testresult__train__lot__batch__batch_product_no=self.batch_product_no_obj)


class BatchMonthProductNoSerializer(BatchDateProductNoSerializer):
    class Meta(BatchDateProductNoSerializer.Meta):
        model = BatchMonth

    def query_points(self, obj):
        return TestDataPoint.objects.filter(testresult__train__lot__batch__batch_month=obj,
                                            testresult__train__lot__batch__batch_product_no=self.batch_product_no_obj)


class BatchProductNoDateCommonSerializer(serializers.ModelSerializer):
    dates = serializers.SerializerMethodField()
    batch_date_model = None
    batch_date_product_no_serializer = None

    class Meta:
        model = BatchProductNo
        fields = ['product_no', 'dates']

    def filter_batch_date_model(self, batches, *args, **kwargs):
        return batches

    def get_dates(self, batch_product_no_obj):
        batches = self.batch_date_model.objects.filter(batch__batch_product_no=batch_product_no_obj)
        batches = self.filter_batch_date_model(batches)
        yc_train_count = Count('batch__lot__train__testresult', distinct=True,
                               filter=~Q(batch__batch_product_no=batch_product_no_obj,
                                         batch__lot__train__testresult__point__indicator__name='流变'),
                               output_field=FloatField())
        yc_test_pass_count = Count('batch__lot__train__testresult', distinct=True,
                                   filter=
                                   Q(~Q(batch__lot__train__testresult__point__indicator__name='流变') &
                                     Q(batch__batch_product_no=batch_product_no_obj) &
                                     Q(batch__lot__train__testresult__qualified=True)),
                                   output_field=FloatField())
        batches = batches \
            .annotate(yc_train_count=yc_train_count) \
            .annotate(yc_test_pass_count=yc_test_pass_count)
        # 流变
        lb_train_count = Count('batch__lot__train__testresult', distinct=True,
                               filter=Q(batch__batch_product_no=batch_product_no_obj,
                                        batch__lot__train__testresult__point__indicator__name='流变'),
                               output_field=FloatField())
        lb_test_pass_count = Count('batch__lot__train__testresult', distinct=True,
                                   filter=Q(batch__batch_product_no=batch_product_no_obj,
                                            batch__lot__train__testresult__point__indicator__name='流变',
                                            batch__lot__train__testresult__qualified=True),
                                   output_field=FloatField())
        batches = batches \
            .annotate(lb_train_count=lb_train_count) \
            .annotate(lb_test_pass_count=lb_test_pass_count)

        # 综合
        zh_train_count = Count('batch__lot__train__testresult', distinct=True,
                               filter=Q(batch__batch_product_no=batch_product_no_obj),
                               output_field=FloatField())
        zh_test_pass_count = Count('batch__lot__train__testresult', distinct=True,
                                   filter=Q(batch__batch_product_no=batch_product_no_obj,
                                            batch__lot__train__testresult__qualified=True),
                                   output_field=FloatField())

        batches = batches \
            .annotate(zh_train_count=zh_train_count) \
            .annotate(zh_test_pass_count=zh_test_pass_count)

        train_count = Count('batch__lot__train', distinct=True)
        batches = batches.annotate(train_count=train_count)

        batches = batches.order_by('date')
        batch_date_product_no_serializer = self.batch_date_product_no_serializer(batches, many=True,
                                                                                 batch_product_no_obj=batch_product_no_obj)
        return batch_date_product_no_serializer.data


class BatchProductNoDaySerializer(BatchProductNoDateCommonSerializer):
    batch_date_model = BatchDay
    batch_date_product_no_serializer = BatchDayProductNoSerializer

    def filter_batch_date_model(self, batches, *args, **kwargs):
        date = self.context['date']
        batches = batches.filter(date__year=date.year, date__month=date.month)
        return batches


class BatchProductNoMonthSerializer(BatchProductNoDateCommonSerializer):
    batch_date_model = BatchMonth
    batch_date_product_no_serializer = BatchMonthProductNoSerializer

    def filter_batch_date_model(self, batches, *args, **kwargs):
        start_time, end_time = self.context['start_time'], self.context['end_time']
        batches = batches.filter(date__gte=start_time, date__lte=end_time)
        return batches


class BatchDayZhPassSerializer(serializers.ModelSerializer):
    mbyl_pass = serializers.SerializerMethodField()

    def get_mbyl_pass(self, obj):
        return to_bfb(obj.zh_test_pass_count / obj.zh_train_count) if obj.zh_train_count else None

    class Meta:
        model = BatchDay
        fields = ['date', 'mbyl_pass']


class BatchMonthZhPassSerializer(serializers.ModelSerializer):
    mbyl_pass = serializers.SerializerMethodField()

    def get_mbyl_pass(self, obj):
        return to_bfb(obj.zh_test_pass_count / obj.zh_train_count) if obj.zh_train_count else None

    class Meta:
        model = BatchMonth
        fields = ['date', 'mbyl_pass']


class BatchYearZhPassSerializer(serializers.ModelSerializer):
    mbyl_pass = serializers.SerializerMethodField()

    def get_mbyl_pass(self, obj):
        return to_bfb(obj.zh_test_pass_count / obj.zh_train_count) if obj.zh_train_count else None

    class Meta:
        model = BatchYear
        fields = ['date', 'mbyl_pass']


class BatchProductNoDateZhPassSerializer(serializers.ModelSerializer):
    dates = serializers.SerializerMethodField()

    class Meta:
        model = BatchProductNo
        fields = ['product_no', 'dates']

    def get_dates(self, obj):
        batch_date_model = self.context['batch_date_model']
        batch_dates = batch_date_model.objects.filter(batch__batch_product_no=obj)
        zh_train_count = Count('batch__lot__train__testresult', distinct=True,
                               filter=Q(batch__batch_product_no=obj),
                               output_field=FloatField())
        zh_test_pass_count = Count('batch__lot__train__testresult', distinct=True,
                                   filter=Q(batch__batch_product_no=obj,
                                            batch__lot__train__testresult__qualified=True),
                                   output_field=FloatField())
        batch_dates = batch_dates.annotate(zh_train_count=zh_train_count,
                                           zh_test_pass_count=zh_test_pass_count)
        batch_dates.order_by('date')
        if batch_date_model == BatchDay:
            return BatchDayZhPassSerializer(instance=batch_dates, many=True).data
        elif batch_date_model == BatchMonth:
            return BatchMonthZhPassSerializer(instance=batch_dates, many=True).data
        elif batch_date_model == BatchYear:
            return BatchYearZhPassSerializer(instance=batch_dates, many=True).data


class BatchClassZhPassSerializer(serializers.ModelSerializer):
    mbyl_pass = serializers.SerializerMethodField()

    def get_mbyl_pass(self, obj):
        return to_bfb(obj.zh_test_pass_count / obj.zh_train_count) if obj.zh_train_count else None

    class Meta:
        model = BatchClass
        fields = ['production_class', 'mbyl_pass']


class BatchProductNoClassZhPassSerializer(serializers.ModelSerializer):
    classes = serializers.SerializerMethodField()

    def get_classes(self, obj):
        batch_classes = BatchClass.objects.filter(batch__batch_product_no=obj)
        zh_train_count = Count('batch__lot__train__testresult', distinct=True,
                               filter=Q(batch__batch_product_no=obj),
                               output_field=FloatField())
        zh_test_pass_count = Count('batch__lot__train__testresult', distinct=True,
                                   filter=Q(batch__batch_product_no=obj,
                                            batch__lot__train__testresult__qualified=True),
                                   output_field=FloatField())
        batch_classes = batch_classes.annotate(zh_train_count=zh_train_count,
                                               zh_test_pass_count=zh_test_pass_count)

        return BatchClassZhPassSerializer(batch_classes, many=True).data

    class Meta:
        model = BatchProductNo
        fields = ['product_no', 'classes']


class MaterialDealResultListSerializer1(serializers.ModelSerializer):

    def to_representation(self, instance):
        ret = super(MaterialDealResultListSerializer1, self).to_representation(instance)
        pallet_data = PalletFeedbacks.objects.filter(lot_no=instance.lot_no).first()
        test_order_data = MaterialTestOrder.objects.filter(lot_no=instance.lot_no).first()
        test_results = MaterialTestResult.objects.filter(material_test_order__lot_no=instance.lot_no)
        ret['day_time'] = str(test_order_data.production_factory_date)
        ret['product_no'] = pallet_data.product_no
        ret['equip_no'] = pallet_data.equip_no
        ret['residual_weight'] = None
        ret['actual_weight'] = pallet_data.actual_weight
        ret['classes_group'] = test_order_data.production_class + '/' + test_order_data.production_group
        last_test_result = test_results.last()
        ret['test'] = {'test_status': '复检' if test_results.filter(test_times__gt=1).exists() else '正常',
                       'test_factory_date': last_test_result.test_factory_date,
                       'test_class': test_order_data.production_class,
                       'test_user': None if not test_order_data.created_user else test_order_data.created_user.username}
        if pallet_data.begin_trains and pallet_data.end_trains:
            trains = [str(x) for x in range(pallet_data.begin_trains, pallet_data.end_trains + 1)]
            trains = ",".join(trains)
        else:
            trains = ""
        ret["trains"] = trains
        return ret

    class Meta:
        model = MaterialDealResult
        fields = "__all__"


"""
    原料检测序列化器
"""


class TestIndicatorRawSerializer(BaseModelSerializer):
    name = serializers.CharField(help_text='指标名称',
                                 validators=[UniqueValidator(queryset=TestIndicatorRaw.objects.all(),
                                                             message='该指标名称已存在！')])

    def create(self, validated_data):
        validated_data['no'] = uuid.uuid1()
        return super().create(validated_data)

    class Meta:
        model = TestIndicatorRaw
        fields = ('name',)


class TestMethodRawSerializer(BaseModelSerializer):
    name = serializers.CharField(help_text='试验方法名称', validators=[UniqueValidator(queryset=TestMethodRaw.objects.all(),
                                                                                 message='该试验方法名称已存在！')])
    test_type_name = serializers.CharField(source='test_type.name', read_only=True)
    test_indicator_name = serializers.CharField(source='test_type.test_indicator.name', read_only=True)

    def create(self, validated_data):
        validated_data['no'] = uuid.uuid1()
        return super().create(validated_data)

    class Meta:
        model = TestMethodRaw
        fields = ('id', 'name', 'test_type', 'test_type_name', 'test_indicator_name')


class TestTypeRawSerializer(BaseModelSerializer):
    name = serializers.CharField(help_text='试验类型名称', validators=[UniqueValidator(queryset=TestTypeRaw.objects.all(),
                                                                                 message='该试验类型名称已存在！')])
    test_indicator_name = serializers.CharField(source='test_indicator.name', read_only=True)

    def create(self, validated_data):
        validated_data['no'] = uuid.uuid1()
        return super().create(validated_data)

    class Meta:
        model = TestTypeRaw
        fields = ('id', 'name', 'test_indicator', 'test_indicator_name')


class DataPointRawSerializer(BaseModelSerializer):
    test_type_name = serializers.CharField(source='test_type.name', read_only=True)
    test_indicator_name = serializers.CharField(source='test_type.test_indicator.name', read_only=True)

    def create(self, validated_data):
        validated_data['no'] = uuid.uuid1()
        return super().create(validated_data)

    class Meta:
        model = DataPointRaw
        fields = ('id', 'name', 'unit', 'test_type', 'test_type_name', 'test_indicator_name')
        validators = [
            UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=('name', 'test_type'),
                message="已存在相同数据点，请修改后重试！"
            )
        ]


class MaterialDataPointIndicatorRawSerializer(BaseModelSerializer):
    level = serializers.IntegerField(help_text='等级', min_value=0)
    last_updated_username = serializers.CharField(source='last_updated_user.username', read_only=True, default=None)

    class Meta:
        model = MaterialDataPointIndicatorRaw
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialTestMethodRawSerializer(BaseModelSerializer):
    data_points = serializers.SerializerMethodField(read_only=True)
    material_no = serializers.CharField(source='material.material_no', read_only=True)
    test_method_name = serializers.CharField(source='test_method.name', read_only=True)
    test_type_name = serializers.CharField(source='test_method.test_type.name', read_only=True)
    test_indicator_name = serializers.CharField(source='test_method.test_type.test_indicator.name', read_only=True)

    @staticmethod
    def get_data_points(obj):
        return obj.data_point.values('id', 'name')

    class Meta:
        model = MaterialTestMethodRaw
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS
        validators = [
            UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=('material', 'test_method'),
                message="该原材料已存在相同的试验方法，请修改后重试！"
            )
        ]


class LevelResultRawSerializer(BaseModelSerializer):
    """等级和结果"""

    class Meta:
        model = LevelResultRaw
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialTestResultRawSerializer(BaseModelSerializer):
    class Meta:
        model = MaterialTestResultRaw
        fields = ('value', 'data_point', 'test_method')
        extra_kwargs = {'value': {'required': False, 'allow_null': True}}
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialTestOrderRawSerializer(BaseModelSerializer):
    order_results_raw = MaterialTestResultRawSerializer(many=True, required=True, help_text="""
    [{"value": 111, "data_point": "数据点id"， "test_method": "试验方法id"}]
    """)

    @atomic()
    def create(self, validated_data):
        order_results = validated_data.pop('order_results_raw', None)
        test_order = MaterialTestOrderRaw.objects.filter(lot_no=validated_data['lot_no'],
                                                         material=validated_data['material']).first()
        if test_order:
            instance = test_order
            created = False
        else:
            instance = super().create(validated_data)
            created = True

        material = validated_data['material']
        for item in order_results:
            if not item.get('value'):
                continue
            item['material_test_order'] = instance
            if created:
                item['test_times'] = 1
            else:
                last_test_result = MaterialTestResultRaw.objects.filter(
                    material_test_order=instance,
                    data_point=item['data_point'],
                ).order_by('-test_times').first()
                if last_test_result:
                    item['test_times'] = last_test_result.test_times + 1
                else:
                    item['test_times'] = 1
            material_test_method = MaterialTestMethodRaw.objects.filter(
                material=material,
                test_method=item['test_method']).first()
            if material_test_method:
                indicator = MaterialDataPointIndicatorRaw.objects.filter(
                    material_test_method=material_test_method,
                    data_point=item['data_point'],
                    upper_limit__gte=item['value'],
                    lower_limit__lte=item['value']).first()
                if indicator:
                    item['result'] = indicator.result
                    item['data_point_indicator'] = indicator
                    item['level'] = indicator.level
                else:
                    item['result'] = '三等品'
                    item['level'] = 2
            else:
                item['result'] = '三等品'
                item['level'] = 2
            MaterialTestResultRaw.objects.create(**item)

        max_result_ids = list(instance.order_results_raw.values(
            'test_method', 'data_point').annotate(max_id=Max('id')).values_list('max_id', flat=True))
        if max_result_ids:
            if MaterialTestResultRaw.objects.filter(id__in=max_result_ids, level__gt=1).exists():
                instance.is_qualified = False
            else:
                instance.is_qualified = True
            instance.save()
        return instance

    class Meta:
        model = MaterialTestOrderRaw
        exclude = ('is_qualified',)
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialTestResultRawListSerializer(BaseModelSerializer):
    upper_lower = serializers.SerializerMethodField(read_only=True)

    def get_upper_lower(self, instance):
        mdp_obj = MaterialDataPointIndicatorRaw.objects.filter(
            material_test_method__material=instance.material_test_order.material,
            material_test_method__test_method=instance.test_method,
            data_point=instance.data_point,
            level=1).first()
        if not mdp_obj:
            return None
        else:
            return "{}-{}".format(mdp_obj.lower_limit, mdp_obj.upper_limit)

    class Meta:
        model = MaterialTestResultRaw
        fields = '__all__'


class MaterialTestOrderRawListSerializer(BaseModelSerializer):
    order_results_raw = MaterialTestResultRawListSerializer(many=True)
    material_no = serializers.ReadOnlyField(source='material.material_no')
    material_name = serializers.ReadOnlyField(source='material.material_name')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        order_results = data['order_results_raw']
        ret = {}
        for item in order_results:
            indicator = TestMethodRaw.objects.get(id=item['test_method']).test_type.test_indicator.name
            data_point = DataPointRaw.objects.get(id=item['data_point']).name
            if indicator not in ret:
                ret[indicator] = {}
                ret[indicator][data_point] = item
            else:
                if data_point not in ret[indicator]:
                    ret[indicator][data_point] = item
                else:
                    if ret[indicator][data_point]['test_times'] < item['test_times']:
                        ret[indicator][data_point] = item
        data['order_results_raw'] = ret
        return data

    class Meta:
        model = MaterialTestOrderRaw
        fields = '__all__'


class MaterialTestOrderRawUpdateSerializer(BaseModelSerializer):
    class Meta:
        model = MaterialTestOrderRaw
        fields = '__all__'


class UnqualifiedMaterialDealResultListSerializer(serializers.ModelSerializer):
    material_test_order_raw = MaterialTestOrderRawListSerializer()
    deal_username = serializers.ReadOnlyField(source='deal_user.username', default='')
    confirm_username = serializers.ReadOnlyField(source='confirm_user.username', default='')

    class Meta:
        model = UnqualifiedMaterialDealResult
        fields = '__all__'


class UnqualifiedMaterialDealResultUpdateSerializer(serializers.ModelSerializer):
    def update(self, instance, validated_data):
        status = validated_data.get('status')
        if status:
            if status == 2:
                validated_data['deal_user'] = self.context['request'].user
            if status == 3:
                validated_data['confirm_user'] = self.context['request'].user
        return super(UnqualifiedMaterialDealResultUpdateSerializer, self).update(instance, validated_data)

    class Meta:
        model = UnqualifiedMaterialDealResult
        fields = ('status', 'release_result', 'unqualified_result', 'is_delivery')


"""新原材料快检"""


# class MaterialExamineEquipmentTypeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = MaterialExamineEquipmentType
#         fields = '__all__'
#
#
# class MaterialExamineEquipmentSerializer(serializers.ModelSerializer):
#     type_name = serializers.CharField(source="type.name", help_text="设备类型名称", read_only=True)
#
#     class Meta:
#         model = MaterialExamineEquipment
#         fields = '__all__'


class MaterialExamineRatingStandardSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialExamineRatingStandard
        fields = '__all__'


class MaterialExamineTypeSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    standards = MaterialExamineRatingStandardSerializer(MaterialExamineRatingStandard.objects.all(), many=True)

    class Meta:
        model = MaterialExamineType
        fields = '__all__'
        # depth = 2


class ExamineValueUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamineValueUnit
        fields = '__all__'


class MaterialSingleTypeExamineResultSerializer(serializers.ModelSerializer):
    examine_name = serializers.CharField(source="type.name")
    equip_name = serializers.CharField(source="equipment.name")

    class Meta:
        model = MaterialSingleTypeExamineResult
        fields = '__all__'


class MaterialExamineResultSerializer(serializers.ModelSerializer):
    recorder_name = serializers.CharField(source='recorder.username', read_only=True)
    sampler_name = serializers.CharField(source='sampling_user.username', read_only=True)
    single_examine_results = MaterialSingleTypeExamineResultSerializer(MaterialSingleTypeExamineResult.objects.all(),
                                                                       many=True, allow_null=True)

    def create(self, validated_data):
        node_data = validated_data.pop('single_examine_results', None)
        instance = super().create(validated_data)
        if node_data:
            MaterialSingleTypeExamineResult.objects.bulk_create(
                [MaterialSingleTypeExamineResult(**x.update(material_examine_result=instance)) for x in node_data])
        return instance

    class Meta:
        model = MaterialExamineResult
        fields = '__all__'
