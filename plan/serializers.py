from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from plan.models import ProductDayPlan, ProductClassesPlan, MaterialDemanded, ProductBatchingClassesPlan
from basics.models import GlobalCode, WorkSchedulePlan
from mes.conf import COMMON_READ_ONLY_FIELDS
from mes.base_serializer import BaseModelSerializer
from plan.uuidfield import UUidTools


class ProductClassesPlanSerializer(BaseModelSerializer):
    classes_name = serializers.CharField(source='classes_detail.classes.global_name', read_only=True)
    classes = serializers.PrimaryKeyRelatedField(queryset=GlobalCode.objects.all(),
                                                 help_text='班次id（公共代码）', write_only=True)

    class Meta:
        model = ProductClassesPlan
        exclude = ('product_day_plan', 'work_schedule_plan','plan_classes_uid')
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
        validators = [
            UniqueTogetherValidator(
                queryset=model.objects.filter(delete_flag=False),
                fields=('equip', 'product_batching', 'plan_schedule'),
                message="当天该机台已有相同的胶料计划数据，请修改后重试!"
            )
        ]

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
            for pbd_obj in instance.product_batching.batching_details.all():
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
