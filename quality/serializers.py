import time
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
from plan.uuidfield import UUidTools
from production.models import PalletFeedbacks
from quality.models import TestMethod, MaterialTestOrder, \
    MaterialTestResult, MaterialDataPointIndicator, MaterialTestMethod, TestType, DataPoint, DealSuggestion, \
    MaterialDealResult, LevelResult, TestIndicator, LabelPrint, Batch, TestDataPoint, BatchMonth, BatchDay, BatchEquip, \
    BatchClass, BatchProductNo, MaterialDealResult, LevelResult, TestIndicator, LabelPrint
from recipe.models import MaterialAttribute


class TestIndicatorSerializer(BaseModelSerializer):
    name = serializers.CharField(help_text='指标名称', validators=[UniqueValidator(queryset=TestIndicator.objects.all(),
                                                                               message='该指标名称已存在！')])

    def create(self, validated_data):
        validated_data['no'] = UUidTools.uuid1_hex('TD')
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
        validated_data['no'] = UUidTools.uuid1_hex('TM')
        return super(TestMethodSerializer, self).create(validated_data)

    class Meta:
        model = TestMethod
        fields = ('id', 'name', 'test_type', 'test_type_name', 'test_indicator_name')


class TestTypeSerializer(BaseModelSerializer):
    name = serializers.CharField(help_text='试验类型名称', validators=[UniqueValidator(queryset=TestType.objects.all(),
                                                                                 message='该试验类型名称已存在！')])
    test_indicator_name = serializers.CharField(source='test_indicator.name', read_only=True)

    def create(self, validated_data):
        validated_data['no'] = UUidTools.uuid1_hex('TP')
        return super().create(validated_data)

    class Meta:
        model = TestType
        fields = ('id', 'name', 'test_indicator', 'test_indicator_name')


