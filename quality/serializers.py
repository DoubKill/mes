import json
import logging
import re
import time
import uuid
from datetime import datetime, timedelta
from django.db.models import Q, F
from django.db.models import Count, Min
from django.db.models import FloatField
from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.validators import UniqueTogetherValidator, UniqueValidator

from django.db.models import Max

from inventory.models import DeliveryPlan, DeliveryPlanStatus, WmsNucleinManagement
from mes.base_serializer import BaseModelSerializer

from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.models import ProductClassesPlan
from production.models import PalletFeedbacks
from quality.models import TestMethod, MaterialTestOrder, \
    MaterialTestResult, MaterialDataPointIndicator, MaterialTestMethod, TestType, DataPoint, DealSuggestion, \
    TestDataPoint, BatchMonth, BatchDay, BatchEquip, BatchClass, BatchProductNo, MaterialDealResult, LevelResult, \
    TestIndicator, LabelPrint, UnqualifiedDealOrder, UnqualifiedDealOrderDetail, BatchYear, ExamineMaterial, \
    MaterialExamineResult, MaterialSingleTypeExamineResult, MaterialExamineType, \
    MaterialExamineRatingStandard, ExamineValueUnit, DataPointStandardError, MaterialEquipType, MaterialEquip, \
    IgnoredProductInfo, MaterialReportEquip, MaterialReportValue, ProductReportEquip, \
    ProductReportValue, QualifiedRangeDisplay, ProductTestPlan, ProductTestPlanDetail, RubberMaxStretchTestResult, \
    LabelPrintLog, MaterialTestPlan, MaterialTestPlanDetail, MaterialDataPointIndicatorHistory, \
    MaterialInspectionRegistration
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


class DataPointStandardErrorSerializer(BaseModelSerializer):
    value = serializers.CharField(write_only=True, help_text='范围，如（0， 5）', required=True)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['value'] = '{}{},{}{}'.format('(' if ret['lv_type'] == 2 else '[',
                                          ret['lower_value'],
                                          ret['upper_value'],
                                          ')' if ret['uv_type'] == 2 else ']')
        return ret

    def validate(self, attrs):
        value = attrs.pop('value', "")
        ret = re.match(r"([（|(|\[])([\-|\+]?\d+(\.\d+)?)[,|，]([\-|\+]?\d+(\.\d+)?)([)|）|\]])", value)
        if not ret:
            raise serializers.ValidationError('指标范围值错误')
        lv_type = 2 if ret.group(1) in ('(', '（') else 1
        uv_type = 2 if ret.group(6) in (')', '）') else 1
        lower_value = float(ret.group(2))
        upper_value = float(ret.group(4))
        if lower_value > upper_value:
            raise serializers.ValidationError('开始值不得大于结束值！')
        attrs['lv_type'] = lv_type
        attrs['uv_type'] = uv_type
        attrs['lower_value'] = lower_value
        attrs['upper_value'] = upper_value
        return attrs

    class Meta:
        model = DataPointStandardError
        fields = ('id', 'data_point', 'tracking_card', 'label', 'value',
                  'lower_value', 'upper_value', 'lv_type', 'uv_type')
        read_only_fields = ('lower_value', 'upper_value', 'lv_type', 'uv_type')


class MaterialDataPointIndicatorSerializer(BaseModelSerializer):
    # test_data_name = serializers.CharField(source='material_test_data.data_name')
    # test_data_id = serializers.CharField(source='material_test_data.id')
    level = serializers.IntegerField(help_text='等级', min_value=0)
    last_updated_username = serializers.CharField(source='last_updated_user.username', read_only=True, default=None)
    test_method_id = serializers.CharField(source='material_test_method.test_method_id', read_only=True)

    def update(self, instance, validated_data):
        if not instance.last_updated_user:
            username = self.context['request'].user.username
        else:
            username = instance.last_updated_user.username
        MaterialDataPointIndicatorHistory.objects.create(
            product_no=instance.material_test_method.material.material_no,
            test_method=instance.material_test_method.test_method,
            data_point=instance.data_point,
            level=instance.level,
            result=instance.result,
            upper_limit=instance.upper_limit,
            lower_limit=instance.lower_limit,
            created_username=username,
            created_date=instance.last_updated_date
        )
        instance = super().update(instance, validated_data)
        return instance

    class Meta:
        model = MaterialDataPointIndicator
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialDataPointIndicatorHistorySerializer(serializers.ModelSerializer):
    data_point_name = serializers.CharField(source='data_point.name')
    test_method_name = serializers.CharField(source='test_method.name')

    class Meta:
        model = MaterialDataPointIndicatorHistory
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

        pallets = PalletFeedbacks.objects.filter(
            equip_no=validated_data['production_equip_no'],
            product_no=validated_data['product_no'],
            classes=validated_data['production_class'],
            factory_date=validated_data['production_factory_date'],
            begin_trains__lte=validated_data['actual_trains'],
            end_trains__gte=validated_data['actual_trains']
        )
        for pallet in pallets:
            validated_data['lot_no'] = pallet.lot_no
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
                    item['is_judged'] = material_test_method.is_judged
                    indicator = MaterialDataPointIndicator.objects.filter(
                        material_test_method=material_test_method,
                        data_point__name=item['data_point_name'],
                        data_point__test_type__test_indicator__name=item['test_indicator_name'],
                        level=1).first()
                    if indicator:
                        if indicator.lower_limit <= item['value'] <= indicator.upper_limit:
                            item['mes_result'] = '一等品'
                            item['level'] = 1
                        else:
                            item['mes_result'] = '三等品'
                            item['level'] = 2
                        item['data_point_indicator'] = indicator
                        item['judged_upper_limit'] = indicator.upper_limit
                        item['judged_lower_limit'] = indicator.lower_limit
                    else:
                        continue
                        # item['mes_result'] = '三等品'
                        # item['level'] = 2
                else:
                    raise serializers.ValidationError('该胶料实验方法不存在！')
                item['created_user'] = self.context['request'].user  # 加一个create_user
                item['test_class'] = validated_data['production_class']  # 暂时先这么写吧
                MaterialTestResult.objects.create(**item)
        return validated_data

    class Meta:
        model = MaterialTestOrder
        exclude = ('material_test_order_uid', 'production_group')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class UnqualifiedDealOrderDetailSerializer(serializers.ModelSerializer):
    test_data = serializers.ListField(help_text='检测数据详情', write_only=True)

    def validate(self, attrs):
        test_data = attrs['test_data']
        try:
            test_data = json.dumps(test_data)
        except Exception:
            raise serializers.ValidationError('json格式错误！')
        attrs['test_data'] = test_data
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['test_data'] = json.loads(instance.test_data)
        return ret

    class Meta:
        model = UnqualifiedDealOrderDetail
        exclude = ('unqualified_deal_order',)
        read_only_fields = COMMON_READ_ONLY_FIELDS


