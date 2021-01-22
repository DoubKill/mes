from django.db.models import Q, Sum
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.models import ProductClassesPlan, BatchingClassesPlan
from terminal.models import BatchChargeLog, EquipOperationLog, WeightBatchingLog, FeedingLog, WeightTankStatus, \
    WeightPackageLog, MaterialSupplierCollect


class BatchChargeLogSerializer(BaseModelSerializer):
    class Meta:
        model = BatchChargeLog
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class BatchChargeLogCreateSerializer(BaseModelSerializer):

    def validate(self, attrs):
        bra_code = attrs['bra_code']
        mat_supplier_collect = MaterialSupplierCollect.objects.filter(bra_code=bra_code, delete_flag=False).first()
        if not mat_supplier_collect:
            raise serializers.ValidationError('未找到该条形码信息！')
        classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=attrs['plan_classes_uid']).first()
        if not classes_plan:
            raise serializers.ValidationError('该计划不存在')
        attrs['production_factory_date'] = classes_plan.work_schedule_plan.plan_schedule.day_time
        attrs['production_classes'] = classes_plan.work_schedule_plan.classes.global_name
        attrs['production_group'] = classes_plan.work_schedule_plan.group.global_name
        attrs['product_no'] = classes_plan.product_batching.stage_product_batch_no
        attrs['equip_no'] = classes_plan.equip.equip_no
        if mat_supplier_collect.material_no not in classes_plan.product_batching.batching_material_nos:
            attrs['status'] = 2
        # validated_data['batch_time'] = datetime.datetime.now()
        attrs['material_name'] = mat_supplier_collect.material_name
        attrs['material_no'] = mat_supplier_collect.material_no
        return attrs

    class Meta:
        model = BatchChargeLog
        fields = ('plan_classes_uid', 'bra_code', 'batch_classes', 'batch_group', 'trains')


class EquipOperationLogSerializer(BaseModelSerializer):
    class Meta:
        model = EquipOperationLog
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class BatchingClassesPlanSerializer(BaseModelSerializer):
    dev_type_name = serializers.CharField(source='weigh_cnt_type.weigh_batching'
                                                 '.product_batching.dev_type.category_name', read_only=True)
    product_no = serializers.CharField(source='weigh_cnt_type.weigh_batching.product_batching.stage_product_batch_no',
                                       read_only=True)
    product_factory_date = serializers.CharField(source='work_schedule_plan.plan_schedule.day_time', read_only=True)
    plan_trains = serializers.IntegerField(source='plan_package', read_only=True)
    classes = serializers.CharField(source='work_schedule_plan.classes.global_name', read_only=True)
    finished_trains = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_finished_trains(obj):
        finished_trains = WeightPackageLog.objects.filter(plan_batching_uid=obj.plan_batching_uid
                                                          ).aggregate(trains=Sum('quantity'))['trains']
        return finished_trains if finished_trains else 0

    class Meta:
        model = BatchingClassesPlan
        fields = '__all__'


class WeightBatchingLogSerializer(BaseModelSerializer):
    class Meta:
        model = WeightBatchingLog
        fields = ('material_no', 'material_name', 'bra_code', 'status',
                  'plan_weight', 'actual_weight', 'tank_no', 'created_date')


