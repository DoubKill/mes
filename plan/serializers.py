import re
from datetime import datetime

from django.db.transaction import atomic
from rest_framework import serializers
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator, UniqueValidator

from basics.models import GlobalCode, WorkSchedulePlan, EquipCategoryAttribute, Equip, PlanSchedule
from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.utils import calculate_product_stock
from plan.models import ProductDayPlan, ProductClassesPlan, MaterialDemanded, ProductBatchingClassesPlan, \
    BatchingClassesPlan, BatchingClassesEquipPlan, SchedulingParamsSetting, SchedulingRecipeMachineSetting, \
    SchedulingEquipCapacity, SchedulingWashRule, SchedulingWashRuleDetail, SchedulingWashPlaceKeyword, \
    SchedulingWashPlaceOperaKeyword, SchedulingProductDemandedDeclare, SchedulingProductDemandedDeclareSummary, \
    SchedulingProductSafetyParams, SchedulingResult, SchedulingEquipShutDownPlan
from plan.uuidfield import UUidTools
from production.models import PlanStatus
from quality.utils import get_cur_sheet
from recipe.models import ProductBatching, ProductInfo, ProductBatchingDetail, Material
import copy


class ProductClassesPlanSerializer(BaseModelSerializer):
    classes_name = serializers.CharField(source='classes_detail.classes.global_name', read_only=True)
    classes = serializers.PrimaryKeyRelatedField(queryset=GlobalCode.objects.all(),
                                                 help_text='班次id（公共代码）', write_only=True)

    class Meta:
        model = ProductClassesPlan
        exclude = ('product_day_plan', 'work_schedule_plan', 'plan_classes_uid')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductDayPlanSerializer(BaseModelSerializer):
    """胶料日计划序列化"""
    pdp_product_classes_plan = ProductClassesPlanSerializer(many=True,
                                                            help_text="""
                                                            {"sn":1,"plan_trains":1,"classes":班次id
                                                            "time":"12.5","weight":1,"unit":1,"note":备注}
                                                            """)
    equip_no = serializers.CharField(source='equip.equip_no', read_only=True, help_text='机台编号')
    category = serializers.CharField(source='equip.category', read_only=True, help_text='设备种类属性')
    product_no = serializers.CharField(source='product_batching.stage_product_batch_no', read_only=True,
                                       help_text='胶料编码')
    batching_weight = serializers.DecimalField(source='product_batching.batching_weight', decimal_places=2,
                                               max_digits=8,
                                               read_only=True, help_text='配料重量')
    production_time_interval = serializers.DecimalField(source='product_batching.production_time_interval',
                                                        read_only=True,
                                                        help_text='配料时间', decimal_places=2, max_digits=10)
    dev_type_name = serializers.CharField(source='product_batching.dev_type.global_name', read_only=True)

    class Meta:
        model = ProductDayPlan
        fields = ('id', 'equip', 'equip_no', 'category', 'plan_schedule',
                  'product_no', 'batching_weight', 'production_time_interval', 'product_batching',
                  'pdp_product_classes_plan', 'dev_type_name')
        read_only_fields = COMMON_READ_ONLY_FIELDS
        # validators = [
        #     UniqueTogetherValidator(
        #         queryset=model.objects.filter(delete_flag=False),
        #         fields=('equip', 'product_batching', 'plan_schedule'),
        #         message="当天该机台已有相同的胶料计划数据，请修改后重试!"
        #     )
        # ]

    @atomic()
    def create(self, validated_data):
        details = validated_data.pop('pdp_product_classes_plan', None)
        # 创建胶料日计划
        instance = super().create(validated_data)
        # 创建胶料日班次班次计划和原材料需求量
        for detail in details:
            if not detail['plan_trains']:
                continue
            classes = detail.pop('classes')
            work_schedule_plan = WorkSchedulePlan.objects.filter(classes=classes,
                                                                 plan_schedule=instance.plan_schedule).first()
            if not work_schedule_plan:
                raise serializers.ValidationError('暂无该班次排班数据')
            while 1:
                plan_classes_uid = UUidTools.uuid1_hex(instance.equip.equip_no)
                if not ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).exists():
                    break
            detail['plan_classes_uid'] = plan_classes_uid
            detail['product_day_plan'] = instance
            detail['work_schedule_plan'] = work_schedule_plan
            pcp_obj = ProductClassesPlan.objects.create(**detail, created_user=self.context['request'].user)
            for pbd_obj in instance.product_batching.batching_details.filter(delete_flag=False):
                MaterialDemanded.objects.create(product_classes_plan=pcp_obj,
                                                work_schedule_plan=pcp_obj.work_schedule_plan,
                                                material=pbd_obj.material,
                                                material_demanded=pbd_obj.actual_weight * pcp_obj.plan_trains,
                                                plan_classes_uid=pcp_obj.plan_classes_uid)
        return instance


