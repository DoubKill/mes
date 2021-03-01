import requests
from django.db.models import Q, Sum
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from mes import settings
from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.models import ProductClassesPlan, BatchingClassesPlan, BatchingClassesEquipPlan
from production.models import PalletFeedbacks
from terminal.models import EquipOperationLog, WeightBatchingLog, FeedingLog, WeightTankStatus, \
    WeightPackageLog, MaterialSupplierCollect, FeedingMaterialLog, LoadMaterialLog
import logging
logger = logging.getLogger('api_log')


def generate_bra_code(plan_id, equip_no, factory_date, classes, begin_trains, end_trains, update=False):
    # 后端生成，工厂编码E101 + 称量机台号 + 小料计划的工厂日期8位补零 + 班次1 - 3 + 开始车次+结束车次。
    # 重复打印条码规则不变，重新生成会比较麻烦，根据修改的工厂时间班次来生成，序列号改成字母。从A~Z
    classes_dict = {'早班': '1', '中班': '2', '夜班': '3'}
    return 'E101{}{}{}{}{}{}{}'.format(plan_id, equip_no, ''.join(str(factory_date).split('-')),
                                       classes_dict[classes], begin_trains, end_trains,
                                       'R' if update else '')


class LoadMaterialLogSerializer(BaseModelSerializer):
    product_no = serializers.ReadOnlyField(source='feed_log.product_no')
    created_date = serializers.DateTimeField(source='feed_log.feed_begin_time')
    trains = serializers.ReadOnlyField(source='feed_log.trains')

    class Meta:
        model = LoadMaterialLog
        fields = '__all__'


class LoadMaterialLogCreateSerializer(BaseModelSerializer):
    bra_code = serializers.CharField(write_only=True)

    def validate(self, attrs):
        bra_code = attrs['bra_code']
        # 条码来源有三种，子系统、收皮条码，称量打包条码
        mat_supplier_collect = MaterialSupplierCollect.objects.filter(bra_code=bra_code,
                                                                      delete_flag=False,
                                                                      material__isnull=False).first()
        pallet_feedback = PalletFeedbacks.objects.filter(lot_no=bra_code).first()
        weight_package = WeightPackageLog.objects.filter(bra_code=bra_code).first()
        material_no = material_name = None
        if mat_supplier_collect:
            material_no = mat_supplier_collect.material.material_no
            material_name = mat_supplier_collect.material.material_name
        if pallet_feedback:
            material_no = pallet_feedback.product_no
            material_name = pallet_feedback.product_no
        if weight_package:
            material_no = weight_package.material_no
            material_name = weight_package.material_name
        if not material_no:
            raise serializers.ValidationError('未找到该条形码信息！')
        classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=attrs['plan_classes_uid']).first()
        if not classes_plan:
            raise serializers.ValidationError('该计划不存在')
        attrs['equip_no'] = classes_plan.equip.equip_no
        attrs['material_name'] = material_name
        attrs['material_no'] = material_no
        if material_no not in classes_plan.product_batching.batching_material_nos:
            attrs['status'] = 2
        else:
            attrs['status'] = 1
        # 发送条码信息到群控
        try:
            resp = requests.post(url=settings.AUXILIARY_URL + 'api/v1/production/current_weigh/', data=attrs)
            code = resp.status_code
            if code != 200:
                logger.error('条码信息下发错误：{}'.format(resp.text))
        except Exception:
            logger.error('群控服务器错误！')
        if material_no not in classes_plan.product_batching.batching_material_nos:
            raise serializers.ValidationError('条码错误，该物料不在生产配方中！')
        return attrs

    def create(self, validated_data):
        return validated_data

    class Meta:
        model = FeedingMaterialLog
        fields = ('plan_classes_uid', 'bra_code', 'batch_classes', 'batch_group', 'trains')