class WeightBatchingLogCreateSerializer(BaseModelSerializer):

    def validate(self, attr):
        batching_classes_plan = BatchingClassesPlan.objects.filter(plan_batching_uid=attr['plan_batching_uid']).first()
        if not batching_classes_plan:
            raise serializers.ValidationError('参数错误')
        mat_supplier_collect = MaterialSupplierCollect.objects.filter(bra_code=attr['bra_code'], delete_flag=False).first()
        if not mat_supplier_collect:
            raise serializers.ValidationError('未找到该条形码信息！')
        attr['trains'] = batching_classes_plan.plan_package
        attr['production_factory_date'] = batching_classes_plan.work_schedule_plan.plan_schedule.day_time
        attr['production_classes'] = batching_classes_plan.work_schedule_plan.classes.global_name
        attr['production_group'] = batching_classes_plan.work_schedule_plan.group.global_name
        attr['dev_type'] = batching_classes_plan.weigh_cnt_type.weigh_batching.product_batching.dev_type.category_name
        attr['product_no'] = batching_classes_plan.weigh_cnt_type.weigh_batching.product_batching.stage_product_batch_no
        # attr['batch_time'] = datetime.datetime.now()
        if mat_supplier_collect.material_no not in batching_classes_plan.weigh_cnt_type.weighting_material_nos:
            attr['status'] = 2
        attr['material_name'] = mat_supplier_collect.material_name
        attr['material_no'] = mat_supplier_collect.material_no
        return attr

    class Meta:
        model = WeightBatchingLog
        fields = ('equip_no', 'plan_batching_uid', 'bra_code', 'quantity',
                  'batch_classes', 'batch_group', 'tank_no', 'location_no')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class FeedingLogSerializer(BaseModelSerializer):
    class Meta:
        model = FeedingLog
        fields = ('feeding_port', 'material_name', 'created_date')
        read_only_fields = ('created_date',)


class WeightTankStatusSerializer(BaseModelSerializer):
    tank_no = serializers.CharField(max_length=64, help_text='料罐编码',
                                    validators=[UniqueValidator(queryset=WeightTankStatus.objects.all(),
                                                                message='该料罐编号已存在！')])

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

    @staticmethod
    def get_material_details(obj):
        return BatchingClassesPlan.objects.get(plan_batching_uid=obj.plan_batching_uid).weigh_cnt_type. \
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
        attr['dev_type'] = batching_classes_plan.weigh_cnt_type.weigh_batching.product_batching.dev_type.category_name
        attr['product_no'] = batching_classes_plan.weigh_cnt_type.weigh_batching.product_batching.stage_product_batch_no
        weigh_type_dict = {1: '-a', 2: '-b', 3: '-s'}
        attr['material_no'] = attr['product_no'] + weigh_type_dict[batching_classes_plan.weigh_cnt_type.weigh_type]
        attr['material_name'] = attr['product_no'] + weigh_type_dict[batching_classes_plan.weigh_cnt_type.weigh_type]
        return attr

    class Meta:
        model = WeightPackageLog
        fields = ('equip_no', 'plan_batching_uid', 'product_no', 'batch_classes', 'bra_code',
                  'batch_group', 'location_no', 'dev_type', 'begin_trains', 'end_trains', 'quantity',
                  'production_factory_date', 'production_classes', 'production_group', 'created_date',
                  'material_details')
        read_only_fields = ('production_factory_date', 'production_classes', 'dev_type', 'product_no',
                            'production_group', 'created_date', 'material_details')


class WeightPackageUpdateLogSerializer(BaseModelSerializer):
    material_details = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_material_details(obj):
        return BatchingClassesPlan.objects.get(plan_batching_uid=obj.plan_batching_uid).weigh_cnt_type. \
            weighbatchingdetail_set.values('material__material_no', 'standard_weight')

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


class BatchChargeLogListSerializer(BaseModelSerializer):
    mixing_finished = serializers.SerializerMethodField(help_text='混炼/终炼', read_only=True)

    def get_mixing_finished(self, obj):
        product_no = obj.product_no
        if "FM" in product_no:
            return '终炼'
        else:
            return "混炼"

    class Meta:
        model = BatchChargeLog
        fields = '__all__'


class WeightBatchingLogListSerializer(BaseModelSerializer):
    weight_batch_no = serializers.SerializerMethodField(help_text='小料配方', read_only=True)

    def get_weight_batch_no(self, obj):
        try:
            plan_batching_uid = obj.plan_batching_uid
            bcp_obj = BatchingClassesPlan.objects.filter(plan_batching_uid=plan_batching_uid, delete_flag=False).first()
            weight_batch_no = bcp_obj.weigh_cnt_type.weigh_batching.weight_batch_no
            return weight_batch_no
        except Exception as e:
            # print(e)
            return None

    class Meta:
        model = WeightBatchingLog
        fields = '__all__'


class MaterialSupplierCollectSerializer(BaseModelSerializer):
    child_system_name = serializers.CharField(source='child_system.global_name', read_only=True, default=None)

    class Meta:
        model = MaterialSupplierCollect
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS
