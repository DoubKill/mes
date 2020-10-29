from datetime import datetime

from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator, UniqueValidator

from django.db.models import Sum, Max

from mes.base_serializer import BaseModelSerializer

from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.models import ProductClassesPlan
from plan.uuidfield import UUidTools
from production.models import TrainsFeedbacks, PalletFeedbacks
from quality.models import TestMethod, MaterialTestOrder, \
    MaterialTestResult, MaterialDataPointIndicator, MaterialTestMethod, TestType, DataPoint, DealSuggestion, \
    MaterialDealResult


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

    class Meta:
        model = MaterialDataPointIndicator
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialTestResultSerializer(BaseModelSerializer):
    class Meta:
        model = MaterialTestResult
        exclude = ('data_point_indicator', 'material_test_order', 'test_factory_date', 'test_class',
                   'test_group', 'test_times', 'mes_result', 'result')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialTestOrderSerializer(BaseModelSerializer):
    order_results = MaterialTestResultSerializer(many=True, required=True)
    actual_trains = serializers.IntegerField(min_value=0)

    @atomic()
    def create(self, validated_data):
        order_results = validated_data.pop('order_results', None)
        test_order = MaterialTestOrder.objects.filter(lot_no=validated_data['lot_no'],
                                                      actual_trains=validated_data['actual_trains']).first()
        plan = ProductClassesPlan.objects.filter(plan_classes_uid=validated_data['plan_classes_uid']).first()
        if not plan:
            raise serializers.ValidationError('该计划编号不存在')
        validated_data['plan_classes_uid'] = plan.work_schedule_plan.group.global_name
        if test_order:
            instance = test_order
            created = False
        else:
            validated_data['material_test_order_uid'] = UUidTools.uuid1_hex('KJ')
            instance = super().create(validated_data)
            created = True

        material_no = validated_data['product_no']
        for item in order_results:
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
            MaterialTestResult.objects.create(**item)
        return instance

    class Meta:
        model = MaterialTestOrder
        exclude = ('material_test_order_uid', 'production_group')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialTestResultListSerializer(BaseModelSerializer):
    level = serializers.CharField(source='data_point_indicator.level', read_only=True, default=None)

    class Meta:
        model = MaterialTestResult
        fields = '__all__'


class MaterialTestOrderListSerializer(BaseModelSerializer):
    order_results = MaterialTestResultListSerializer(many=True)

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

    def get_day_time(self, obj):
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        if not pfb_obj:
            return None
        pcp_obj = ProductClassesPlan.objects.filter(plan_classes_uid=pfb_obj.plan_classes_uid).first()
        if pcp_obj:
            return pcp_obj.work_schedule_plan.plan_schedule.day_time
        else:
            return None

    def get_classes_group(self, obj):
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        if not pfb_obj:
            return None
        pcp_obj = ProductClassesPlan.objects.filter(plan_classes_uid=pfb_obj.plan_classes_uid).first()
        if pcp_obj:
            return f"{pfb_obj.classes}/{pcp_obj.work_schedule_plan.group.global_name}"
        else:
            return None

    def get_equip_no(self, obj):
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        if not pfb_obj:
            return None
        return pfb_obj.equip_no

    def get_product_no(self, obj):
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        if not pfb_obj:
            return None
        return pfb_obj.product_no

    def get_actual_weight(self, obj):
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        if not pfb_obj:
            return None
        return pfb_obj.actual_weight

    def get_residual_weight(self, obj):
        return None

    def get_test(self, obj):
        mtr_list = []
        # 找到每个车次检测次数最多的那一条
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        if not pfb_obj:
            return None
        for i in range(pfb_obj.begin_trains, pfb_obj.end_trains + 1):
            mto_obj = MaterialTestOrder.objects.filter(lot_no=pfb_obj.lot_no, product_no=pfb_obj.product_no,
                                                       plan_classes_uid=pfb_obj.plan_classes_uid,
                                                       production_equip_no=pfb_obj.equip_no, actual_trains=i).last()
            if not mto_obj:
                continue
            mtr_obj = MaterialTestResult.objects.filter(material_test_order=mto_obj).order_by('test_times').last()
            if not mtr_obj:
                continue
            mtr_list.append(mtr_obj)
        # 找到level等级最大的那一条
        if len(mtr_list) == 0:
            return None
        max_mtr = mtr_list[0]
        for mtr_obj in mtr_list:
            if mtr_obj.data_point_indicator.level > max_mtr.data_point_indicator.level:
                max_mtr = mtr_obj
        if max_mtr.test_times == 1:
            test_status = '正常'
        elif max_mtr.test_times > 1:
            test_status = '复检'
        else:
            test_status = None  # 检测状态
        test_factory_date = max_mtr.test_factory_date  # 检测时间
        test_class = max_mtr.test_class  # 检测班次
        test_user = max_mtr.created_user.username  # 检测员
        test_note = max_mtr.material_test_order.note  # 备注
        result = max_mtr.result  # 检测结果
        return {'test_status': test_status, 'test_factory_date': test_factory_date, 'test_class': test_class,
                'test_user': test_user,
                'test_note': test_note, 'result': result}

    def get_mtr_list(self, obj):
        mtr_list_return = {}
        # 找到每个车次检测次数最多的那一条
        table_head_count = []
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        if not pfb_obj:
            return None
        for i in range(pfb_obj.begin_trains, pfb_obj.end_trains + 1):
            mto_obj = MaterialTestOrder.objects.filter(lot_no=pfb_obj.lot_no, product_no=pfb_obj.product_no,
                                                       plan_classes_uid=pfb_obj.plan_classes_uid,
                                                       production_equip_no=pfb_obj.equip_no, actual_trains=i).last()
            if not mto_obj:
                continue
            mtr_list_return[i] = []
            # 先弄出表头
            table_head = mto_obj.order_results.all().values('test_indicator_name').annotate()
            for table_head_dict in table_head:
                table_head_count.append(table_head_dict['test_indicator_name'])

            mtr_list = mto_obj.order_results.all().values('test_indicator_name').annotate(
                test_times=Max('test_times')).values('test_indicator_name', 'value',
                                                     'result', 'test_times')
            for mtr_dict in mtr_list:
                mtr_dict['status'] = f"{mtr_dict['test_times']}:{mtr_dict['result']}"
                mtr_list_return[i].append(mtr_dict)
        table_head_set = list(set(table_head_count))
        mtr_list_return['table_head'] = table_head_set
        return mtr_list_return

    def get_actual_trains(self, obj):
        at_list = []
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        if not pfb_obj:
            return None
        for i in range(pfb_obj.begin_trains, pfb_obj.end_trains + 1):
            at_list.append(str(i))
        at_str = "/".join(at_list)
        return at_str

    def get_operation_user(self, obj):
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        if not pfb_obj:
            return None
        return pfb_obj.operation_user

    class Meta:
        model = MaterialDealResult
        fields = (
            'id', 'day_time', 'lot_no', 'classes_group', 'equip_no', 'product_no', 'actual_weight', 'residual_weight',
            'production_factory_date', 'valid_time', 'test', 'print_time', 'deal_user', 'deal_time', 'suggestion_desc',
            'mtr_list', 'actual_trains', 'operation_user')