class ProductBatchingClassesPlanSerializer(BaseModelSerializer):
    classes = serializers.CharField(source='classes_detail.classes.global_name', read_only=True)

    class Meta:
        model = ProductBatchingClassesPlan
        exclude = ('product_batching_day_plan', 'classes_detail')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialDemandedSerializer(BaseModelSerializer):
    """原材料需求量序列化"""
    sn = serializers.IntegerField(source='product_classes_plan.sn', read_only=True, help_text='顺序')
    material_name = serializers.CharField(source='material.material_name', read_only=True, help_text='原材料名称')
    classes = serializers.CharField(source='work_schedule_plan.classes.global_name', read_only=True, help_text='班次')
    material_type = serializers.CharField(source='material.material_type', read_only=True, help_text='原材料类别')
    material_no = serializers.CharField(source='material.material_no', read_only=True, help_text='原材料编码')
    product_no = serializers.CharField(
        source='product_classes_plan.product_day_plan.product_batching.stage_product_batch_no', read_only=True,
        help_text='胶料编码')

    class Meta:
        model = MaterialDemanded
        fields = ('sn', 'material_name', 'classes', 'material_type', 'material_no', 'material_demanded', 'product_no')


class ProductClassesPlanManyCreateSerializer(BaseModelSerializer):
    """胶料日班次计划序列化"""

    classes_name = serializers.CharField(source='work_schedule_plan.classes.global_name', read_only=True)
    product_no = serializers.CharField(source='product_batching.stage_product_batch_no', read_only=True)
    status = serializers.SerializerMethodField(read_only=True, help_text='计划状态')
    start_time = serializers.DateTimeField(source='work_schedule_plan.start_time', read_only=True)
    end_time = serializers.DateTimeField(source='work_schedule_plan.end_time', read_only=True)
    equip_no = serializers.CharField(source='equip.equip_no', read_only=True)
    batching_type = serializers.IntegerField(source='product_batching.batching_type', default=None)

    def get_status(self, obj):
        try:
            plan_status = PlanStatus.objects.using("SFJ").filter(
                plan_classes_uid=obj.plan_classes_uid).order_by('created_date').last().status
            return plan_status
        except:
            return obj.status

    class Meta:
        model = ProductClassesPlan
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS
        extra_kwargs = {'plan_classes_uid': {'validators': []}}

    @atomic()
    def create(self, validated_data):
        plan_classes_uid = validated_data['plan_classes_uid']
        pcp_obj = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid, delete_flag=False).first()
        if not pcp_obj:
            validated_data['status'] = '已保存'
            instance = super().create(validated_data)
            # 创建计划状态
            PlanStatus.objects.create(plan_classes_uid=instance.plan_classes_uid, equip_no=instance.equip.equip_no,
                                      product_no=instance.product_batching.stage_product_batch_no,
                                      status='已保存', operation_user=self.context['request'].user.username)
            # 创建原材料需求量
            for pbd_obj in instance.product_batching.batching_details.filter(delete_flag=False):
                MaterialDemanded.objects.create(product_classes_plan=instance,
                                                work_schedule_plan=instance.work_schedule_plan,
                                                material=pbd_obj.material,
                                                material_demanded=pbd_obj.actual_weight * instance.plan_trains,
                                                plan_classes_uid=instance.plan_classes_uid)
        else:
            validated_data.pop('status', None)
            instance = super().update(pcp_obj, validated_data)
            PlanStatus.objects.filter(plan_classes_uid=instance.plan_classes_uid).update(
                equip_no=instance.equip.equip_no,
                product_no=instance.product_batching.stage_product_batch_no)
            MaterialDemanded.objects.filter(product_classes_plan=instance).update(delete_flag=True)
            for pbd_obj in instance.product_batching.batching_details.filter(delete_flag=False):
                MaterialDemanded.objects.create(product_classes_plan=instance,
                                                work_schedule_plan=instance.work_schedule_plan,
                                                material=pbd_obj.material,
                                                material_demanded=pbd_obj.actual_weight * instance.plan_trains,
                                                plan_classes_uid=instance.plan_classes_uid)
        return instance