class UnqualifiedDealOrderCreateSerializer(BaseModelSerializer):
    deal_details = UnqualifiedDealOrderDetailSerializer(many=True, help_text="""[{"ordering": "序号",
                                                                               "lot_no": "收皮条码",
                                                                               "factory_date": "工厂日期",
                                                                               "equip_no": "机台号",
                                                                               "classes": "班次",
                                                                               "product_no": "胶料名称",
                                                                               "test_data": "检测详情",
                                                                               "trains": "车次",
                                                                               "reason": "不合格情况"
                                                                               }]""")

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        deal_details = ret.pop('deal_details', [])
        deal_items = {}
        for item in deal_details:
            if item['ordering'] not in deal_items:
                deal_items[item['ordering']] = {
                    "ordering": item['ordering'],
                    "lot_no": item['lot_no'],
                    "factory_date": item['factory_date'],
                    "equip_no": item['equip_no'],
                    "classes": item['classes'],
                    "product_no": item['product_no'],
                    "test_data": item['test_data'],
                    "reason": item['reason'],
                    "trains": [{"id": item['id'], "train": item['trains']}]
                }
            else:
                deal_items[item['ordering']]['trains'].append({"id": item['id'], "train": item['trains']})
        ret['deal_details'] = list(deal_items.values())
        return ret

    @atomic()
    def create(self, validated_data):
        deal_details = validated_data.pop('deal_details', [])
        validated_data['deal_user'] = self.context['request'].user.username
        validated_data['t_deal_suggestion'] = None
        validated_data['c_deal_suggestion'] = None
        validated_data['t_deal_user'] = None
        validated_data['t_deal_date'] = None
        validated_data['c_deal_user'] = None
        validated_data['c_deal_date'] = None
        validated_data['desc'] = None
        validated_data['deal_method'] = None
        instance = super().create(validated_data)
        for deal_detail in deal_details:
            deal_detail['unqualified_deal_order'] = instance
            UnqualifiedDealOrderDetail.objects.create(**deal_detail)
            MaterialDealResult.objects.filter(lot_no=deal_detail['lot_no']).update(is_deal=True)
        return instance

    class Meta:
        model = UnqualifiedDealOrder
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS
        extra_kwargs = {'deal_user': {'read_only': True},
                        'deal_date': {'read_only': True}}


class UnqualifiedDealOrderSerializer(BaseModelSerializer):
    c_solved = serializers.SerializerMethodField()
    t_solved = serializers.SerializerMethodField()

    def get_c_solved(self, obj):
        return 'Y' if obj.c_deal_user else 'N'

    def get_t_solved(self, obj):
        return 'Y' if obj.t_deal_user else 'N'

    class Meta:
        model = UnqualifiedDealOrder
        fields = '__all__'


class TechDealOrderDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = UnqualifiedDealOrderDetail
        fields = ('id', 'is_release', 'suggestion')
        extra_kwargs = {'id': {'read_only': False}}


class UnqualifiedDealOrderUpdateSerializer(BaseModelSerializer):
    tech_deal_result = TechDealOrderDetailSerializer(help_text='[{"id": "处置单详情id", "is_release": "是否放行", '
                                                       '"suggestion":"意见"}]', required=False, write_only=True,
                                                     many=True)

    def update(self, instance, validated_data):
        tech_deal_result = validated_data.pop('tech_deal_result', {})
        c_agreed = validated_data.get('c_agreed')

        for key, value in dict(validated_data).items():
            if value is None or value == '':
                validated_data.pop(key)

        # 技术科处理
        if tech_deal_result:
            validated_data['c_deal_suggestion'] = None
            validated_data['c_deal_user'] = None
            validated_data['c_deal_date'] = None
            validated_data['c_agreed'] = None
            for item in tech_deal_result:
                deal_details = UnqualifiedDealOrderDetail.objects.filter(id=item['id'])
                deal_details.update(suggestion=item['suggestion'], is_release=item['is_release'])

        UnqualifiedDealOrder.objects.filter(id=instance.id).update(**validated_data)

        # 检查科处理
        if c_agreed is not None:
            if c_agreed:
                # 同意
                for detail in instance.deal_details.filter(is_release=True):
                    MaterialDealResult.objects.filter(lot_no=detail.lot_no).update(test_result='PASS',
                                                                                   deal_suggestion=detail.suggestion,
                                                                                   deal_time=datetime.now(),
                                                                                   deal_user=instance.t_deal_user,
                                                                                   update_store_test_flag=4)
            else:
                # 不同意
                for detail in instance.deal_details.filter(is_release=True):
                    MaterialDealResult.objects.filter(lot_no=detail.lot_no).update(test_result='三等品',
                                                                                   deal_suggestion='不合格',
                                                                                   deal_time=datetime.now(),
                                                                                   deal_user=instance.t_deal_user)
        return instance

    class Meta:
        model = UnqualifiedDealOrder
        exclude = ('unqualified_deal_order_uid', )
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialTestResultListSerializer(BaseModelSerializer):
    upper_lower = serializers.SerializerMethodField(read_only=True)

    def get_upper_lower(self, obj):
        return f'{obj.judged_lower_limit}-{obj.judged_upper_limit}'
        # try:
        #     mdp_obj = MaterialDataPointIndicator.objects.filter(
        #         material_test_method__material__material_name=obj.material_test_order.product_no,
        #         material_test_method__test_method__name=obj.test_method_name,
        #         material_test_method__data_point__name=obj.data_point_name,
        #         data_point__name=obj.data_point_name, level=1).first()
        #     if not mdp_obj:
        #         return None
        #     else:
        #         return f'{mdp_obj.lower_limit}-{mdp_obj.upper_limit}'
        # except:
        #     return None

    class Meta:
        model = MaterialTestResult
        fields = ('id', 'test_times', 'value', 'data_point_name', 'test_method_name',
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
                    if ret[indicator][data_point]['id'] < item['id']:
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
    test_type = serializers.IntegerField(source='test_method.test_type.id', read_only=True)
    test_indicator_name = serializers.CharField(source='test_method.test_type.test_indicator.name', read_only=True)

    @staticmethod
    def get_data_points(obj):
        return obj.data_point.values('id', 'name')

    def update(self, instance, validated_data):
        ins_dts = set(instance.data_point.values_list('id', flat=True))
        data_point = validated_data.get('data_point', None)
        if data_point:
            u_dts = set([d.id for d in data_point])
            instance.data_point.clear()
            uncommon_dts1 = u_dts & ins_dts
            uncommon_dts = ins_dts - uncommon_dts1
            MaterialDataPointIndicator.objects.filter(material_test_method=instance, data_point_id__in=uncommon_dts).delete()
        return super().update(instance, validated_data)

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
        pallet_data = PalletFeedbacks.objects.filter(lot_no=instance.lot_no,
                                                     product_no=instance.product_no).first()
        # test_order_data = MaterialTestOrder.objects.filter(lot_no=instance.lot_no).first()
        test_results = MaterialTestResult.objects.filter(material_test_order__lot_no=instance.lot_no).order_by('id')
        plan = ProductClassesPlan.objects.filter(plan_classes_uid=pallet_data.plan_classes_uid).first()
        if not plan:
            # classes = pallet_data.classes
            group = ''
        else:
            # classes = plan.work_schedule_plan.classes.global_name
            group = plan.work_schedule_plan.group.global_name
        ret['day_time'] = str(instance.factory_date)  # 工厂日期
        # ret['product_no'] = pallet_data.product_no  # 胶料编码
        # ret['equip_no'] = pallet_data.equip_no  # 设备编号
        ret['residual_weight'] = None  # 余量
        ret['actual_weight'] = pallet_data.actual_weight  # 收皮重量
        ret['operation_user'] = pallet_data.operation_user  # 操作员
        ret['actual_trains'] = '/'.join(
            [str(i) for i in range(pallet_data.begin_trains, pallet_data.end_trains + 1)])  # 托盘车次
        ret['classes_group'] = instance.classes + '/' + group  # 班次班组
        last_test_result = test_results.last()
        ret['test'] = {'test_status': '复检' if test_results.filter(test_times__gt=1).exists() else '正常',
                       'test_factory_date': last_test_result.test_factory_date.strftime('%Y-%m-%d %H:%M:%S'),
                       'test_class': instance.classes,
                       'pallet_no': pallet_data.pallet_no,
                       'test_user': None if not last_test_result.created_user else last_test_result.created_user.username}
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
            expire_time = (product_time + timedelta(**param)).strftime('%Y-%m-%d %H:%M:%S')
            ret['valid_time'] = expire_time  # 有效期
        else:
            ret['valid_time'] = None
        ret['range_showed'] = QualifiedRangeDisplay.objects.first().is_showed
        return ret

    def get_mtr_list(self, obj):
        ret = {}
        table_head_top = {}
        sort_rules = {'门尼': 1, '硬度': 2, '比重': 3, '流变': 4, '钢拔': 5, '物性': 6}
        test_orders = MaterialTestOrder.objects.filter(lot_no=obj.lot_no,
                                                       product_no=obj.product_no
                                                       ).order_by('actual_trains')
        methods = list(MaterialTestMethod.objects.filter(material__material_no=obj.product_no,
                                                         is_print=True
                                                         ).values_list('test_method__name', flat=True))
        indicators = []
        for test_order in test_orders:
            ret[test_order.actual_trains] = []
            max_result_ids = list(test_order.order_results.values(
                'test_indicator_name', 'data_point_name'
            ).annotate(max_id=Max('id')).values_list('max_id', flat=True))
            test_results = MaterialTestResult.objects.filter(id__in=max_result_ids,
                                                             test_method_name__in=methods
                                                             ).order_by('test_indicator_name',
                                                                        'data_point_name')
            for test_result in test_results:
                if test_result.level == 1:
                    result = '合格'
                elif test_result.is_passed:
                    result = 'pass'
                else:
                    result = '不合格'
                if test_order.is_qualified:
                    status = '1:一等品'
                elif test_order.is_passed:
                    status = 'PASS'
                else:
                    status = '3:三等品'
                if test_result.result == '合格':
                    tag = ""
                else:
                    value = test_result.value
                    if value > test_result.judged_upper_limit:
                        tag = '+'
                    elif value < test_result.judged_lower_limit:
                        tag = '-'
                    else:
                        tag = ''
                ret[test_order.actual_trains].append(
                    {
                        'add_subtract': '',
                        'data_point_name': test_result.data_point_name,
                        'max_test_times': test_result.test_times,
                        'result': result,
                        'test_indicator_name': test_result.test_indicator_name,
                        'value': test_result.value,
                        'status': status,
                        'point': test_result.data_point_name,
                        "upper_limit": test_result.judged_upper_limit,
                        "lower_limit": test_result.judged_lower_limit,
                        'tag': tag
                    }
                )
                test_indicator_name = test_result.test_indicator_name
                if test_indicator_name in table_head_top:
                    table_head_top[test_indicator_name][test_result.data_point_name] = {'upper_limit': test_result.judged_upper_limit,
                                                                                         'lower_limit': test_result.judged_lower_limit,
                                                                                         'point': test_result.data_point_name}
                else:
                    table_head_top[test_indicator_name] = {test_result.data_point_name: {'upper_limit': test_result.judged_upper_limit,
                                                                                         'lower_limit': test_result.judged_lower_limit,
                                                                                         'point': test_result.data_point_name}}
        for key, value in table_head_top.items():
            sorted_value = sorted(value.values(), key=lambda x: x['point'])
            indicators.append({'point': key, 'point_head': sorted_value})
        try:
            indicators = sorted(indicators, key=lambda d: sort_rules[d['point']])
        except Exception:
            pass
        trains = []
        for k, v in ret.items():
            trains.append({'train': k, 'content': v})
        mtr_list = {'trains': trains, 'table_head': indicators}
        return mtr_list

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
    print_times = serializers.SerializerMethodField()

    def get_print_times(self, obj):
        return obj.print_logs.count()

    def to_representation(self, instance):
        ret = super(MaterialDealResultListSerializer1, self).to_representation(instance)
        pallet_data = PalletFeedbacks.objects.filter(lot_no=instance.lot_no,
                                                     product_no=instance.product_no).first()
        # test_order_data = MaterialTestOrder.objects.filter(lot_no=instance.lot_no).first()
        test_results = MaterialTestResult.objects.filter(material_test_order__lot_no=instance.lot_no)
        plan = ProductClassesPlan.objects.filter(plan_classes_uid=pallet_data.plan_classes_uid).first()
        if not plan:
            # classes = pallet_data.classes
            group = ''
        else:
            # classes = plan.work_schedule_plan.classes.global_name
            group = plan.work_schedule_plan.group.global_name
        ret['day_time'] = str(instance.factory_date)
        # ret['product_no'] = pallet_data.product_no
        # ret['equip_no'] = pallet_data.equip_no
        ret['residual_weight'] = None
        ret['actual_weight'] = pallet_data.actual_weight
        ret['classes_group'] = instance.classes + '/' + group  # 班次班组
        last_test_result = test_results.last()
        ret['test'] = {'test_status': '复检' if test_results.filter(test_times__gt=1).exists() else '正常',
                       'test_factory_date': last_test_result.test_factory_date,
                       'test_class': instance.classes,
                       'test_user': None if not last_test_result.created_user else last_test_result.created_user.username}
        trains = [str(x) for x in range(instance.begin_trains, instance.end_trains + 1)]
        ret["trains"] = ",".join(trains)
        return ret

    class Meta:
        model = MaterialDealResult
        fields = "__all__"


class IgnoredProductInfoSerializer(BaseModelSerializer):
    product_nos = serializers.ListField(write_only=True)

    @atomic()
    def create(self, validated_data):
        product_nos = validated_data['product_nos']
        for product_no in product_nos:
            try:
                IgnoredProductInfo.objects.create(product_no=product_no)
            except Exception:
                raise serializers.ValidationError('该胶料{}已存在，请勿重复添加！'.format(product_no))
        return validated_data

    class Meta:
        model = IgnoredProductInfo
        fields = "__all__"
        read_only_fields = ('product_no',)


class Test_Indicator_Name(serializers.ModelSerializer):

    class Meta:
        model = TestIndicator
        fields = ['name']


class ProductReportEquipSerializer(BaseModelSerializer):
    data_point_name = serializers.ReadOnlyField(source='data_point.name')
    test_type_name = serializers.ReadOnlyField(source='data_point.test_type.name')
    test_type = serializers.ReadOnlyField(source='data_point.test_type.id')
    last_time = serializers.SerializerMethodField()
    test_indicator_name = serializers.SerializerMethodField()
    no = serializers.CharField(help_text='设备编号', validators=[UniqueValidator(queryset=ProductReportEquip.objects.all(),
                                                                               message='该设备已存在！')])
    ip = serializers.CharField(help_text='IP', validators=[UniqueValidator(queryset=ProductReportEquip.objects.all(),
                                                                               message='该IP已被使用！')])

    class Meta:
        model = ProductReportEquip
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS

    def get_last_time(self, obj):
        last_time = ProductTestPlan.objects.filter(test_equip=obj).values('test_time').last()
        return last_time['test_time'].strftime('%Y-%m-%d %H:%M:%S') if last_time else None

    def get_test_indicator_name(self, obj):  # 实验类型
        test_indicator_name = ProductReportEquip.objects.filter(id=obj.id).values('test_indicator__name')
        return test_indicator_name


class ProductReportValueViewSerializer(serializers.ModelSerializer):
    test_type = serializers.PrimaryKeyRelatedField(queryset=TestType.objects.all(), write_only=True)
    data_point = serializers.PrimaryKeyRelatedField(queryset=DataPoint.objects.all(), write_only=True)
    product_no = serializers.CharField(help_text='胶料编码', write_only=True)
    actual_trains = serializers.IntegerField(help_text='车次', write_only=True)
    production_class = serializers.CharField(max_length=64, help_text='生产班次名', write_only=True)
    equip_no = serializers.CharField(max_length=64, help_text='机台', write_only=True)
    production_factory_date = serializers.DateField(help_text='工厂日期', write_only=True)

    def create(self, validated_data):
        equip_no = validated_data['equip_no']
        product_no = validated_data['product_no']
        production_class = validated_data['production_class']
        factory_date = validated_data['production_factory_date']
        actual_trains = validated_data['actual_trains']
        test_indicator_name = validated_data['test_type'].test_indicator.name
        data_point_name = validated_data['data_point'].name
        pallet = PalletFeedbacks.objects.filter(
            equip_no=equip_no,
            product_no=product_no,
            classes=production_class,
            factory_date=factory_date,
            begin_trains__lte=actual_trains,
            end_trains__gte=actual_trains
        ).first()
        if not pallet:
            raise serializers.ValidationError('未找到胶料{}第【{}】车收皮信息！'.format(product_no, actual_trains))
        lot_no = pallet.lot_no
        plan = ProductClassesPlan.objects.filter(plan_classes_uid=pallet.plan_classes_uid).first()
        if not plan:
            return validated_data
        test_order = MaterialTestOrder.objects.filter(lot_no=lot_no,
                                                      actual_trains=actual_trains).first()
        if test_order:
            instance = test_order
            created = False
        else:
            instance = MaterialTestOrder.objects.create(
                lot_no=lot_no,
                material_test_order_uid=uuid.uuid1(),
                actual_trains=actual_trains,
                product_no=product_no,
                plan_classes_uid=pallet.plan_classes_uid,
                production_class=production_class,
                production_group=plan.work_schedule_plan.group.global_name,
                production_equip_no=equip_no,
                production_factory_date=factory_date,
            )
            created = True

        result_data = dict()
        result_data['material_test_order'] = instance
        result_data['test_factory_date'] = datetime.now()
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
        material_test_method = MaterialTestMethod.objects.filter(
            material__material_no=product_no,
            test_method__test_type=validated_data['test_type'],
            data_point=validated_data['data_point']).first()
        if material_test_method:
            indicator = MaterialDataPointIndicator.objects.filter(
                material_test_method=material_test_method,
                data_point=validated_data['data_point'],
                upper_limit__gte=validated_data['value'],
                lower_limit__lte=validated_data['value']).first()
            if indicator:
                result_data['mes_result'] = indicator.result
                result_data['data_point_indicator'] = indicator
                result_data['level'] = indicator.level
            else:
                result_data['mes_result'] = '三等品'
                result_data['level'] = 2
        else:
            raise serializers.ValidationError('未找到胶料{}【{}】试验方法，请录入后重试！'.format(product_no,
                                                                                validated_data['test_type'].name))
        result_data['created_user'] = self.context['request'].user
        result_data['test_class'] = validated_data['production_class']
        result_data['value'] = validated_data['value']
        result_data['data_point_name'] = data_point_name
        result_data['test_method_name'] = material_test_method.test_method.name
        result_data['test_indicator_name'] = test_indicator_name
        MaterialTestResult.objects.create(**result_data)
        ProductReportValue.objects.filter(id=validated_data['id']).update(is_binding=True)
        return validated_data

    class Meta:
        model = ProductReportValue
        exclude = ('ip', 'created_date', 'is_binding')
        extra_kwargs = {'id': {'read_only': False}}


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


class MaterialExamineRatingStandardNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialExamineRatingStandard
        exclude = ('examine_type',)


class MaterialExamineTypeSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source='unit.name', read_only=True, default=None)
    standards = MaterialExamineRatingStandardNodeSerializer(many=True, required=False)
    unitname = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    name = serializers.CharField(validators=[UniqueValidator(queryset=MaterialExamineType.objects.all(),
                                                             message='该检测类型名称已存在')])

    # actual_name = serializers.CharField(validators=[UniqueValidator(queryset=MaterialExamineType.objects.all(),
    #                                                                 message='该检测类型名称已存在111')])

    @atomic()
    def create(self, validated_data):
        unit_name = validated_data.pop("unitname", None)
        standards = validated_data.pop("standards", None)
        if unit_name:
            unit, flag = ExamineValueUnit.objects.get_or_create(name=unit_name)
            validated_data["unit"] = unit
        instance = super().create(validated_data)
        if standards:
            for x in standards:
                x.update(examine_type=instance)
            MaterialExamineRatingStandard.objects.bulk_create([MaterialExamineRatingStandard(**x) for x in standards])
        return instance

    @atomic()
    def update(self, instance, validated_data):
        standards = validated_data.pop("standards", None)
        if 'unitname' in validated_data:
            if validated_data['unitname']:
                unit, _ = ExamineValueUnit.objects.get_or_create(name=validated_data['unitname'])
            else:
                unit = None
            validated_data["unit"] = unit
        instance.standards.all().delete()
        if standards:
            for x in standards:
                x.update(examine_type=instance)
            MaterialExamineRatingStandard.objects.bulk_create(
                [MaterialExamineRatingStandard(**x) for x in standards])
        validated_data.pop("unitname", None)
        return super().update(instance, validated_data)

    class Meta:
        model = MaterialExamineType
        fields = '__all__'


class ExamineValueUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamineValueUnit
        fields = '__all__'


class MaterialSingleTypeExamineResultMainSerializer(serializers.ModelSerializer):
    equip_name = serializers.ReadOnlyField(source="equipment.equip_name")
    type_name = serializers.ReadOnlyField(source="type.name")
    qualified_range = serializers.SerializerMethodField()
    interval_type = serializers.ReadOnlyField(source='type.interval_type')

    @staticmethod
    def get_qualified_range(obj):
        if obj.type.interval_type == 1:
            standard = MaterialExamineRatingStandard.objects.filter(level=1, examine_type=obj.type).first()
            if standard:
                return [standard.lower_limiting_value, standard.upper_limit_value]
        elif obj.type.interval_type == 2:
            return [None, obj.type.limit_value]
        elif obj.type.interval_type == 3:
            return [obj.type.limit_value, None]
        return []

    # def validate(self, attrs):
    #     if 'mes_decide_qualified' not in attrs:
    #         if attrs['value']:
    #             attrs['mes_decide_qualified'] = None
    #             type_standard = MaterialExamineRatingStandard.objects.filter(examine_type=attrs['type'],
    #                                                                          level=1).first()
    #             if type_standard:
    #                 if type_standard.lower_limiting_value <= attrs['value'] <= type_standard.upper_limit_value:
    #                     attrs['mes_decide_qualified'] = True
    #                 else:
    #                     attrs['mes_decide_qualified'] = False
    #     return attrs

    class Meta:
        model = MaterialSingleTypeExamineResult
        exclude = ('material_examine_result',)


class MaterialExamineResultMainCreateSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(write_only=True, help_text='物料名称')
    material_sample_name = serializers.CharField(write_only=True, help_text='样品名称',
                                                 allow_blank=True, allow_null=True)
    material_batch = serializers.CharField(write_only=True, help_text='批次号')
    material_supplier = serializers.CharField(write_only=True, help_text='产地',
                                              allow_blank=True, allow_null=True)
    material_tmh = serializers.CharField(write_only=True, help_text='条码号')
    material_wlxxid = serializers.CharField(write_only=True, help_text='物料信息id')
    single_examine_results = MaterialSingleTypeExamineResultMainSerializer(
        many=True, required=False, help_text="""[{"type": 检测类型id, "value": 检测值, "equipment":检测机台id]""")

    def validate(self, attrs):
        material_name = attrs.pop('material_name')
        material_sample_name = attrs.pop('material_sample_name', None)
        material_batch = attrs.pop('material_batch')
        material_supplier = attrs.pop('material_supplier', None)
        material_tmh = attrs.pop('material_tmh')
        material_wlxxid = attrs.pop('material_wlxxid')
        material = ExamineMaterial.objects.filter(batch=material_batch,
                                                  wlxxid=material_wlxxid).first()
        if not material:
            material = ExamineMaterial.objects.create(batch=material_batch,
                                                      name=material_name,
                                                      sample_name=material_sample_name,
                                                      supplier=material_supplier,
                                                      tmh=material_tmh,
                                                      wlxxid=material_wlxxid)
        attrs['material'] = material
        return attrs

    @atomic()
    def create(self, validated_data):
        node_data = validated_data.pop('single_examine_results', [])
        validated_data['qualified'] = False
        validated_data['recorder'] = self.context['request'].user
        instance = super().create(validated_data)
        for x in node_data:
            x.update(material_examine_result=instance)
            MaterialSingleTypeExamineResult.objects.create(**x)
        if not instance.single_examine_results.filter(mes_decide_qualified=False).exists():
            instance.qualified = True
            instance.save()
        material = instance.material
        result_status = 1
        first_examine_tesult = MaterialExamineResult.objects.exclude(id=instance.id).filter(material=material).order_by('id').first()
        if first_examine_tesult:
            if not first_examine_tesult.qualified:
                # 第一次检测不合格，后面检测结果不用更新到立库
                result_status = 3
        material.status = result_status
        material.qualified = instance.qualified
        material.save()
        return instance

    class Meta:
        model = MaterialExamineResult
        extra_kwargs = {
            'qualified': {'read_only': True},
            'recorder': {'read_only': True},
            'material': {'read_only': True},
        }
        fields = '__all__'


class MaterialExamineResultMainSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source='material.name')
    sample_name = serializers.ReadOnlyField(source='material.sample_name')
    batch = serializers.ReadOnlyField(source='material.batch')
    supplier = serializers.ReadOnlyField(source='material.supplier')
    recorder_username = serializers.ReadOnlyField(source='recorder.username')
    sampling_username = serializers.ReadOnlyField(source='sampling_user.username')
    sample_qualified = serializers.ReadOnlyField(source='material.qualified')
    is_latest = serializers.SerializerMethodField()
    single_examine_results = MaterialSingleTypeExamineResultMainSerializer(
        many=True, required=False, help_text="""[{"type": 检测类型id, "value": 检测值, "equipment":检测机台id]""")

    @staticmethod
    def get_is_latest(obj):
        """是否同批次最新检测"""
        return MaterialExamineResult.objects.filter(material=obj.material).last().id == obj.id

    @atomic()
    def update(self, instance, validated_data):
        node_data = validated_data.pop('single_examine_results', [])
        validated_data['qualified'] = False
        instance = super().update(instance, validated_data)
        instance.single_examine_results.all().delete()
        for x in node_data:
            x.update(material_examine_result=instance)
            MaterialSingleTypeExamineResult.objects.create(**x)
        # MaterialSingleTypeExamineResult.objects.bulk_create(
        #     [MaterialSingleTypeExamineResult(**x) for x in node_data])
        if not instance.single_examine_results.filter(mes_decide_qualified=False).exists():
            instance.qualified = True
            instance.save()
        last_test_result = MaterialExamineResult.objects.filter(material=instance.material).last()
        material = instance.material
        material.qualified = last_test_result.qualified
        material.save()
        return instance

    class Meta:
        model = MaterialExamineResult
        extra_kwargs = {
            'qualified': {'read_only': True},
            'recorder': {'read_only': True},
        }
        fields = '__all__'


class MaterialSingleTypeExamineResultSerializer(serializers.ModelSerializer):
    type_name = serializers.ReadOnlyField(source='type.name')
    interval_type = serializers.ReadOnlyField(source='type.interval_type')

    class Meta:
        model = MaterialSingleTypeExamineResult
        fields = ['type_name', 'value', 'mes_decide_qualified', 'interval_type']


class MaterialExamineResultSerializer(serializers.ModelSerializer):
    sampling_user = serializers.ReadOnlyField(source='sampling_user.username')
    recorder = serializers.ReadOnlyField(source='recorder.username')
    single_examine_results = MaterialSingleTypeExamineResultSerializer(many=True, read_only=True)

    class Meta:
        model = MaterialExamineResult
        fields = ['examine_date',
                  'transport_date',
                  'sampling_user',
                  'recorder',
                  'qualified',
                  're_examine',
                  'qualified',
                  'newest_qualified',
                  'create_time',
                  'update_time',
                  'single_examine_results']


class ExamineMaterialSerializer(serializers.ModelSerializer):
    examine_results = MaterialExamineResultSerializer(many=True, read_only=True)
    examine_types = serializers.SerializerMethodField()

    @staticmethod
    def get_examine_types(obj):
        return set(MaterialSingleTypeExamineResult.objects.filter(
            material_examine_result__material=obj).values_list('type__name', flat=True))

    class Meta:
        model = ExamineMaterial
        fields = "__all__"


class ExamineMaterialCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamineMaterial
        fields = '__all__'


class MaterialEquipTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialEquipType
        exclude = ('examine_type',)


class MaterialEquipTypeUpdateSerializer(serializers.ModelSerializer):

    def update(self, instance, validated_data):
        # 将之前关联的检测类型清除
        instance.examine_type.clear()
        return super().update(instance, validated_data)

    class Meta:
        model = MaterialEquipType
        fields = ('id', 'examine_type', 'type_name')


class MaterialEquipSerializer(serializers.ModelSerializer):
    equip_type_name = serializers.ReadOnlyField(source='equip_type.type_name')
    examine_type = serializers.SerializerMethodField()

    @staticmethod
    def get_examine_type(obj):
        return obj.equip_type.examine_type.filter().values_list('id', flat=True)

    class Meta:
        model = MaterialEquip
        fields = '__all__'