class DataPointSerializer(BaseModelSerializer):
    test_type_name = serializers.CharField(source='test_type.name', read_only=True)
    test_indicator_name = serializers.CharField(source='test_type.test_indicator.name', read_only=True)

    def create(self, validated_data):
        validated_data['no'] = UUidTools.uuid1_hex('TM')
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

    @atomic()
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
            validated_data['material_test_order_uid'] = UUidTools.uuid1_hex('KJ')
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
                    item['mes_result'] = '不合格'
                    item['level'] = 3
            else:
                item['mes_result'] = '不合格'
                item['level'] = 3
            item['created_user'] = self.context['request'].user  # 加一个create_user
            item['test_class'] = validated_data['production_class']  # 暂时先这么写吧
            MaterialTestResult.objects.create(**item)
        return instance

    class Meta:
        model = MaterialTestOrder
        exclude = ('material_test_order_uid', 'production_group')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialTestResultListSerializer(BaseModelSerializer):
    class Meta:
        model = MaterialTestResult
        fields = ('test_times', 'value', 'data_point_name', 'test_method_name',
                  'test_indicator_name', 'mes_result', 'result', 'machine_name', 'level')


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
    day_time = serializers.SerializerMethodField(read_only=True, help_text='工厂时间')
    classes_group = serializers.SerializerMethodField(read_only=True, help_text='生产班次/班组')
    equip_no = serializers.SerializerMethodField(read_only=True, help_text='生产机台')
    product_no = serializers.SerializerMethodField(read_only=True, help_text='胶料编码')
    actual_weight = serializers.SerializerMethodField(read_only=True, help_text='收皮重量')
    residual_weight = serializers.SerializerMethodField(read_only=True, help_text='余量')
    test = serializers.SerializerMethodField(read_only=True, help_text='余量')
    suggestion_desc = serializers.CharField(source='deal_opinion.suggestion_desc', read_only=True)
    mtr_list = serializers.SerializerMethodField(read_only=True, )
    actual_trains = serializers.SerializerMethodField(read_only=True, )
    operation_user = serializers.SerializerMethodField(read_only=True, help_text='收皮员')
    deal_suggestion = serializers.SerializerMethodField(read_only=True, help_text='处理意见')
    deal_user = serializers.SerializerMethodField(read_only=True, help_text='处理人')
    deal_time = serializers.SerializerMethodField(read_only=True, help_text='处理时间')
    valid_time = serializers.SerializerMethodField(read_only=True, help_text="有效时间")

    def get_valid_time(self, obj):
        product_no = self.product_no
        product_time = obj.production_factory_date
        material_detail = MaterialAttribute.objects.filter(material__material_no=product_no).first()
        if not material_detail:
            return None
        unit = material_detail.validity_unit
        if unit in ["天", "days", "day"]:
            param = {"days": material_detail.period_of_validity}
        elif unit in ["小时", "hours", "hour"]:
            param = {"hours": material_detail.period_of_validity}
        else:
            param = {"days": material_detail.period_of_validity}
        expire_time = product_time + timedelta(**param)
        return expire_time.strftime("%Y-%m-%d %H:%M:%S")

    def get_deal_suggestion(self, obj):
        if obj.status == "已处理":
            return obj.deal_suggestion
        return None

    def get_deal_user(self, obj):
        if obj.status == "已处理":
            return obj.deal_user
        return None

    def get_deal_time(self, obj):
        if obj.status == "已处理":
            return obj.deal_time.strftime("%Y-%m-%d %H:%M:%S")
        return None

    def get_day_time(self, obj):
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        self.__setattr__("pfb_obj", pfb_obj)
        if not pfb_obj:
            return None
        pcp_obj = ProductClassesPlan.objects.filter(plan_classes_uid=pfb_obj.plan_classes_uid).first()
        if pcp_obj:
            return pcp_obj.work_schedule_plan.plan_schedule.day_time
        else:
            return None

    def get_classes_group(self, obj):
        # pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        pfb_obj = self.pfb_obj
        if not pfb_obj:
            return None
        pcp_obj = ProductClassesPlan.objects.filter(plan_classes_uid=pfb_obj.plan_classes_uid).first()
        if pcp_obj:
            return f"{pfb_obj.classes}/{pcp_obj.work_schedule_plan.group.global_name}"
        else:
            return f"{pfb_obj.classes}/None"

    def get_equip_no(self, obj):
        # pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        pfb_obj = self.pfb_obj
        if not pfb_obj:
            return None
        return pfb_obj.equip_no

    def get_product_no(self, obj):
        # pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        pfb_obj = self.pfb_obj
        if not pfb_obj:
            return None
        self.__setattr__("product_no", pfb_obj.product_no)
        return pfb_obj.product_no

    def get_actual_weight(self, obj):
        # pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        pfb_obj = self.pfb_obj
        if not pfb_obj:
            return None
        return pfb_obj.actual_weight

    def get_residual_weight(self, obj):
        return None

    def get_test(self, obj):
        mtr_list = []
        # 找到每个车次检测次数最多的那一条
        mto_set = MaterialTestOrder.objects.filter(lot_no=obj.lot_no).all()
        for mto_obj in mto_set:
            mtr_obj = MaterialTestResult.objects.filter(material_test_order=mto_obj).order_by('test_times').last()
            if not mtr_obj:
                continue
            mtr_list.append(mtr_obj)
        # 找到level等级最大的那一条
        if len(mtr_list) == 0:
            return None
        max_mtr = mtr_list[0]
        for mtr_obj in mtr_list:
            # if not mtr_obj.data_point_indicator or not max_mtr.data_point_indicator:  # 数据不在上下限范围内，这个得前端做好约束
            #     continue
            if mtr_obj.level > max_mtr.level:
                max_mtr = mtr_obj
        if max_mtr.test_times == 1:
            test_status = '正常'
        elif max_mtr.test_times > 1:
            test_status = '复检'
        else:
            test_status = None  # 检测状态
        test_factory_date = max_mtr.test_factory_date.strftime('%Y-%m-%d %H:%M:%S')  # 检测时间
        test_class = max_mtr.test_class  # 检测班次
        try:
            test_user = max_mtr.created_user.username  # 检测员
        except:
            test_user = None
        test_note = max_mtr.material_test_order.note  # 备注
        result = max_mtr.result  # 检测结果,改了
        return {'test_status': test_status, 'test_factory_date': test_factory_date, 'test_class': test_class,
                'test_user': test_user,
                'test_note': test_note, 'result': result}

    def get_mtr_list(self, obj):
        mtr_list_return = {}
        # 找到每个车次检测次数最多的那一条
        table_head_count = {}
        mto_set = MaterialTestOrder.objects.filter(lot_no=obj.lot_no).all()
        for mto_obj in mto_set:
            if not mto_obj:
                continue
            mtr_list_return[mto_obj.actual_trains] = []
            # 先弄出表头
            table_head = mto_obj.order_results.all().values('test_indicator_name',
                                                            'data_point_name').annotate().distinct()
            for table_head_dict in table_head:
                if table_head_dict['test_indicator_name'] not in table_head_count.keys():
                    table_head_count[table_head_dict['test_indicator_name']] = []
                table_head_count[table_head_dict['test_indicator_name']].append(table_head_dict['data_point_name'])
                table_head_count[table_head_dict['test_indicator_name']] = list(
                    set(table_head_count[table_head_dict['test_indicator_name']]))
            # 根据test_indicator_name分组找到啊test_times最大的
            mtr_list = mto_obj.order_results.all().values('test_indicator_name', 'data_point_name').annotate(
                max_test_times=Max('test_times')).values('test_indicator_name', 'data_point_name',
                                                         'max_test_times',
                                                         )
            mtr_max_list = []
            for mtr_max_obj in mtr_list:
                # 根据分组找到数据
                mtr_obj = MaterialTestResult.objects.filter(material_test_order=mto_obj,
                                                            test_indicator_name=mtr_max_obj['test_indicator_name'],
                                                            data_point_name=mtr_max_obj['data_point_name'],
                                                            test_times=mtr_max_obj['max_test_times']).last()
                if mtr_obj.level == 1:
                    result = '一等品'
                else:
                    result = '三等品'
                # 判断加减
                data_point_name = mtr_obj.data_point_name  # 数据点名称
                test_method_name = mtr_obj.test_method_name  # 试验方法名称
                test_indicator_name = mtr_obj.test_indicator_name  # 检测指标名称
                product_no = mtr_obj.material_test_order.product_no  # 胶料编码
                # 根据material-test-orders接口逻辑找到data_point_indicator
                material_test_method = MaterialTestMethod.objects.filter(
                    material__material_no=product_no,
                    test_method__name=test_method_name,
                    test_method__test_type__test_indicator__name=test_indicator_name,
                    data_point__name=data_point_name,
                    data_point__test_type__test_indicator__name=test_indicator_name).first()
                add_subtract = None  # 页面的加减
                if material_test_method:
                    indicator = MaterialDataPointIndicator.objects.filter(
                        material_test_method=material_test_method,
                        data_point__name=data_point_name,
                        data_point__test_type__test_indicator__name=test_indicator_name, level=1).first()
                    if indicator:  # 判断value与上下限的比较
                        if mtr_obj.value > indicator.upper_limit:
                            add_subtract = '+'
                        elif mtr_obj.value < indicator.lower_limit:
                            add_subtract = '-'

                mtr_max_list.append(
                    {'test_indicator_name': mtr_obj.test_indicator_name, 'data_point_name': mtr_obj.data_point_name,
                     'value': mtr_obj.value,
                     'result': result,
                     'max_test_times': mtr_obj.level,
                     'add_subtract': add_subtract})

            for mtr_dict in mtr_max_list:
                mtr_dict['status'] = f"{mtr_dict['max_test_times']}:{mtr_dict['result']}"
                mtr_list_return[mto_obj.actual_trains].append(mtr_dict)
        table_head_top = {}
        for i in sorted(table_head_count.items(), key=lambda x: len(x[1]), reverse=False):
            table_head_top[i[0]] = i[-1]
        mtr_list_return['table_head'] = table_head_top
        return mtr_list_return

    def get_actual_trains(self, obj):
        at_list = []
        # pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        pfb_obj = self.pfb_obj
        if not pfb_obj:
            return None
        for i in range(pfb_obj.begin_trains, pfb_obj.end_trains + 1):
            at_list.append(str(i))
        at_str = "/".join(at_list)
        return at_str

    def get_operation_user(self, obj):
        # pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        pfb_obj = self.pfb_obj
        if not pfb_obj:
            return None
        return pfb_obj.operation_user

    class Meta:
        model = MaterialDealResult
        fields = (
            'id', 'day_time', 'lot_no', 'classes_group', 'equip_no', 'product_no', 'actual_weight', 'residual_weight',
            'production_factory_date', 'valid_time', 'test', 'print_time', 'deal_user', 'deal_time', 'suggestion_desc',
            'mtr_list', 'actual_trains', 'operation_user', 'deal_result', 'deal_suggestion')