class ProductBatchingSerializer(BaseModelSerializer):
    """胶料配料标准同步"""
    delete_flag = serializers.BooleanField(write_only=True)
    created_date = serializers.DateTimeField(write_only=True)
    factory__global_no = serializers.CharField(write_only=True, required=False)
    site__global_no = serializers.CharField(write_only=True, required=False)
    product_info__product_no = serializers.CharField(write_only=True, required=False)
    dev_type__category_no = serializers.CharField(write_only=True, required=False)
    stage__global_no = serializers.CharField(write_only=True, required=False)
    equip__equip_no = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        factory1 = attrs.pop('factory__global_no', None)
        site1 = attrs.pop('site__global_no', None)
        product_info1 = attrs.pop('product_info__product_no', None)
        dev_type1 = attrs.pop('dev_type__category_no', None)
        stage1 = attrs.pop('stage__global_no', None)
        equip1 = attrs.pop('equip__equip_no', None)
        try:
            if factory1:
                factory = GlobalCode.objects.get(global_no=factory1)
            else:
                factory = None
            if site1:
                site = GlobalCode.objects.get(global_no=site1)
            else:
                site = None
            if product_info1:
                product_info = ProductInfo.objects.get(product_no=product_info1)
            else:
                product_info = None
            if dev_type1:
                dev_type = EquipCategoryAttribute.objects.get(category_no=dev_type1)
            else:
                dev_type = None
            if stage1:
                stage = GlobalCode.objects.get(global_no=stage1)
            else:
                stage = None
            if equip1:
                equip = Equip.objects.get(equip_no=equip1)
            else:
                equip = None
        except GlobalCode.DoesNotExist:
            raise serializers.ValidationError(
                '工厂编号{0}或者SITE编号{1}或者段次{2}不存在'.format(factory1, site1, stage1))
        except ProductInfo.DoesNotExist:
            raise serializers.ValidationError('胶料工艺信息{}不存在'.format(product_info1))
        except EquipCategoryAttribute.DoesNotExist:
            raise serializers.ValidationError('设备种类属性{}不存在'.format(dev_type1))
        except Equip.DoesNotExist:
            raise serializers.ValidationError('设备{}不存在'.format(equip1))
        attrs['factory'] = factory
        attrs['site'] = site
        attrs['product_info'] = product_info
        attrs['dev_type'] = dev_type
        attrs['stage'] = stage
        attrs['equip'] = equip
        return attrs

    @atomic()
    def create(self, validated_data):
        stage_product_batch_no = validated_data['stage_product_batch_no']
        equip = validated_data['equip']
        batching_type = validated_data['batching_type']
        instance = ProductBatching.objects.exclude(used_type=6).filter(stage_product_batch_no=stage_product_batch_no,
                                                                       equip=equip,
                                                                       batching_type=batching_type)
        if instance:
            instance.update(**validated_data)
        else:
            instance = super().create(validated_data)
            ProductBatching.objects.filter(id=instance.id).update(batching_weight=validated_data['batching_weight'])
        return validated_data

    class Meta:
        model = ProductBatching
        fields = (
            'factory__global_no', 'site__global_no', 'product_info__product_no', 'precept', 'stage_product_batch_no',
            'dev_type__category_no', 'stage__global_no', 'versions', 'used_type', 'batching_weight',
            'manual_material_weight', 'auto_material_weight', 'volume', 'production_time_interval', 'equip__equip_no',
            'batching_type', 'delete_flag',
            'created_date')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductBatchingDetailSerializer(BaseModelSerializer):
    """胶料配料标准同步"""
    delete_flag = serializers.BooleanField(write_only=True)
    created_date = serializers.DateTimeField(write_only=True)
    product_batching__stage_product_batch_no = serializers.CharField(write_only=True)
    material__material_no = serializers.CharField(write_only=True)
    product_batching__equip__equip_no = serializers.CharField(write_only=True)
    product_batching__used_type = serializers.CharField(write_only=True)

    def validate(self, attrs):
        product_batching1 = attrs.pop('product_batching__stage_product_batch_no')
        material1 = attrs.pop('material__material_no')
        equip_no1 = attrs.pop('product_batching__equip__equip_no')
        used_type1 = attrs.pop('product_batching__used_type')
        try:
            material = Material.objects.get(material_no=material1)
        except Material.DoesNotExist:
            raise serializers.ValidationError('原材料信息{}不存在'.format(material1))
        pb_obj = ProductBatching.objects.filter(
            stage_product_batch_no=product_batching1,
            equip__equip_no=equip_no1,
            batching_type=1,
            used_type=used_type1
        ).first()
        if not pb_obj:
            raise serializers.ValidationError('配方|胶料配料标准{}不存在'.format(product_batching1))
        attrs['product_batching'] = pb_obj
        attrs['material'] = material
        return attrs

    @atomic()
    def create(self, validated_data):
        if validated_data['delete_flag']:
            ProductBatchingDetail.objects.filter(product_batching=validated_data['product_batching'],
                                                 material=validated_data['material']
                                                 ).update(delete_flag=True)
        else:
            # instance = ProductBatchingDetail.objects.filter(product_batching=validated_data['product_batching'],
            #                                                 material=validated_data['material'],
            #                                                 delete_flag=validated_data['delete_flag'])
            # if instance:
            #     instance.update(**validated_data)
            # else:
            super().create(validated_data)
        return validated_data

    class Meta:
        model = ProductBatchingDetail
        fields = (
            'product_batching__stage_product_batch_no', 'sn', 'material__material_no', 'actual_weight',
            'standard_error',
            'auto_flag', 'type', 'delete_flag',
            'created_date', 'product_batching__equip__equip_no', 'product_batching__used_type')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductDayPlansySerializer(BaseModelSerializer):
    """胶料日计划表同步"""
    delete_flag = serializers.BooleanField(write_only=True)
    created_date = serializers.DateTimeField(write_only=True)
    equip__equip_no = serializers.CharField(write_only=True)
    product_batching__stage_product_batch_no = serializers.CharField(write_only=True)
    plan_schedule__plan_schedule_no = serializers.CharField(write_only=True)

    def validate(self, attrs):
        equip1 = attrs.pop('equip__equip_no')
        product_batching1 = attrs.pop('product_batching__stage_product_batch_no')
        plan_schedule1 = attrs.pop('plan_schedule__plan_schedule_no')
        try:
            equip = Equip.objects.get(equip_no=equip1)
            plan_schedule = PlanSchedule.objects.get(plan_schedule_no=plan_schedule1)
        except Equip.DoesNotExist:
            raise serializers.ValidationError('设备{}不存在'.format(equip1))
        except PlanSchedule.DoesNotExist:
            raise serializers.ValidationError('排班管理{}不存在'.format(plan_schedule1))
        pb_obj = ProductBatching.objects.filter(stage_product_batch_no=product_batching1, batching_type=2).last()
        if not pb_obj:
            pb_obj = ProductBatching.objects.filter(stage_product_batch_no=product_batching1, batching_type=1).last()
        if not pb_obj:
            raise serializers.ValidationError('日计划|胶料配料标准{}不存在'.format(product_batching1))
        attrs['product_batching'] = pb_obj
        attrs['equip'] = equip
        attrs['plan_schedule'] = plan_schedule
        return attrs

    @atomic()
    def create(self, validated_data):
        filter_dict = copy.deepcopy(validated_data)
        filter_dict.pop('created_date')
        instance = ProductDayPlan.objects.filter(equip=validated_data['equip'],
                                                 product_batching=validated_data['product_batching'],
                                                 plan_schedule=validated_data['plan_schedule'])
        if instance:
            instance.update(**validated_data)
        else:
            super().create(validated_data)
        return validated_data

    class Meta:
        model = ProductDayPlan
        fields = (
            'equip__equip_no', 'product_batching__stage_product_batch_no', 'plan_schedule__plan_schedule_no',
            'delete_flag',
            'created_date')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductClassesPlansySerializer(BaseModelSerializer):
    """胶料日计划表同步"""
    delete_flag = serializers.BooleanField(write_only=True)
    created_date = serializers.DateTimeField(write_only=True)
    work_schedule_plan__work_schedule_plan_no = serializers.CharField(write_only=True)
    equip__equip_no = serializers.CharField(write_only=True, required=False)
    product_batching__stage_product_batch_no = serializers.CharField(write_only=True, required=False)
    # product_day_plan__equip__equip_no = serializers.CharField(write_only=True)
    # product_day_plan__plan_schedule__plan_schedule_no = serializers.CharField(write_only=True)
    # product_day_plan__product_batching__stage_product_batch_no = serializers.CharField(write_only=True)
    status = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        work_schedule_plan1 = attrs.pop('work_schedule_plan__work_schedule_plan_no', None)
        equip_no = attrs.pop('equip__equip_no', None)
        product_batching_no = attrs.pop('product_batching__stage_product_batch_no', None)
        attrs.pop('product_day_plan__plan_schedule__plan_schedule_no', None)
        attrs.pop('product_day_plan__equip__equip_no', None)
        attrs.pop('product_day_plan__product_batching__stage_product_batch_no', None)
        try:
            equip = Equip.objects.get(equip_no=equip_no)
            work_schedule_plan = WorkSchedulePlan.objects.get(work_schedule_plan_no=work_schedule_plan1)
        except WorkSchedulePlan.DoesNotExist:
            raise serializers.ValidationError('排班详情{}不存在'.format(work_schedule_plan1))
        except Equip.DoesNotExist:
            raise serializers.ValidationError('设备{}不存在'.format(equip_no))
        pb_obj = ProductBatching.objects.exclude(used_type=6).filter(stage_product_batch_no=product_batching_no,
                                                                     batching_type=1,
                                                                     equip=equip).first()
        if not pb_obj:
            raise serializers.ValidationError('日班次计划|胶料配料标准{}不存在'.format(product_batching_no))
        attrs['product_batching'] = pb_obj
        attrs['equip'] = equip
        attrs['work_schedule_plan'] = work_schedule_plan
        return attrs

    @atomic()
    def create(self, validated_data):
        plan_classes_uid = validated_data['plan_classes_uid']
        instance = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid)
        if instance:
            instance.update(**validated_data)
        else:
            super().create(validated_data)
        return validated_data

    class Meta:
        model = ProductClassesPlan
        fields = ('sn', 'plan_trains', 'time', 'weight', 'unit', 'work_schedule_plan__work_schedule_plan_no',
                  'plan_classes_uid', 'note',
                  'equip__equip_no', 'product_batching__stage_product_batch_no',
                  'status', 'delete_flag', 'created_date')
        read_only_fields = COMMON_READ_ONLY_FIELDS
        extra_kwargs = {'plan_classes_uid': {'validators': []}}