class EquipOperationLogSerializer(BaseModelSerializer):
    class Meta:
        model = EquipOperationLog
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class BatchingClassesEquipPlanSerializer(BaseModelSerializer):
    dev_type_name = serializers.CharField(source='batching_class_plan.weigh_cnt_type.weigh_batching'
                                                 '.product_batching.dev_type.category_name', read_only=True)
    product_no = serializers.CharField(source='batching_class_plan.weigh_cnt_type.weigh_batching.'
                                              'product_batching.stage_product_batch_no',
                                       read_only=True)
    product_factory_date = serializers.CharField(source='batching_class_plan.work_schedule_plan.plan_schedule.day_time',
                                                 read_only=True)
    plan_trains = serializers.IntegerField(source='packages', read_only=True)
    classes = serializers.CharField(source='batching_class_plan.work_schedule_plan.classes.global_name', read_only=True)
    finished_trains = serializers.SerializerMethodField(read_only=True)
    plan_batching_uid = serializers.ReadOnlyField(source='batching_class_plan.plan_batching_uid')

    @staticmethod
    def get_finished_trains(obj):
        finished_trains = WeightPackageLog.objects.filter(plan_batching_uid=obj.batching_class_plan.plan_batching_uid
                                                          ).aggregate(trains=Sum('quantity'))['trains']
        return finished_trains if finished_trains else 0

    class Meta:
        model = BatchingClassesEquipPlan
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
        mat_supplier_collect = MaterialSupplierCollect.objects.filter(bra_code=attr['bra_code'],
                                                                      delete_flag=False,
                                                                      material__isnull=False).first()
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
        attr['material_name'] = mat_supplier_collect.material.material_name
        attr['material_no'] = mat_supplier_collect.material.material_no
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


class WeightPackageRetrieveLogSerializer(BaseModelSerializer):
    material_details = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_material_details(obj):
        return BatchingClassesPlan.objects.get(plan_batching_uid=obj.plan_batching_uid).weigh_cnt_type. \
            weight_details.values('material__material_no', 'standard_weight')

    class Meta:
        model = WeightPackageLog
        fields = '__all__'


class WeightPackageLogCreateSerializer(BaseModelSerializer):
    material_details = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_material_details(obj):
        return BatchingClassesPlan.objects.get(plan_batching_uid=obj.plan_batching_uid).weigh_cnt_type. \
            weight_details.values('material__material_no', 'standard_weight')

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
        weigh_type_dict = {1: '硫磺包' + str(batching_classes_plan.weigh_cnt_type.tag),
                           2: '细料包' + str(batching_classes_plan.weigh_cnt_type.tag)}
        attr['material_no'] = attr['product_no'] + weigh_type_dict[batching_classes_plan.weigh_cnt_type.weigh_type]
        attr['material_name'] = attr['product_no'] + weigh_type_dict[batching_classes_plan.weigh_cnt_type.weigh_type]
        attr['bra_code'] = generate_bra_code(batching_classes_plan.id,
                                             attr['equip_no'],
                                             attr['production_factory_date'],
                                             attr['production_classes'],
                                             attr['begin_trains'],
                                             attr['end_trains'])
        return attr

    class Meta:
        model = WeightPackageLog
        fields = ('equip_no', 'plan_batching_uid', 'product_no', 'batch_classes', 'bra_code',
                  'batch_group', 'location_no', 'dev_type', 'begin_trains', 'end_trains', 'quantity',
                  'production_factory_date', 'production_classes', 'production_group', 'created_date',
                  'material_details')
        read_only_fields = ('production_factory_date', 'production_classes', 'dev_type', 'product_no',
                            'production_group', 'created_date', 'material_details', 'bra_code')


class WeightPackageUpdateLogSerializer(BaseModelSerializer):
    material_details = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_material_details(obj):
        return BatchingClassesPlan.objects.get(plan_batching_uid=obj.plan_batching_uid).weigh_cnt_type. \
            weight_details.values('material__material_no', 'standard_weight')

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


class WeightPackagePartialUpdateLogSerializer(BaseModelSerializer):

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        batching_classes = BatchingClassesPlan.objects.filter(plan_batching_uid=instance.plan_batching_uid).first()
        instance.bra_code = generate_bra_code(batching_classes.id,
                                              instance.equip_no,
                                              instance.production_factory_date,
                                              instance.production_classes,
                                              instance.begin_trains,
                                              instance.end_trains,
                                              update=True)
        instance.save()
        return instance

    class Meta:
        model = WeightPackageLog
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class LoadMaterialLogListSerializer(serializers.ModelSerializer):
    mixing_finished = serializers.SerializerMethodField(help_text='混炼/终炼', read_only=True)
    product_no = serializers.ReadOnlyField(source='feed_log.product_no')
    created_date = serializers.DateTimeField(source='feed_log.feed_begin_time')
    trains = serializers.ReadOnlyField(source='feed_log.trains')
    production_factory_date = serializers.ReadOnlyField(source='feed_log.production_classes')
    production_classes = serializers.ReadOnlyField(source='feed_log.production_classes')

    def get_mixing_finished(self, obj):
        product_no = obj.feed_log.product_no
        if "FM" in product_no:
            return '终炼'
        else:
            return "混炼"

    class Meta:
        model = LoadMaterialLog
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
