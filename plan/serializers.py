from django.db.transaction import atomic
from rest_framework import serializers

from basics.models import GlobalCode, WorkSchedulePlan, EquipCategoryAttribute, Equip, PlanSchedule
from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.models import ProductDayPlan, ProductClassesPlan, MaterialDemanded, ProductBatchingClassesPlan
from plan.uuidfield import UUidTools
from production.models import PlanStatus
from recipe.models import ProductBatching, ProductInfo, ProductBatchingDetail, Material


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
            detail['plan_classes_uid'] = UUidTools.uuid1_hex(instance.equip.equip_no)
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

    def get_status(self, obj):
        plan_status = PlanStatus.objects.filter(plan_classes_uid=obj.plan_classes_uid).order_by('created_date').last()
        if plan_status:
            return plan_status.status
        else:
            return None

    class Meta:
        model = ProductClassesPlan
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS

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
    factory__global_no = serializers.CharField(write_only=True)
    site__global_no = serializers.CharField(write_only=True)
    product_info__product_no = serializers.CharField(write_only=True)
    dev_type__category_no = serializers.CharField(write_only=True)
    stage__global_no = serializers.CharField(write_only=True)
    equip__equip_no = serializers.CharField(write_only=True)

    def validate(self, attrs):
        factory1 = attrs.pop('factory__global_no')
        site1 = attrs.pop('site__global_no')
        product_info1 = attrs.pop('product_info__product_no')
        dev_type1 = attrs.pop('dev_type__category_no')
        stage1 = attrs.pop('stage__global_no')
        equip1 = attrs.pop('equip__equip_no')
        try:
            factory = GlobalCode.objects.get(global_no=factory1)
            site = GlobalCode.objects.get(global_no=site1)
            product_info = ProductInfo.objects.get(product_no=product_info1)
            dev_type = EquipCategoryAttribute.objects.get(category_no=dev_type1)
            stage = GlobalCode.objects.get(global_no=stage1)
            equip = Equip.objects.get(equip_no=equip1)
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
        instance = ProductBatching.objects.filter(stage_product_batch_no=stage_product_batch_no, equip=equip)
        if instance:
            instance.update(**validated_data)
        else:
            super().create(validated_data)
        return validated_data

    class Meta:
        model = ProductBatching
        fields = (
            'factory__global_no', 'site__global_no', 'product_info__product_no', 'precept', 'stage_product_batch_no',
            'dev_type__category_no', 'stage__global_no', 'versions', 'used_type', 'batching_weight',
            'manual_material_weight', 'auto_material_weight', 'volume', 'production_time_interval', 'equip__equip_no',
            'batching_type')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductBatchingDetailSerializer(BaseModelSerializer):
    """胶料配料标准同步"""
    product_batching__stage_product_batch_no = serializers.CharField(write_only=True)
    material__material_no = serializers.CharField(write_only=True)

    def validate(self, attrs):
        product_batching1 = attrs.pop('product_batching__stage_product_batch_no')
        material1 = attrs.pop('material__material_no')
        try:
            material = Material.objects.get(material_no=material1)
        except Material.DoesNotExist:
            raise serializers.ValidationError('原材料信息{}不存在'.format(material1))
        pb_obj = ProductBatching.objects.filter(stage_product_batch_no=product_batching1).first()
        if not pb_obj:
            raise serializers.ValidationError('胶料配料标准{}不存在'.format(product_batching1))
        attrs['product_batching'] = pb_obj
        attrs['material'] = material
        return attrs

    @atomic()
    def create(self, validated_data):
        instance = ProductBatchingDetail.objects.filter(**validated_data)
        if instance:
            instance.update(**validated_data)
        else:
            super().create(validated_data)
        return validated_data

    class Meta:
        model = ProductBatchingDetail
        fields = (
            'product_batching__stage_product_batch_no', 'sn', 'material__material_no', 'actual_weight',
            'standard_error',
            'auto_flag', 'type')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductDayPlansySerializer(BaseModelSerializer):
    """胶料日计划表同步"""
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
        pb_obj = ProductBatching.objects.filter(stage_product_batch_no=product_batching1).first()
        if not pb_obj:
            raise serializers.ValidationError('胶料配料标准{}不存在'.format(product_batching1))
        attrs['product_batching'] = pb_obj
        attrs['equip'] = equip
        attrs['plan_schedule'] = plan_schedule
        return attrs

    @atomic()
    def create(self, validated_data):
        instance = ProductDayPlan.objects.filter(**validated_data)
        if instance:
            instance.update(**validated_data)
        else:
            super().create(validated_data)
        return validated_data

    class Meta:
        model = ProductDayPlan
        fields = ('equip__equip_no', 'product_batching__stage_product_batch_no', 'plan_schedule__plan_schedule_no')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductClassesPlansySerializer(BaseModelSerializer):
    """胶料日计划表同步"""
    work_schedule_plan__work_schedule_plan_no = serializers.CharField(write_only=True)
    equip__equip_no = serializers.CharField(write_only=True)
    product_batching__stage_product_batch_no = serializers.CharField(write_only=True)
    product_day_plan__equip__equip_no = serializers.CharField(write_only=True)
    product_day_plan__plan_schedule__plan_schedule_no = serializers.CharField(write_only=True)
    product_day_plan__product_batching__stage_product_batch_no = serializers.CharField(write_only=True)

    def validate(self, attrs):
        work_schedule_plan1 = attrs.pop('work_schedule_plan__work_schedule_plan_no', None)
        equip1 = attrs.pop('equip__equip_no', None)
        product_batching1 = attrs.pop('product_batching__stage_product_batch_no', None)
        # 上辅机里work_schedule_plan1和equip1可能为空
        if product_batching1 == '0':
            attrs['product_batching'] = None
        if equip1 == '0':
            attrs['equip'] = None
        if product_batching1 != '0' and equip1 != '0':
            try:
                equip = Equip.objects.get(equip_no=equip1)
            except Equip.DoesNotExist:
                raise serializers.ValidationError('设备{}不存在'.format(equip1))

            pb_obj = ProductBatching.objects.filter(stage_product_batch_no=product_batching1).first()
            if not pb_obj:
                raise serializers.ValidationError('胶料配料标准{}不存在'.format(product_batching1))
            attrs['product_batching'] = pb_obj
            attrs['equip'] = equip

        try:
            work_schedule_plan = WorkSchedulePlan.objects.get(work_schedule_plan_no=work_schedule_plan1)
        except WorkSchedulePlan.DoesNotExist:
            raise serializers.ValidationError('排班详情{}不存在'.format(work_schedule_plan1))
        attrs['work_schedule_plan'] = work_schedule_plan

        pcp_plan_schedule = attrs.pop('product_day_plan__plan_schedule__plan_schedule_no')
        pcp_equip = attrs.pop('product_day_plan__equip__equip_no')
        pcp_product_batching = attrs.pop('product_day_plan__product_batching__stage_product_batch_no')

        try:
            p_equip = Equip.objects.get(equip_no=pcp_equip)
            p_plan_schedule = PlanSchedule.objects.get(plan_schedule_no=pcp_plan_schedule)
        except Equip.DoesNotExist:
            raise serializers.ValidationError('设备{}不存在'.format(pcp_equip))
        except PlanSchedule.DoesNotExist:
            raise serializers.ValidationError('排班管理{}不存在'.format(pcp_plan_schedule))
        p_pb_obj = ProductBatching.objects.filter(stage_product_batch_no=pcp_product_batching).first()
        if not p_pb_obj:
            raise serializers.ValidationError('胶料配料标准{}不存在'.format(pcp_product_batching))
        pdp_obj = ProductDayPlan.objects.filter(equip=p_equip, plan_schedule=p_plan_schedule,
                                                product_batching=p_pb_obj).first()
        attrs['product_day_plan'] = pdp_obj
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
                  'status',
                  'product_day_plan__equip__equip_no', 'product_day_plan__product_batching__stage_product_batch_no',
                  'product_day_plan__plan_schedule__plan_schedule_no')
        read_only_fields = COMMON_READ_ONLY_FIELDS