class MaterialsySerializer(BaseModelSerializer):
    """原材料表同步"""
    material_type__global_no = serializers.CharField(write_only=True, required=False)
    package_unit__global_no = serializers.CharField(write_only=True, required=False)
    material_no = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        material_type1 = attrs.pop('material_type__global_no', None)
        package_unit1 = attrs.pop('package_unit__global_no', None)
        try:
            material_type = GlobalCode.objects.get(global_no=material_type1)
            if package_unit1:
                package_unit = GlobalCode.objects.get(global_no=package_unit1)
            else:
                package_unit = None
        except GlobalCode.DoesNotExist:
            raise serializers.ValidationError('原材料类别{0}或者包装单位{1}不存在'.format(material_type1, package_unit1))
        attrs['material_type'] = material_type
        attrs['package_unit'] = package_unit
        return attrs

    @atomic()
    def create(self, validated_data):
        instance = Material.objects.filter(material_no=validated_data['material_no'])

        if instance:
            instance.update(**validated_data)
        else:
            super().create(validated_data)
        return validated_data

    class Meta:
        model = Material
        fields = (
            'material_no', 'material_name', 'for_short', 'material_type__global_no', 'package_unit__global_no',
            'use_flag')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class BatchingClassesPlanSerializer(serializers.ModelSerializer):
    day_time = serializers.ReadOnlyField(source='work_schedule_plan.plan_schedule.day_time', default='')
    classes_name = serializers.ReadOnlyField(source='work_schedule_plan.classes.global_name', default='')
    category_name = serializers.ReadOnlyField(
        source='weigh_cnt_type.product_batching.dev_type.category_name', default='')
    stage_product_batch_no = serializers.ReadOnlyField(
        source='weigh_cnt_type.product_batching.stage_product_batch_no', default='')
    send_user = serializers.ReadOnlyField(source='send_user.username', default='')
    weigh_batching_used_type = serializers.ReadOnlyField(source='weigh_cnt_type.product_batching.used_type')
    weigh_type = serializers.ReadOnlyField(source='weigh_cnt_type.weigh_type')
    package_type = serializers.ReadOnlyField(source='weigh_cnt_type.package_type')
    undistributed_package = serializers.ReadOnlyField()
    weight_batch_no = serializers.ReadOnlyField(source='weigh_cnt_type.name')

    class Meta:
        model = BatchingClassesPlan
        fields = '__all__'