class MaterialReportEquipSerializer(BaseModelSerializer):
    type_name = serializers.ReadOnlyField(source='type.name')

    class Meta:
        model = MaterialReportEquip
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialReportValueSerializer(BaseModelSerializer):
    created_date = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')

    class Meta:
        model = MaterialReportValue
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialReportValueCreateSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(write_only=True, help_text='物料名称')
    material_sample_name = serializers.CharField(write_only=True, help_text='样品名称',
                                                 allow_blank=True, allow_null=True)
    material_batch = serializers.CharField(write_only=True, help_text='批次号')
    material_supplier = serializers.CharField(write_only=True, help_text='产地',
                                              allow_blank=True, allow_null=True)
    material_tmh = serializers.CharField(write_only=True, help_text='条码号')
    material_wlxxid = serializers.CharField(write_only=True, help_text='物料信息id')
    single_examine_results = MaterialSingleTypeExamineResultMainSerializer(
        many=True, required=False, help_text="""[{"type": 检测类型id, "value": 检测值]""")

    def validate(self, attrs):
        material_name = attrs.pop('material_name')
        material_sample_name = attrs.pop('material_sample_name', None)
        material_batch = attrs.pop('material_batch')
        material_supplier = attrs.pop('material_supplier', None)
        material_tmh = attrs.pop('material_tmh')
        material_wlxxid = attrs.pop('material_wlxxid')
        material = ExamineMaterial.objects.filter(batch=material_batch,
                                                  wlxxid=material_wlxxid).first()
        if not material:
            material = ExamineMaterial.objects.create(batch=material_batch,
                                                      name=material_name,
                                                      sample_name=material_sample_name,
                                                      supplier=material_supplier,
                                                      tmh=material_tmh,
                                                      wlxxid=material_wlxxid)
        attrs['material'] = material
        return attrs

    @atomic()
    def create(self, validated_data):
        validated_data['qualified'] = False
        validated_data['recorder'] = self.context['request'].user
        instance = super().create(validated_data)
        MaterialSingleTypeExamineResult.objects.create(material_examine_result_id=instance.id,
                                                       type_id=self.initial_data['type'],
                                                       mes_decide_qualified=self.initial_data['qualified'],
                                                       value=self.initial_data['value'])
        if not instance.single_examine_results.filter(mes_decide_qualified=False).exists():
            instance.qualified = True
            instance.save()
        material = instance.material
        material.qualified = instance.qualified
        material.save()
        obj = MaterialReportValue.objects.get(id=self.initial_data['id'])
        obj.is_binding = True
        obj.save()
        return instance

    class Meta:
        model = MaterialExamineResult
        extra_kwargs = {
            'qualified': {'read_only': True},
            'recorder': {'read_only': True},
            'material': {'read_only': True},
        }
        fields = '__all__'


class MaterialInspectionRegistrationSerializer(BaseModelSerializer):
    mes_quality_status = serializers.SerializerMethodField()
    locked_status = serializers.SerializerMethodField()

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['created_date'] = ret['created_date'][:10]
        return ret

    def get_mes_quality_status(self, obj):
        instance = ExamineMaterial.objects.filter(batch=obj.batch).first()
        if instance:
            return '合格' if instance.qualified else '不合格'
        return '待检品'

    def get_locked_status(self, obj):
        instance = WmsNucleinManagement.objects.filter(batch_no=obj.batch).first()
        if instance:
            return instance.locked_status
        else:
            return '未管控'

    class Meta:
        model = MaterialInspectionRegistration
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS
        validators = [UniqueTogetherValidator(
            queryset=MaterialInspectionRegistration.objects.all(),
            fields=('batch', 'material_no'), message='改批次送检数据已存在，请勿重复添加！')]


class ProductTestPlanDetailSerializer(BaseModelSerializer):

    class Meta:
        model = ProductTestPlanDetail
        fields = '__all__'
        read_only_fields = ('test_plan', 'production_group', 'value', 'raw_value', 'test_time')


class ProductTestPlanDetailBulkCreateSerializer(serializers.Serializer):
    test_plan = serializers.PrimaryKeyRelatedField(queryset=ProductTestPlan.objects.all())
    product_test_plan_detail = ProductTestPlanDetailSerializer(many=True)

    def create(self, validated_data):
        product_test_plan_details = validated_data['product_test_plan_detail']
        test_plan = validated_data['test_plan']
        # 新建检测任务
        for product_test_plan_detail in product_test_plan_details:
            if 'lot_no' in product_test_plan_detail:
                pallet_data = PalletFeedbacks.objects.filter(lot_no=product_test_plan_detail['lot_no']).first()
            else:
                pallet_data = PalletFeedbacks.objects.filter(
                    equip_no=product_test_plan_detail['equip_no'],
                    product_no=product_test_plan_detail['product_no'],
                    classes=product_test_plan_detail['production_classes'],
                    factory_date=product_test_plan_detail['factory_date'],
                    begin_trains__lte=product_test_plan_detail['actual_trains'],
                    end_trains__gte=product_test_plan_detail['actual_trains']).first()
            # 补充生产班组字段
            if pallet_data:
                s = ProductClassesPlan.objects.filter(
                    plan_classes_uid=pallet_data.plan_classes_uid
                ).values('work_schedule_plan__group__global_name').first()
                if not s:
                    product_test_plan_detail['production_group'] = test_plan.test_group
                else:
                    product_test_plan_detail['production_group'] = s['work_schedule_plan__group__global_name']
            else:
                raise serializers.ValidationError('第{}车生产批次数据不存在'.format(product_test_plan_detail['actual_trains']))
            product_test_plan_detail['lot_no'] = pallet_data.lot_no
            product_test_plan_detail['test_plan'] = test_plan
            ProductTestPlanDetail.objects.create(**product_test_plan_detail)
        return validated_data

    class Meta:
        model = ProductTestPlanDetail
        fields = '__all__'
        read_only_fields = ('test_plan', 'production_group', 'value', 'raw_value', 'test_time')


class ProductTestPlanSerializer(BaseModelSerializer):
    test_equip_no = serializers.ReadOnlyField(source='test_equip.no')
    product_test_plan_detail = ProductTestPlanDetailSerializer(many=True)

    @atomic()
    def create(self, validated_data):
        product_test_plan_details = validated_data.pop('product_test_plan_detail')
        test_indicator_name = validated_data['test_indicator_name']
        if test_indicator_name == '门尼':
            s = 'M'
        elif test_indicator_name == '流变':
            s = 'L'
        elif test_indicator_name == '物性':
            s = 'W'
        elif test_indicator_name == '钢拔':
            s = 'G'
        else:
            raise serializers.ValidationError('不支持该指标检测！')

        # 判断该机台是否有正在进行中的检测计划
        equip_test_plan = ProductTestPlan.objects.filter(
            status=1, test_equip=validated_data['test_equip']).first()
        if equip_test_plan:
            raise serializers.ValidationError('当前有计划正在执行，请结束后再开始检测！')

        # 后端补充字段，新建test_plan主表数据
        plan_uid = f"{s}{validated_data['test_equip'].no}{datetime.now().strftime('%Y%m%d%H%M%S')}"
        validated_data['plan_uid'] = plan_uid
        validated_data['test_user'] = self.context['request'].user
        validated_data['test_time'] = datetime.now()
        instance = super().create(validated_data)

        # 新建检测任务
        for product_test_plan_detail in product_test_plan_details:
            if 'lot_no' in product_test_plan_detail:
                pallet_data = PalletFeedbacks.objects.filter(lot_no=product_test_plan_detail['lot_no']).first()
            else:
                pallet_data = PalletFeedbacks.objects.filter(
                    equip_no=product_test_plan_detail['equip_no'],
                    product_no=product_test_plan_detail['product_no'],
                    classes=product_test_plan_detail['production_classes'],
                    factory_date=product_test_plan_detail['factory_date'],
                    begin_trains__lte=product_test_plan_detail['actual_trains'],
                    end_trains__gte=product_test_plan_detail['actual_trains']).first()
            # 补充生产班组字段
            if pallet_data:
                s = ProductClassesPlan.objects.filter(
                    plan_classes_uid=pallet_data.plan_classes_uid
                ).values('work_schedule_plan__group__global_name').first()
                if not s:
                    product_test_plan_detail['production_group'] = validated_data['test_group']
                else:
                    product_test_plan_detail['production_group'] = s['work_schedule_plan__group__global_name']
            else:
                raise serializers.ValidationError('第{}车生产批次数据不存在'.format(product_test_plan_detail['actual_trains']))
            product_test_plan_detail['lot_no'] = pallet_data.lot_no
            product_test_plan_detail['test_plan'] = instance
            ProductTestPlanDetail.objects.create(**product_test_plan_detail)
        return instance

    class Meta:
        model = ProductTestPlan
        fields = '__all__'
        read_only_fields = ['plan_uid', 'test_time', 'test_user', 'status', 'created_date', 'last_updated_date',
                            'delete_date', 'delete_flag', 'created_user', 'last_updated_user', 'delete_user']


class ProductTEstResumeSerializer(BaseModelSerializer):
    plan_uid = serializers.ReadOnlyField(source='test_plan.plan_uid')
    test_equip = serializers.ReadOnlyField(source='test_plan.test_equip.no')
    test_classes = serializers.ReadOnlyField(source='test_plan.test_classes')
    test_group = serializers.ReadOnlyField(source='test_plan.test_group')
    test_indicator_name = serializers.ReadOnlyField(source='test_plan.test_indicator_name')
    test_method_name = serializers.ReadOnlyField(source='test_plan.test_method_name')
    test_times = serializers.ReadOnlyField(source='test_plan.test_times')
    test_interval = serializers.ReadOnlyField(source='test_plan.test_interval')
    test_user = serializers.ReadOnlyField(source='test_plan.test_user')
    # status = serializers.ReadOnlyField(source='test_plan.status')
    values = serializers.CharField(read_only=True)

    class Meta:
        model = ProductTestPlanDetail
        fields = '__all__'

    def get_test_time(self, obj):
        return obj.test_plan.test_time.strftime('%Y-%m-%d %H:%M:%S')


class ReportValueSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=(1, 2), help_text='上报类型1：原材料 2：胶料')
    ip = serializers.CharField(help_text='IP地址')
    value = serializers.JSONField(help_text='{"l_4: 12"}')
    raw_value = serializers.CharField(help_text='机台检测完整数据')


class RubberMaxStretchTestResultSerializer(serializers.ModelSerializer):
    product_no = serializers.ReadOnlyField(source='product_test_plan_detail.product_no')

    class Meta:
        model = RubberMaxStretchTestResult
        fields = '__all__'


class UnqualifiedPalletFeedBackSerializer(serializers.ModelSerializer):
    trains = serializers.SerializerMethodField()
    test_data = serializers.SerializerMethodField()

    def get_trains(self, obj):
        pallet = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        return '{}-{}'.format(pallet.begin_trains, pallet.end_trains) if not \
            pallet.begin_trains == pallet.end_trains else str(pallet.begin_trains)

    def get_test_data(self, obj):
        last_result_ids = list(MaterialTestResult.objects.filter(
            is_judged=True,
            material_test_order__lot_no=obj.lot_no).values(
            'material_test_order', 'test_indicator_name', 'data_point_name'
        ).annotate(max_id=Max('id')).values_list('max_id', flat=True))
        return MaterialTestResult.objects.filter(
            level__gt=1,
            id__in=last_result_ids).values(
            'data_point_name').annotate(min_value=Min('value'),
                                        max_value=Max('value')
                                        ).values('data_point_name', 'min_value', 'max_value')

    class Meta:
        model = MaterialDealResult
        fields = '__all__'


class LabelPrintLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = LabelPrintLog
        fields = '__all__'


class MaterialTestPlanCreateSerializer(serializers.ModelSerializer):

    material_list = serializers.ListField(write_only=True, default=[])

    class Meta:
        model = MaterialTestPlan
        fields = '__all__'

    @atomic
    def create(self, validated_data):
        validated_data['plan_uid'] = f"JH{datetime.now().strftime('%Y%m%d%H%M%S')}"
        material_list = validated_data.pop('material_list')
        material_test_plan = super().create(validated_data)
        for material_dic in material_list:
            material_name = material_dic.get('material_name')
            material_sample_name = material_dic.get('material_sample_name', None)
            material_batch = material_dic.get('material_batch')
            material_supplier = material_dic.get('material_supplier', None)
            material_tmh = material_dic.get('material_tmh')
            material_wlxxid = material_dic.get('material_wlxxid')
            material = ExamineMaterial.objects.filter(batch=material_batch,
                                                      wlxxid=material_wlxxid).first()
            if not material:
                material = ExamineMaterial.objects.create(batch=material_batch,
                                                          name=material_name,
                                                          sample_name=material_sample_name,
                                                          supplier=material_supplier,
                                                          tmh=material_tmh,
                                                          wlxxid=material_wlxxid)
            MaterialTestPlanDetail.objects.create(material_test_plan=material_test_plan,
                                                  material=material,recorder=self.context['request'].user,
                                                  sampling_user=self.context['request'].user)
        return material_test_plan


class MaterialTestPlanDetailSerializer(serializers.ModelSerializer):
    material_name = serializers.ReadOnlyField(source='material.name')
    material_tmh = serializers.ReadOnlyField(source='material.tmh')
    material_batch = serializers.ReadOnlyField(source='material.batch')

    class Meta:
        model = MaterialTestPlanDetail
        fields = '__all__'


class MaterialTestPlanSerializer(serializers.ModelSerializer):
    material_list = MaterialTestPlanDetailSerializer(many=True)

    class Meta:
        model = MaterialTestPlan
        fields = '__all__'