class LevelResultSerializer(BaseModelSerializer):
    """等级和结果"""

    class Meta:
        model = LevelResult
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class LabelPrintSerializer(serializers.ModelSerializer):
    """标签打印"""

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
        lb_train_count = Count('batch__lot__train__testresult',distinct=True,
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
        return TestDataPoint.objects.filter(testresult__train__lot__batch__batch_day=obj)


class BatchMonthProductNoSerializer(BatchDateProductNoSerializer):
    class Meta(BatchDateProductNoSerializer.Meta):
        model = BatchMonth

    def query_points(self, obj):
        return TestDataPoint.objects.filter(testresult__train__lot__batch__batch_month=obj)


class BatchProductNoDateCommonSerializer(serializers.ModelSerializer):
    dates = serializers.SerializerMethodField()
    batch_date_model = None
    batch_date_product_no_serializer = None

    class Meta:
        model = BatchProductNo
        fields = ['product_no', 'dates']

    def get_dates(self, batch_product_no_obj):
        batches = self.batch_date_model.objects.filter(batch__batch_product_no=batch_product_no_obj)
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
        return self.batch_date_product_no_serializer(batches, many=True).data


class BatchProductNoDaySerializer(BatchProductNoDateCommonSerializer):
    batch_date_model = BatchDay
    batch_date_product_no_serializer = BatchDayProductNoSerializer


class BatchProductNoMonthSerializer(BatchProductNoDateCommonSerializer):
    batch_date_model = BatchMonth
    batch_date_product_no_serializer = BatchMonthProductNoSerializer