class BatchingClassesEquipPlanSerializer(serializers.ModelSerializer):
    equip_no = serializers.ReadOnlyField(source='equip.equip_no')
    equip_name = serializers.ReadOnlyField(source='equip.equip_name')
    send_username = serializers.ReadOnlyField(source='send_user.username')

    def create(self, validated_data):
        validated_data['send_user'] = self.context['request'].user
        validated_data['send_time'] = datetime.now()
        equip_plan = BatchingClassesEquipPlan.objects.filter(
            batching_class_plan=validated_data['batching_class_plan'],
            equip=validated_data['equip']).first()
        # 有相同的机台计划则累加
        if equip_plan:
            equip_plan.packages += validated_data['packages']
            equip_plan.save()
            return equip_plan
        batching_class_plan = validated_data['batching_class_plan']
        batching_class_plan.status = 2
        batching_class_plan.save()
        return super().create(validated_data)

    class Meta:
        model = BatchingClassesEquipPlan
        fields = '__all__'
        read_only_fields = ('send_user', 'send_time', 'package_changed', 'status')


class IssueBatchingClassesPlanSerializer(serializers.ModelSerializer):
    equip = serializers.PrimaryKeyRelatedField(queryset=Equip.objects.filter(use_flag=True,
                                                                             delete_flag=False,
                                                                             category__equip_type__global_name='称量设备'))

    class Meta:
        model = BatchingClassesPlan
        fields = ('equip',)

    def update(self, instance, validated_data):
        if instance.status == 1:
            instance.status = 2
        instance.package_changed = False
        instance.send_time = timezone.now()
        return super().update(instance, validated_data)


class PlantImportSerializer(BaseModelSerializer):
    excel_file = serializers.FileField(write_only=True)

    def validate(self, attrs):
        excel_file = attrs.pop('excel_file')
        current_sheet = get_cur_sheet(excel_file)
        file_name = excel_file.name.strip()
        try:
            factory_date = file_name[:10]
            datetime.strptime(factory_date, "%Y-%m-%d")
        except Exception:
            raise ValidationError('文件名错误，请以日期格式开头！')
        classes_plan_list = []
        for j in range(2):
            i = 0
            while 1:
                raw_index = j * 25 + 1
                col_index = i * 4 + 1
                if col_index >= 33:
                    break
                try:
                    equip_data = current_sheet.cell(raw_index, col_index).value.strip()
                    if not equip_data:
                        break
                    ret = re.search(r'Z\d+', equip_data)
                    equip_no = ret.group()
                    if len(equip_no) < 3:
                        equip_no = 'Z' + '0{}'.format(equip_no[-1])
                except IndexError:
                    break
                except Exception:
                    raise serializers.ValidationError('机台格式错误')
                tmp_class = None
                for rowNum in range(j * 25 + 3, 25 * (j + 1)):
                    value = current_sheet.row_values(rowNum)[i * 4 + 1:(i + 1) * 4 + 1]
                    classes = current_sheet.cell(rowNum, 0).value
                    if classes:
                        tmp_class = classes
                    else:
                        classes = tmp_class
                    product_no = value[0].strip()
                    plan_trains = value[1]
                    note = value[3].strip()
                    if not all([classes, product_no, plan_trains]):
                        continue
                    try:
                        plan_trains = int(plan_trains)
                    except ValueError:
                        raise serializers.ValidationError('机台：{}， 胶料规格:{}，车次信息错误，请修改后重试！'.format(equip_no, value[0]))
                    except Exception:
                        raise
                    product_batching = ProductBatching.objects.filter(used_type=4,
                                                                      stage_product_batch_no=product_no,
                                                                      batching_type=2
                                                                      ).first()
                    work_schedule_plan = WorkSchedulePlan.objects.filter(classes__global_name=classes,
                                                                         plan_schedule__day_time=factory_date
                                                                         ).first()
                    equip = Equip.objects.filter(equip_no=equip_no).first()
                    if not equip:
                        raise serializers.ValidationError('机台：{}未找到，请修改后重试！'.format(equip_no))
                    if not product_batching:
                        raise serializers.ValidationError('机台：{}，胶料规格:{}未找到，请修改后重试！'.format(equip_no, value[0]))
                    if not work_schedule_plan:
                        raise serializers.ValidationError('{}日期未找到{}排班数据未找到，请修改后重试！'.format(factory_date, classes))
                    if product_batching.dev_type != equip.category:
                        raise serializers.ValidationError('机台{}所属机型与胶料规格{}机型不一致，请修改后重试！'.format(equip_no, product_no))
                    classes_plan_data = {
                        "sn": 0,
                        "plan_trains": plan_trains,
                        "unit": "车",
                        "work_schedule_plan": work_schedule_plan,
                        "note": note,
                        "equip": equip,
                        "product_batching": product_batching,
                        "status": "已保存"}
                    classes_plan_list.append(classes_plan_data)
                i += 1
            j += 1
        attrs['classes_plan_list'] = classes_plan_list
        return attrs

    @atomic()
    def create(self, validated_data):
        classes_plan_list = validated_data['classes_plan_list']
        for item in classes_plan_list:
            while 1:
                plan_classes_uid = UUidTools.uuid1_hex(item['equip'].equip_no)
                if not ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).exists():
                    break
            item['plan_classes_uid'] = plan_classes_uid
            pdp_obj = ProductDayPlan.objects.filter(equip_id=item['equip'],
                                                    product_batching_id=item['product_batching'],
                                                    plan_schedule=item['work_schedule_plan'].plan_schedule,
                                                    delete_flag=False).first()
            if pdp_obj:
                item['product_day_plan_id'] = pdp_obj.id
            else:
                item['product_day_plan_id'] = ProductDayPlan.objects.create(
                    equip=item['equip'],
                    product_batching=item['product_batching'],
                    plan_schedule=item['work_schedule_plan'].plan_schedule).id
            ProductClassesPlan.objects.create(**item)
        return validated_data

    class Meta:
        model = ProductClassesPlan
        fields = ('excel_file', )


