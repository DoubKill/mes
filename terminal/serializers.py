import random
from datetime import datetime

import requests
from django.db.models import Q, Sum
from django.db.utils import ConnectionDoesNotExist
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from inventory.models import MaterialOutHistory, WmsInventoryMaterial
from mes import settings
from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.models import ProductClassesPlan, BatchingClassesPlan, BatchingClassesEquipPlan
from production.models import PalletFeedbacks
from recipe.models import ZCMaterial
from terminal.models import EquipOperationLog, WeightBatchingLog, FeedingLog, WeightTankStatus, \
    WeightPackageLog, FeedingMaterialLog, LoadMaterialLog, MaterialInfo, Bin, Plan, RecipePre, ReportBasic, ReportWeight
import logging

from terminal.utils import INWeighSystem

logger = logging.getLogger('send_log')


def generate_bra_code(equip_no, factory_date, classes):
    # 后端生成，工厂编码E101 + 称量机台号 + 小料计划的工厂日期8位 + 班次1 - 3 + 四位随机数。
    # 重复打印条码规则不变，重新生成会比较麻烦，根据修改的工厂时间班次来生成，序列号改成字母。从A~Z
    random_str = ['z', 'y', 'x', 'w', 'v', 'u', 't', 's', 'r',
                  'q', 'p', 'o', 'n', 'm', 'l', 'k', 'j', 'i',
                  'h', 'g', 'f', 'e', 'd', 'c', 'b', 'a',
                  '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    classes_dict = {'早班': '1', '中班': '2', '夜班': '3'}
    return 'E101{}{}{}{}'.format(equip_no, ''.join(str(factory_date).split('-')),
                                 classes_dict[classes],
                                 ''.join(random.sample(random_str, 4)))


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
        # 条码来源有三种，wms子系统、收皮条码，称量打包条码
        bra_code = attrs['bra_code']
        try:
            # 查原材料出库履历查到原材料物料编码
            wms_stock = MaterialOutHistory.objects.using('wms').filter(
                lot_no=bra_code).values('material_no', 'material_name')
        except Exception:
            raise serializers.ValidationError('连接WMS库失败，请联系管理员！')

        pallet_feedback = PalletFeedbacks.objects.filter(lot_no=bra_code).first()
        weight_package = WeightPackageLog.objects.filter(bra_code=bra_code).first()
        material_no = material_name = None

        if wms_stock:
            msc = ZCMaterial.objects.filter(wlxxid=wms_stock[0]['material_no'],
                                            material__isnull=False).first()
            if msc:
                material_no = msc.material.material_no
                material_name = msc.material.material_name
            else:
                raise serializers.ValidationError('该物料未与MES原材料建立绑定关系！')
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
        if material_name not in classes_plan.product_batching.batching_material_names:
            attrs['status'] = 2
        else:
            attrs['status'] = 1
        # 发送条码信息到群控
        try:
            resp = requests.post(url=settings.AUXILIARY_URL + 'api/v1/production/current_weigh/',
                                 data=attrs, timeout=5)
            code = resp.status_code
            if code == 200:
                logger.error('条码信息下发成功：{}'.format(resp.text))
            else:
                logger.error('条码信息下发错误：{}'.format(resp.text))
        except Exception:
            logger.error('群控服务器错误！')
        if material_name not in classes_plan.product_batching.batching_material_names:
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
    dev_type_name = serializers.CharField(source='batching_class_plan.weigh_cnt_type'
                                                 '.product_batching.dev_type.category_name', read_only=True)
    product_no = serializers.CharField(source='batching_class_plan.weigh_cnt_type.'
                                              'product_batching.stage_product_batch_no',
                                       read_only=True)
    product_factory_date = serializers.CharField(source='batching_class_plan.work_schedule_plan.plan_schedule.day_time',
                                                 read_only=True)
    plan_trains = serializers.IntegerField(source='packages', read_only=True)
    classes = serializers.CharField(source='batching_class_plan.work_schedule_plan.classes.global_name', read_only=True)
    finished_trains = serializers.SerializerMethodField(read_only=True)
    plan_batching_uid = serializers.ReadOnlyField(source='batching_class_plan.plan_batching_uid')
    name = serializers.ReadOnlyField(source='batching_class_plan.weigh_cnt_type.name')

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
        try:
            wms_stock = MaterialOutHistory.objects.using('wms').filter(
                lot_no=attr['bra_code']).values('material_no', 'material_name')
        except Exception:
            if settings.DEBUG:
                wms_stock = None
            else:
                raise serializers.ValidationError('连接WMS库失败，请联系管理员！')
        if not wms_stock:
            raise serializers.ValidationError('该条码信息不存在！')
        msc = ZCMaterial.objects.filter(material_no=wms_stock[0]['material_no'],
                                        material__isnull=False).first()
        if msc:
            # 如果有别称
            material_no = msc.material.material_no
            material_name = msc.material.material_name
        else:
            # 否则按照wms的物料编码
            material_no = wms_stock[0]['material_no']
            material_name = wms_stock[0]['material_name']
        attr['trains'] = batching_classes_plan.plan_package
        attr['production_factory_date'] = batching_classes_plan.work_schedule_plan.plan_schedule.day_time
        attr['production_classes'] = batching_classes_plan.work_schedule_plan.classes.global_name
        attr['production_group'] = batching_classes_plan.work_schedule_plan.group.global_name
        attr['dev_type'] = batching_classes_plan.weigh_cnt_type.weigh_batching.product_batching.dev_type.category_name
        attr['product_no'] = batching_classes_plan.weigh_cnt_type.weigh_batching.product_batching.stage_product_batch_no
        # attr['batch_time'] = datetime.datetime.now()
        if wms_stock.material_no not in batching_classes_plan.weigh_cnt_type.weighting_material_nos:
            attr['status'] = 2
        attr['material_name'] = material_name
        attr['material_no'] = material_no
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
            weight_details.filter(delete_flag=False).values('material__material_no',
                                                            'standard_weight',
                                                            'weigh_cnt_type__package_cnt')

    class Meta:
        model = WeightPackageLog
        fields = '__all__'


class WeightPackageLogCreateSerializer(BaseModelSerializer):
    material_details = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_material_details(obj):
        return BatchingClassesPlan.objects.get(plan_batching_uid=obj.plan_batching_uid).weigh_cnt_type. \
            weight_details.filter(delete_flag=False).values('material__material_no',
                                                            'standard_weight',
                                                            'weigh_cnt_type__package_cnt')

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
        attr['batch_classes'] = batching_classes_plan.work_schedule_plan.classes.global_name
        attr['production_group'] = batching_classes_plan.work_schedule_plan.group.global_name
        attr['dev_type'] = batching_classes_plan.weigh_cnt_type.product_batching.dev_type.category_name
        attr['product_no'] = batching_classes_plan.weigh_cnt_type.product_batching.stage_product_batch_no
        attr['material_no'] = attr['material_name'] = batching_classes_plan.weigh_cnt_type.name
        while 1:
            bra_code = generate_bra_code(attr['equip_no'],
                                         attr['production_factory_date'],
                                         attr['production_classes'])
            if not WeightPackageLog.objects.filter(bra_code=bra_code).exists():
                break
        attr['bra_code'] = bra_code
        return attr

    class Meta:
        model = WeightPackageLog
        fields = ('equip_no', 'plan_batching_uid', 'product_no', 'batch_classes', 'bra_code',
                  'batch_group', 'location_no', 'dev_type', 'begin_trains', 'end_trains', 'quantity',
                  'production_factory_date', 'production_classes', 'production_group', 'created_date',
                  'material_details')
        read_only_fields = ('production_factory_date', 'production_classes', 'dev_type', 'product_no',
                            'production_group', 'created_date', 'material_details', 'bra_code', 'batch_classes')


class WeightPackageUpdateLogSerializer(BaseModelSerializer):
    material_details = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_material_details(obj):
        return BatchingClassesPlan.objects.get(plan_batching_uid=obj.plan_batching_uid).weigh_cnt_type. \
            weight_details.filter(delete_flag=False).values('material__material_no',
                                                            'standard_weight',
                                                            'weigh_cnt_type__package_cnt')

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
        while 1:
            bra_code = generate_bra_code(instance.equip_no,
                                         instance.production_factory_date,
                                         instance.production_classes)
            if not WeightPackageLog.objects.filter(bra_code=bra_code).exists():
                break
        instance.bra_code = bra_code
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
    production_factory_date = serializers.ReadOnlyField(source='feed_log.production_factory_date')
    production_classes = serializers.ReadOnlyField(source='feed_log.production_classes')
    equip_no = serializers.ReadOnlyField(source='feed_log.equip_no')

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


"""
小料称量序列化器
"""


class MaterialInfoSerializer(serializers.ModelSerializer):
    equip_no = serializers.CharField(write_only=True, help_text='称量机台')

    def create(self, validated_data):
        equip_no = validated_data.pop('equip_no')
        validated_data['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            instance = MaterialInfo.objects.using(equip_no).create(**validated_data)
        except ConnectionDoesNotExist:
            raise serializers.ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception:
            raise
        return instance

    class Meta:
        model = MaterialInfo
        fields = '__all__'
        read_only_fields = ('time', 'remark')


class BinSerializer(serializers.ModelSerializer):

    class Meta:
        model = Bin
        fields = '__all__'


class PlanSerializer(serializers.ModelSerializer):
    equip_no = serializers.CharField(write_only=True, help_text='称量机台')

    def create(self, validated_data):
        equip_no = validated_data.pop('equip_no')
        validated_data['planid'] = datetime.now().strftime('%Y%m%d%H%M%S')[2:]
        validated_data['state'] = '等待'
        validated_data['actno'] = 0
        validated_data['order_by'] = 1
        validated_data['addtime'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        validated_data['oper'] = self.context['request'].user.username
        try:
            instance = Plan.objects.using(equip_no).create(**validated_data)
        except ConnectionDoesNotExist:
            raise serializers.ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception:
            raise
        return instance

    class Meta:
        model = Plan
        read_only_fields = ('planid', 'state', 'actno', 'order_by', 'addtime', 'starttime', 'stoptime', 'oper')
        fields = '__all__'


class PlanUpdateSerializer(serializers.ModelSerializer):
    action = serializers.IntegerField(help_text='动作 1：下达计划  2：计划重传  3：修改车次 4：计划停止', write_only=True)
    equip_no = serializers.CharField(write_only=True, help_text='称量机台')

    def update(self, instance, validated_data):
        action = validated_data['action']
        equip_no = validated_data['equip_no']
        if settings.DEBUG:
            if action == 1:
                instance.state = '运行'
                instance.save()
            elif action == 2:
                pass
            elif action == 3:
                setno = validated_data['setno']
                actno = instance.actno if instance.actno else 0
                if not setno:
                    raise serializers.ValidationError('设定车次不可为空!')
                if setno <= actno:
                    raise serializers.ValidationError('设定车次不能小于完成车次!')
                instance.setno = setno
                instance.save()
            elif action == 4:
                instance.state = '终止'
                instance.save()
        else:
            ins = INWeighSystem(equip_no)
            if action == 1:
                ins.issue_plan({
                    "plan_no": instance.planid,
                    "recipe_no": instance.recipe,
                    "num": instance.setno,
                    "action": "1"
                    })
            elif action == 2:
                ins.reload_plan(
                    {
                        "plan_no": instance.planid,
                        "action": "1",
                    }
                )
            elif action == 3:
                setno = validated_data['setno']
                actno = instance.actno if instance.actno else 0
                if not setno:
                    raise serializers.ValidationError('设定车次不可为空!')
                if setno <= actno:
                    raise serializers.ValidationError('设定车次不能小于完成车次!')
                ins.update_trains(
                    {
                        "plan_no": instance.planid,
                        "action": "1",
                        "num": instance.setno
                    }
                )
            elif action == 4:
                ins.stop({
                            "plan_no": instance.planid,
                            "action": "1"
                        })
            else:
                raise serializers.ValidationError('action参数错误！')
        return instance

    class Meta:
        model = Plan
        fields = ('id', 'setno', 'action', 'equip_no')


class RecipePreSerializer(serializers.ModelSerializer):

    class Meta:
        model = RecipePre
        fields = '__all__'


class ReportBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportBasic
        fields = '__all__'


class ReportWeightSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportWeight
        fields = '__all__'
