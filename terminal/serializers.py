from django.db.models import Q
from rest_framework import serializers

from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.models import ProductClassesPlan, BatchingClassesPlan, BatchingProductPlanRelation
from terminal.models import BatchChargeLog, EquipOperationLog, WeightBatchingLog, FeedingLog, WeightTankStatus, \
    WeightPackageLog


class BatchChargeLogSerializer(BaseModelSerializer):
    class Meta:
        model = BatchChargeLog
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class BatchChargeLogCreateSerializer(BaseModelSerializer):

    def create(self, validated_data):
        classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=validated_data['plan_classes_uid']).first()
        if not classes_plan:
            raise serializers.ValidationError('该计划编号错误')
        validated_data['production_factory_date'] = classes_plan.work_schedule_plan.plan_schedule.day_time
        validated_data['production_classes'] = classes_plan.work_schedule_plan.classes.global_name
        validated_data['production_group'] = classes_plan.work_schedule_plan.group.global_name
        # validated_data['batch_time'] = datetime.datetime.now()
        # TODO 后期根据扫描的条形码找到绑定的原材料数据
        validated_data['material_name'] = 'TEST_MATERIAL'
        validated_data['material_no'] = 'TEST_NO'
        validated_data['plan_weight'] = 111
        validated_data['actual_weight'] = 111

        return super().create(validated_data)

    class Meta:
        model = BatchChargeLog
        fields = ('equip_no', 'plan_classes_uid', 'product_no', 'bra_code',
                  'status', 'batch_classes', 'batch_group', 'trains')


class EquipOperationLogSerializer(BaseModelSerializer):

    class Meta:
        model = EquipOperationLog
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class BatchingClassesPlanSerializer(BaseModelSerializer):
    dev_type_name = serializers.CharField(source='weigh_cnt_type.weigh_batching.product_batching.dev_type.category_name', read_only=True)
    product_no = serializers.CharField(source='weigh_cnt_type.weigh_batching.product_batching.stage_product_batch_no', read_only=True)
    product_factory_date = serializers.CharField(source='work_schedule_plan.plan_schedule.day_time', read_only=True)
    plan_trains = serializers.IntegerField(source='plan_package', read_only=True)
    classes = serializers.CharField(source='work_schedule_plan.classes.global_name', read_only=True)
    dev_type = serializers.CharField(source='weigh_cnt_type.weigh_batching.product_batching.stage_product_batch_no', read_only=True)

    class Meta:
        model = BatchingClassesPlan
        fields = '__all__'


class WeightBatchingLogSerializer(BaseModelSerializer):

    class Meta:
        model = WeightBatchingLog
        fields = ('material_no', 'material_name', 'bra_code', 'plan_weight', 'actual_weight', 'tank_no', 'created_date')


class WeightBatchingLogCreateSerializer(BaseModelSerializer):

    def validate(self, attr):
        batching_classes_plan = BatchingClassesPlan.objects.filter(plan_batching_uid=attr['plan_batching_uid']).first()
        if not batching_classes_plan:
            raise serializers.ValidationError('参数错误')
        attr['trains'] = batching_classes_plan.plan_package
        attr['production_factory_date'] = batching_classes_plan.work_schedule_plan.plan_schedule.day_time
        attr['production_classes'] = batching_classes_plan.work_schedule_plan.classes.global_name
        attr['production_group'] = batching_classes_plan.work_schedule_plan.group.global_name
        # attr['batch_time'] = datetime.datetime.now()
        # TODO 后期根据扫描的条形码找到绑定的原材料数据
        attr['material_name'] = 'TEST_MATERIAL'
        attr['material_no'] = 'TEST_NO'
        attr['actual_weight'] = 111
        material_demand = batching_classes_plan.classes_demands.filter(
            material__material_no=attr['material_no']).first()
        attr['plan_weight'] = material_demand.plan_weight if material_demand else 0
        return attr

    class Meta:
        model = WeightBatchingLog
        fields = ('equip_no', 'plan_batching_uid', 'product_no', 'bra_code', 'quantity',
                  'batch_classes', 'batch_group', 'tank_no', 'location_no', 'dev_type')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class FeedingLogSerializer(BaseModelSerializer):

    class Meta:
        model = FeedingLog
        fields = ('feeding_port', 'material_name', 'created_date')
        read_only_fields = ('created_date', )


class WeightTankStatusSerializer(BaseModelSerializer):

    class Meta:
        model = WeightTankStatus
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class WeightPackageLogSerializer(BaseModelSerializer):

    class Meta:
        model = WeightPackageLog
        fields = '__all__'


class WeightPackageLogCreateSerializer(BaseModelSerializer):
    material_details = serializers.SerializerMethodField(read_only=True)

    def get_material_details(self, obj):
        return BatchingClassesPlan.objects.get(plan_batching_uid=obj.plan_batching_uid).weigh_cnt_type.\
            weighbatchingdetail_set.values('material__material_no', 'standard_weight')

    def validate(self, attr):
        begin_trains = attr['begin_trains']
        end_trains = attr['end_trains']
        if begin_trains > end_trains:
            raise serializers.ValidationError('开始车次不得大于结束车次')
        if WeightPackageLog.objects.filter(Q(begin_trains__lte=begin_trains, end_trains__gte=begin_trains) |
                                           Q(end_trains__gte=end_trains, end_trains__lte=end_trains),
                                           plan_batching_uid=attr['plan_batching_uid']).exists():
            raise serializers.ValidationError('车次打印重复')
        batching_classes_plan = BatchingClassesPlan.objects.filter(plan_batching_uid=attr['plan_batching_uid']).first()
        if not batching_classes_plan:
            raise serializers.ValidationError('参数错误')
        attr['production_factory_date'] = batching_classes_plan.work_schedule_plan.plan_schedule.day_time
        attr['production_classes'] = batching_classes_plan.work_schedule_plan.classes.global_name
        attr['production_group'] = batching_classes_plan.work_schedule_plan.group.global_name
        # attr['batch_time'] = datetime.datetime.now()
        return attr

    class Meta:
        model = WeightPackageLog
        fields = ('equip_no', 'plan_batching_uid', 'product_no', 'batch_classes', 'bra_code',
                  'batch_group', 'location_no', 'dev_type', 'begin_trains', 'end_trains', 'quantity',
                  'production_factory_date', 'production_classes', 'production_group', 'created_date',
                  'material_details')
        read_only_fields = ('production_factory_date', 'production_classes',
                            'production_group', 'created_date', 'material_details')


class WeightPackageUpdateLogSerializer(BaseModelSerializer):

    def update(self, instance, validated_data):
        instance.times += 1
        instance.save()
        return instance

    class Meta:
        model = WeightPackageLog
        fields = ('id', 'equip_no', 'plan_batching_uid', 'product_no', 'batch_classes', 'bra_code',
                  'batch_group', 'location_no', 'dev_type', 'begin_trains', 'end_trains', 'quantity',
                  'production_factory_date', 'production_classes', 'production_group', 'created_date',
                  'material_details')
        read_only_fields = ('equip_no', 'plan_batching_uid', 'product_no', 'batch_classes', 'bra_code',
                            'batch_group', 'location_no', 'dev_type', 'begin_trains', 'end_trains', 'quantity',
                            'production_factory_date', 'production_classes', 'production_group', 'created_date',
                            'material_details')