class SchedulingParamsSettingSerializer(serializers.ModelSerializer):

    class Meta:
        model = SchedulingParamsSetting
        fields = '__all__'


class SchedulingRecipeMachineSettingSerializer(BaseModelSerializer):
    mixing_vice_machine = serializers.ListField(write_only=True, required=False, allow_empty=True)
    final_vice_machine = serializers.ListField(write_only=True, required=False, allow_empty=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.mixing_vice_machine:
            data['mixing_vice_machine'] = instance.mixing_vice_machine.split('/')
        else:
            data['mixing_vice_machine'] = []
        if instance.final_vice_machine:
            data['final_vice_machine'] = instance.final_vice_machine.split('/')
        else:
            data['final_vice_machine'] = []
        return data

    def validate(self, attrs):
        attrs['mixing_vice_machine'] = '/'.join(attrs.get('mixing_vice_machine', ''))
        attrs['final_vice_machine'] = '/'.join(attrs.get('final_vice_machine', ''))
        return attrs

    class Meta:
        model = SchedulingRecipeMachineSetting
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS
        validators = [UniqueTogetherValidator(
            queryset=SchedulingRecipeMachineSetting.objects.filter(delete_flag=False).all(),
            fields=('rubber_type', 'product_no', 'stage'), message='该数据已存在')]


class RecipeMachineWeightSerializer(serializers.ModelSerializer):
    equip_no = serializers.CharField(source='equip__equip_no')
    devoted_weight = serializers.SerializerMethodField()
    resting_period = serializers.SerializerMethodField()

    def get_resting_period(self, obj):
        return 0

    def get_devoted_weight(self, obj):
        stages = list(GlobalCode.objects.filter(global_type__type_name='胶料段次').values_list('global_name', flat=True))
        c_pb = ProductBatchingDetail.objects.using('SFJ').filter(
            product_batching=obj['id'],
            delete_flag=False,
            material__material_type__global_name__in=stages).first()
        if c_pb:
            return c_pb.actual_weight
        else:
            return 0

    class Meta:
        model = ProductBatching
        fields = ('id', 'equip_no', 'stage_product_batch_no', 'batching_weight', 'devoted_weight', 'resting_period')


class SchedulingEquipCapacitySerializer(BaseModelSerializer):

    class Meta:
        model = SchedulingEquipCapacity
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class SchedulingWashRuleDetailSerializer(BaseModelSerializer):

    class Meta:
        model = SchedulingWashRuleDetail
        exclude = ('wash_rule', )
        read_only_fields = COMMON_READ_ONLY_FIELDS


class SchedulingWashRuleSerializer(BaseModelSerializer):
    rule_details = SchedulingWashRuleDetailSerializer(many=True, help_text="""[{"ordering": 1, "process": "处理", "spec_params": "处理参数（规格/单位）", "quantity_params": "（车数/数量）"}]""")
    rule_no = serializers.CharField(max_length=64, validators=[UniqueValidator(
        queryset=SchedulingWashRule.objects.all(), message='该洗车规则编号已存在！')])

    @atomic()
    def create(self, validated_data):
        rule_details = validated_data.pop('rule_details', [])
        instance = super().create(validated_data)
        for item in rule_details:
            item['wash_rule'] = instance
            item['created_user'] = self.context['request'].user
            SchedulingWashRuleDetail.objects.create(**item)
        return instance

    @atomic()
    def update(self, instance, validated_data):
        rule_details = validated_data.pop('rule_details', [])
        instance = super().update(instance, validated_data)
        if rule_details:
            instance.rule_details.all().delete()
            for item in rule_details:
                item['wash_rule'] = instance
                item['created_user'] = self.context['request'].user
                SchedulingWashRuleDetail.objects.create(**item)
        return instance

    class Meta:
        model = SchedulingWashRule
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class SchedulingWashPlaceKeywordSerializer(BaseModelSerializer):

    class Meta:
        model = SchedulingWashPlaceKeyword
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class SchedulingWashPlaceOperaKeywordSerializer(BaseModelSerializer):

    class Meta:
        model = SchedulingWashPlaceOperaKeyword
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class SchedulingProductDemandedDeclareSerializer(BaseModelSerializer):
    safety_stock = serializers.SerializerMethodField(default=0)

    def get_safety_stock(self, obj):
        p = SchedulingProductSafetyParams.objects.filter(
            product_no=obj.product_no).first()
        if p:
            return p.safety_stock
        else:
            return 0

    @atomic()
    def create(self, validated_data):
        validated_data['factory_date'] = datetime.now().date()
        validated_data['order_no'] = self.context['order_no']
        instance = super().create(validated_data)
        s = SchedulingProductDemandedDeclareSummary.objects.filter(
            factory_date=instance.factory_date,
            product_no=instance.product_no).first()
        current_stock = round((calculate_product_stock(instance.product_no, 'FM') +
                               calculate_product_stock(instance.product_no, 'RFM')) / 1000, 2)
        if not s:
            c = SchedulingProductDemandedDeclareSummary.objects.filter(
                factory_date=instance.factory_date).count()
            sn = c + 1
            SchedulingProductDemandedDeclareSummary.objects.create(
                sn=sn,
                factory_date=instance.factory_date,
                product_no=instance.product_no,
                plan_weight=instance.today_demanded,
                workshop_weight=instance.current_stock,
                current_stock=current_stock
            )
        else:
            s.plan_weight += instance.today_demanded
            s.workshop_weight += instance.current_stock
            s.save()
        return instance

    @atomic()
    def update(self, instance, validated_data):

        s = SchedulingProductDemandedDeclareSummary.objects.filter(
            factory_date=instance.factory_date,
            product_no=instance.product_no).first()
        if s:
            if 'today_demanded' in validated_data:
                s.plan_weight -= instance.today_demanded
                s.plan_weight += validated_data['today_demanded']
            if 'current_stock' in validated_data:
                s.workshop_weight -= instance.current_stock
                s.workshop_weight += validated_data['current_stock']
            s.save()
        return super().update(instance, validated_data)

    class Meta:
        model = SchedulingProductDemandedDeclare
        fields = '__all__'
        read_only_fields = ('order_no', 'factory_date')
        # read_only_fields = COMMON_READ_ONLY_FIELDS
        # extra_kwargs = {'factory_date': {'read_only': False}}


class SchedulingProductSafetyParamsSerializer(BaseModelSerializer):

    class Meta:
        model = SchedulingProductSafetyParams
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class SchedulingProductDemandedDeclareSummarySerializer(serializers.ModelSerializer):
    demanded_weight = serializers.SerializerMethodField(default=0, read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        available_time = data['available_time']
        data['available_time'] = round(available_time * 24, 1)
        return data

    def get_demanded_weight(self, obj):
        return obj.plan_weight - obj.workshop_weight - obj.current_stock

    def create(self, validated_data):
        validated_data['factory_date'] = datetime.now().date()
        c = SchedulingProductDemandedDeclareSummary.objects.filter(
            factory_date=validated_data['factory_date']).count()
        validated_data['sn'] = c + 1
        validated_data['current_stock'] = round((calculate_product_stock(validated_data['factory_date'], validated_data['product_no'], 'FM') +
                                                 calculate_product_stock(validated_data['factory_date'], validated_data['product_no'], 'RFM')) / 1000, 2)
        return super(SchedulingProductDemandedDeclareSummarySerializer, self).create(validated_data)

    class Meta:
        model = SchedulingProductDemandedDeclareSummary
        fields = '__all__'
        read_only_fields = ('sn', 'factory_date')


class SchedulingResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchedulingResult
        fields = '__all__'


class SchedulingEquipShutDownPlanSerializer(BaseModelSerializer):

    def create(self, validated_data):
        validated_data['factory_date'] = datetime.now().date()
        return super().create(validated_data)

    class Meta:
        model = SchedulingEquipShutDownPlan
        fields = '__all__'
        read_only_fields = ('factory_date',)
