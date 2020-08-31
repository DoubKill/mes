import json

from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from mes.sync import BaseInterface
from plan.models import ProductDayPlan, ProductClassesPlan, MaterialDemanded, ProductBatchingDayPlan, \
    ProductBatchingClassesPlan, MaterialRequisitionClasses
from basics.models import PlanSchedule, WorkSchedule, ClassesDetail, GlobalCode, WorkSchedulePlan
from mes.conf import COMMON_READ_ONLY_FIELDS
from mes.base_serializer import BaseModelSerializer
from plan.uuidfield import UUidTools
from datetime import datetime
import requests


class ProductClassesPlanSerializer(BaseModelSerializer):
    classes_name = serializers.CharField(source='classes_detail.classes.global_name', read_only=True)
    classes = serializers.PrimaryKeyRelatedField(queryset=GlobalCode.objects.all(),
                                                 help_text='班次id（公共代码）', write_only=True)

    class Meta:
        model = ProductClassesPlan
        exclude = ('product_day_plan', 'work_schedule_plan')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductDayPlanSerializer(BaseModelSerializer):
    """胶料日计划序列化"""
    pdp_product_classes_plan = ProductClassesPlanSerializer(many=True,
                                                            help_text="""
                                                            {"sn":1,"plan_trains":1,"classes":班次id
                                                            "time":"12.5","weight":1,"unit":1,"note":备注}
                                                            """)
    # plan_date = serializers.DateField(help_text="计划日期， 格式：2020-07-31", write_only=True)
    # work_schedule = serializers.PrimaryKeyRelatedField(queryset=WorkSchedule.objects.all(),
    #                                                    help_text='倒班管理id', write_only=True)
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
            classes = detail.pop('classes')
            work_schedule_plan = WorkSchedulePlan.objects.filter(classes=classes,
                                                                 plan_schedule=instance.plan_schedule).first()
            if not work_schedule_plan:
                raise serializers.ValidationError('暂无该班次排班数据')
            detail['plan_classes_uid'] = UUidTools.uuid1_hex()
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

    @atomic()
    def update(self, instance, validated_data):
        pass


class ProductBatchingClassesPlanSerializer(BaseModelSerializer):
    classes = serializers.CharField(source='classes_detail.classes.global_name', read_only=True)

    class Meta:
        model = ProductBatchingClassesPlan
        exclude = ('product_batching_day_plan', 'classes_detail')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductBatchingDayPlanSerializer(BaseModelSerializer):
    """配料小料日计划序列化"""

    pdp_product_batching_classes_plan = ProductBatchingClassesPlanSerializer(many=True,
                                                                             help_text='{"sn":1,"bags_qty":1,"unit":"1"}')
    plan_date = serializers.DateField(help_text="2020-07-31", write_only=True)
    plan_date_time = serializers.DateField(source='plan_schedule.day_time', read_only=True)
    equip_no = serializers.CharField(source='equip.equip_no', read_only=True, help_text='设备编号')
    catagory_name = serializers.CharField(source='equip.category.equip_type', read_only=True, help_text='设备种类属性')
    product_no = serializers.CharField(source='product_batching.stage_product_batch_no', read_only=True,
                                       help_text='胶料编码')
    manual_material_weight = serializers.DecimalField(source='product_batching.manual_material_weight',
                                                      decimal_places=2,
                                                      max_digits=8,
                                                      read_only=True, help_text='配料小料重量')

    class Meta:
        model = ProductBatchingDayPlan
        fields = ('id', 'equip_no', 'plan_date_time', 'catagory_name', 'product_no', 'manual_material_weight',
                  'equip', 'product_batching', 'plan_date', 'bags_total_qty', 'product_day_plan',
                  'pdp_product_batching_classes_plan', 'product_day_plan')
        read_only_fields = COMMON_READ_ONLY_FIELDS
        extra_kwargs = {
            'product_day_plan': {
                'required': False
            }
        }

    def validate_product_batching(self, value):
        pb_obj = value
        for pbd_obj in pb_obj.batching_details.all():
            if not pbd_obj.actual_weight:
                raise serializers.ValidationError('当前胶料配料标准详情数据不存在')
        return value

    def validate_plan_date(self, value):
        if not PlanSchedule.objects.filter(day_time=value).first():
            raise serializers.ValidationError('当前计划时间不存在')
        return value

    def validate_pdp_product_batching_classes_plan(self, value):
        if len(value) != 3:
            raise serializers.ValidationError('无效数据，必须有三条')
        return value

    @atomic()
    def create(self, validated_data):

        pdp_dic = {}
        pdp_dic['equip'] = validated_data.pop('equip')
        pdp_dic['product_batching'] = validated_data.pop('product_batching')
        plan_date = validated_data.pop('plan_date')
        pdp_dic['plan_schedule'] = PlanSchedule.objects.filter(day_time=plan_date).first()
        pdp_dic['bags_total_qty'] = validated_data.pop('bags_total_qty')
        pdp_dic['product_day_plan'] = validated_data.pop('product_day_plan', None)
        if pdp_dic['product_day_plan'] == None:
            pdp_dic.pop('product_day_plan')
        pdp_dic['created_user'] = self.context['request'].user
        # 创建配料小料日计划
        instance = super().create(pdp_dic)
        details = validated_data['pdp_product_batching_classes_plan']
        cd_queryset = ClassesDetail.objects.filter(
            work_schedule=WorkSchedule.objects.filter(plan_schedule__day_time=plan_date).first())
        i = 0
        # 创建配料小料日班次计划和原材料需求量
        for detail in details:
            detail_dic = dict(detail)
            detail_dic['plan_classes_uid'] = UUidTools.uuid1_hex()
            detail_dic['product_batching_day_plan'] = instance
            detail_dic['classes_detail'] = cd_queryset[i]
            i += 1
            pcp_obj = ProductBatchingClassesPlan.objects.create(**detail_dic, created_user=self.context['request'].user)
            for pbd_obj in instance.product_batching.batching_details.all():
                MaterialDemanded.objects.create(classes=pcp_obj.classes_detail,
                                                material=pbd_obj.material,
                                                material_demanded=pbd_obj.actual_weight * pcp_obj.bags_qty,
                                                plan_classes_uid=pcp_obj.plan_classes_uid,
                                                plan_schedule=instance.plan_schedule)
        return instance

    @atomic()
    def update(self, instance, validated_data):
        update_pcp_list = validated_data.pop('pdp_product_batching_classes_plan', None)
        day_time = validated_data.pop('plan_date', None)
        if day_time:
            validated_data['plan_schedule'] = PlanSchedule.objects.filter(day_time=day_time).first()
        else:
            validated_data['plan_schedule'] = instance.plan_schedule
        validated_data['last_updated_user'] = self.context['request'].user
        pdp_obj = super().update(instance, validated_data)
        # 若没有配料小料日班次计划
        if update_pcp_list is None:
            c_queryset = pdp_obj.pdp_product_batching_classes_plan.all()
            for c_obj in c_queryset:
                MaterialDemanded.objects.filter(plan_classes_uid=c_obj.plan_classes_uid).delete()
            for pcp_obj in pdp_obj.pdp_product_batching_classes_plan.all():
                for pbd_obj in pdp_obj.product_batching.batching_details.all():
                    MaterialDemanded.objects.create(classes=pcp_obj.classes_detail,
                                                    material=pbd_obj.material,
                                                    material_demanded=pbd_obj.actual_weight * pcp_obj.bags_qty,
                                                    plan_classes_uid=pcp_obj.plan_classes_uid,
                                                    plan_schedule=pdp_obj.plan_schedule)
            return pdp_obj
        # 删除原材料需求量和班次计划，再重写
        c_queryset = pdp_obj.pdp_product_batching_classes_plan.all()
        for c_obj in c_queryset:
            MaterialDemanded.objects.filter(plan_classes_uid=c_obj.plan_classes_uid).delete()
        c_queryset.delete()
        cd_queryset = ClassesDetail.objects.filter(
            work_schedule=WorkSchedule.objects.filter(plan_schedule__day_time=day_time).first())
        i = 0
        for update_pcp in update_pcp_list:
            update_pcp = dict(update_pcp)
            update_pcp['product_batching_day_plan'] = instance
            update_pcp['classes_detail'] = cd_queryset[i]
            update_pcp['plan_classes_uid'] = UUidTools.uuid1_hex()
            update_pcp['last_updated_user'] = self.context['request'].user
            # ProductBatchingClassesPlan.objects.create(**update_pcp)
            pcp_obj = ProductBatchingClassesPlan.objects.create(**update_pcp, created_user=self.context['request'].user)
            i += 1
            for pbd_obj in pdp_obj.product_batching.batching_details.all():
                MaterialDemanded.objects.create(classes=pcp_obj.classes_detail,
                                                material=pbd_obj.material,
                                                material_demanded=pbd_obj.actual_weight * pcp_obj.bags_qty,
                                                plan_classes_uid=pcp_obj.plan_classes_uid,
                                                plan_schedule=pdp_obj.plan_schedule)
        return pdp_obj


# class MaterialRequisitionSerializer(BaseModelSerializer):
#     class Meta:
#         model = MaterialRequisitionClasses
#         fields = '__all__'


class MaterialDemandedSerializer(BaseModelSerializer):
    """原材料需求量序列化 暂时没用到，用到了"""
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


class MaterialRequisitionClassesSerializer(BaseModelSerializer):
    """领料计划的序列化"""
    material_ids = serializers.ListField(help_text='三个需求量id', write_only=True)
    plan_date = serializers.DateField(help_text='日期', write_only=True)
    weights = serializers.ListField(help_text='早中晚领料计划的重量', write_only=True)

    class Meta:
        model = MaterialRequisitionClasses
        fields = ('material_ids', 'plan_date', 'weights',)
        read_only_fields = COMMON_READ_ONLY_FIELDS

    # def validate_material_id(self, value):
    #     if not MaterialDemanded.objects.filter(id=value, delete_flag=False):
    #         raise serializers.ValidationError('当前原材料需要量不存在')
    #     return value

    def validate_plan_date(self, value):
        if not PlanSchedule.objects.filter(day_time=value).first():
            raise serializers.ValidationError('当前计划时间不存在')
        return value

    def validate_weights(self, value):
        if len(value) != 3:
            raise serializers.ValidationError('无效数据，必须有三条')
        return value

    @atomic()
    def create(self, validated_data):
        plan_date = validated_data.pop('plan_date')
        weights = validated_data.pop('weights')
        material_ids = validated_data.pop('material_ids')
        for material_id in material_ids:
            mrc_queryset = MaterialDemanded.objects.filter(id=material_id).first().md_material_requisition_classes.all()
            if mrc_queryset:
                mrc_queryset.delete()
        cd_queryset = ClassesDetail.objects.filter(
            work_schedule=WorkSchedule.objects.filter(plan_schedule__day_time=plan_date).first())
        i = 0
        for weight in weights:
            mrc_dic = {}
            mrc_dic['plan_classes_uid'] = UUidTools.uuid1_hex()
            mrc_dic['created_user'] = self.context['request'].user
            mrc_dic['weight'] = weight
            mrc_dic['classes_detail'] = cd_queryset[i]
            mrc_dic['unit'] = 'kg'
            instance = MaterialRequisitionClasses.objects.create(**mrc_dic)
            for material_id in material_ids:
                instance.material_demanded.add(MaterialDemanded.objects.filter(id=material_id).first())
            i += 1
        return instance


class ProductDayPlanCopySerializer(BaseModelSerializer):
    """胶料日计划的复制序列化"""
    src_date = serializers.DateField(help_text="2020-07-31", write_only=True)
    dst_date = serializers.DateField(help_text="2020-08-01", write_only=True)

    # is_delete = serializers.BooleanField(help_text='是否覆盖', write_only=True)

    class Meta:
        model = ProductDayPlan
        # fields = ('src_date', 'dst_date', 'is_delete')
        fields = ('src_date', 'dst_date')

    def validate_src_date(self, value):
        instance = PlanSchedule.objects.filter(day_time=value).first()
        if not instance:
            raise serializers.ValidationError('被复制的日期没有计划时间')
        pdp_obj = ProductDayPlan.objects.filter(plan_schedule=instance)
        if not pdp_obj:
            raise serializers.ValidationError('被复制的日期没有计划')
        return value

    def validate_dst_date(self, value):
        instance = PlanSchedule.objects.filter(day_time=value)
        if not instance:
            raise serializers.ValidationError('新建的日期没有计划时间')
        delete_pdp_queryset = ProductDayPlan.objects.filter(plan_schedule__day_time=value, delete_flag=False)
        if delete_pdp_queryset:
            raise serializers.ValidationError('新建的日期当天已经有胶料日计划了')
        return value

    def validate(self, attrs):
        src_date = attrs['src_date']
        dst_date = attrs['dst_date']
        if dst_date < src_date:
            raise serializers.ValidationError('新建日期不能小于被复制日期')

        instance = PlanSchedule.objects.filter(day_time=dst_date)
        if not instance:
            raise serializers.ValidationError('新建的日期没有计划时间')
        return attrs

    @atomic()
    def create(self, validated_data):
        src_date = validated_data.pop('src_date')
        dst_date = validated_data.pop('dst_date')
        ps_obj = PlanSchedule.objects.filter(day_time=dst_date).first()
        pdp_queryset = ProductDayPlan.objects.filter(plan_schedule__day_time=src_date, delete_flag=False)
        delete_pdp_queryset = ProductDayPlan.objects.filter(plan_schedule__day_time=dst_date, delete_flag=False)
        # 如果新建日期当天有计划的话，是会被覆盖掉的
        if delete_pdp_queryset:
            ProductDayPlan.objects.filter(plan_schedule__day_time=dst_date, delete_flag=False).update(delete_flag=True,
                                                                                                      delete_user=
                                                                                                      self.context[
                                                                                                          'request'].user)
            for delete_pdp_obj in delete_pdp_queryset:
                delete_pcp_queryset = ProductClassesPlan.objects.filter(product_day_plan=delete_pdp_obj,
                                                                        delete_flag=False)
                if delete_pcp_queryset:
                    for delete_pcp_obj in delete_pcp_queryset:
                        if MaterialDemanded.objects.filter(plan_classes_uid=delete_pcp_obj.plan_classes_uid,
                                                           delete_flag=False):
                            MaterialDemanded.objects.filter(plan_classes_uid=delete_pcp_obj.plan_classes_uid,
                                                            delete_flag=False).update(
                                delete_flag=True,
                                delete_user=self.context[
                                    'request'].user)
                    ProductClassesPlan.objects.filter(product_day_plan=delete_pdp_obj,
                                                      delete_flag=False).update(delete_flag=True,
                                                                                delete_user=self.context[
                                                                                    'request'].user)
        # 实现复制功能 创建了胶料日计划 胶料日班次计划 原材料需求量
        for pdp_obj in pdp_queryset:
            instance = ProductDayPlan.objects.create(equip=pdp_obj.equip, product_batching=pdp_obj.product_batching,
                                                     plan_schedule=ps_obj, created_user=self.context['request'].user)

            pc_queryset = ProductClassesPlan.objects.filter(product_day_plan=pdp_obj)
            for pc_obj in pc_queryset:
                pcp_obj = ProductClassesPlan.objects.create(product_day_plan=instance, sn=pc_obj.sn,
                                                            plan_trains=pc_obj.plan_trains,
                                                            time=pc_obj.time,
                                                            weight=pc_obj.weight, unit=pc_obj.unit,
                                                            work_schedule_plan=pc_obj.work_schedule_plan,
                                                            plan_classes_uid=UUidTools.uuid1_hex(),
                                                            created_user=self.context['request'].user)
                for pbd_obj in instance.product_batching.batching_details.all():
                    MaterialDemanded.objects.create(classes=pcp_obj.classes_detail,
                                                    material=pbd_obj.material,
                                                    material_demanded=pbd_obj.actual_weight * pcp_obj.plan_trains,
                                                    plan_classes_uid=pcp_obj.plan_classes_uid,
                                                    plan_schedule=instance.plan_schedule)
        return instance


class ProductBatchingDayPlanCopySerializer(BaseModelSerializer):
    src_date = serializers.DateField(help_text="2020-07-31", write_only=True)
    dst_date = serializers.DateField(help_text="2020-08-01", write_only=True)

    class Meta:
        model = ProductBatchingDayPlan
        fields = ('src_date', 'dst_date')

    def validate_src_date(self, value):
        instance = PlanSchedule.objects.filter(day_time=value).first()
        if not instance:
            raise serializers.ValidationError('被复制的日期没有计划时间')
        pdp_obj = ProductBatchingDayPlan.objects.filter(plan_schedule=instance)
        if not pdp_obj:
            raise serializers.ValidationError('被复制的日期没有计划')
        return value

    def validate_dst_date(self, value):
        instance = PlanSchedule.objects.filter(day_time=value)
        if not instance:
            raise serializers.ValidationError('新建的日期没有计划时间')
        delete_pdp_queryset = ProductBatchingDayPlan.objects.filter(plan_schedule__day_time=value, delete_flag=False)
        if delete_pdp_queryset:
            raise serializers.ValidationError('新建的日期已经有配料小料日计划了')
        return value

    def validate(self, attrs):
        src_date = attrs['src_date']
        dst_date = attrs['dst_date']
        if dst_date < src_date:
            raise serializers.ValidationError('新建日期不能小于被复制日期')
        return attrs

    @atomic()
    def create(self, validated_data):

        src_date = validated_data.pop('src_date')
        dst_date = validated_data.pop('dst_date')
        ps_obj = PlanSchedule.objects.filter(day_time=dst_date).first()
        pbdp_queryset = ProductBatchingDayPlan.objects.filter(plan_schedule__day_time=src_date, delete_flag=False)
        delete_pdp_queryset = ProductBatchingDayPlan.objects.filter(plan_schedule__day_time=dst_date, delete_flag=False)
        # 如果新建日期有配料小料日计划就删除
        if delete_pdp_queryset:
            ProductBatchingDayPlan.objects.filter(plan_schedule__day_time=dst_date, delete_flag=False).update(
                delete_flag=True,
                delete_user=
                self.context[
                    'request'].user)
            for delete_pdp_obj in delete_pdp_queryset:
                delete_pbcp_queryset = ProductBatchingClassesPlan.objects.filter(
                    product_batching_day_plan=delete_pdp_obj, delete_flag=False)
                if delete_pbcp_queryset:
                    for delete_pbcp_obj in delete_pbcp_queryset:
                        if MaterialDemanded.objects.filter(plan_classes_uid=delete_pbcp_obj.plan_classes_uid,
                                                           delete_flag=False):
                            MaterialDemanded.objects.filter(plan_classes_uid=delete_pbcp_obj.plan_classes_uid,
                                                            delete_flag=False).update(
                                delete_flag=True,
                                delete_user=
                                self.context[
                                    'request'].user)
                    ProductBatchingClassesPlan.objects.filter(
                        product_batching_day_plan=delete_pdp_obj, delete_flag=False).update(
                        delete_flag=True,
                        delete_user=self.context[
                            'request'].user)
        # 复制配料小料日计划 配料小料日班次计划 原材料需求量
        for pbdp_obj in pbdp_queryset:
            instance = ProductBatchingDayPlan.objects.create(equip=pbdp_obj.equip,
                                                             product_batching=pbdp_obj.product_batching,
                                                             plan_schedule=ps_obj,
                                                             bags_total_qty=pbdp_obj.bags_total_qty,
                                                             product_day_plan=pbdp_obj.product_day_plan,
                                                             created_user=self.context['request'].user)
            pc_queryset = ProductBatchingClassesPlan.objects.filter(product_batching_day_plan=pbdp_obj)
            for pc_obj in pc_queryset:
                pcp_obj = ProductBatchingClassesPlan.objects.create(product_batching_day_plan=instance,
                                                                    sn=pc_obj.sn, bags_qty=pc_obj.bags_qty,
                                                                    # time=pc_obj.time,
                                                                    # weight=pc_obj.weight, unit=pc_obj.unit,
                                                                    classes_detail=pc_obj.classes_detail,
                                                                    plan_classes_uid=UUidTools.uuid1_hex(),
                                                                    created_user=self.context['request'].user)
                for pbd_obj in instance.product_batching.batching_details.all():
                    MaterialDemanded.objects.create(classes=pcp_obj.classes_detail,
                                                    material=pbd_obj.material,
                                                    material_demanded=pbd_obj.actual_weight * pcp_obj.bags_qty,
                                                    plan_classes_uid=pcp_obj.plan_classes_uid,
                                                    plan_schedule=instance.plan_schedule
                                                    )
        return instance


# class MaterialRequisitionCopySerializer(BaseModelSerializer):
#     src_date = serializers.DateField(help_text="2020-07-31", write_only=True)
#     dst_date = serializers.DateField(help_text="2020-08-01", write_only=True)
#
#     class Meta:
#         model = MaterialDemanded
#         fields = ('src_date', 'dst_date')
#
#     def validate_src_date(self, value):
#         instance = PlanSchedule.objects.filter(day_time=value).first()
#         if not instance:
#             raise serializers.ValidationError('被复制的日期没有计划时间')
#         pdp_queryset = ProductDayPlan.objects.filter(plan_schedule=instance)
#         pbdp_queryset = ProductBatchingDayPlan.objects.filter(plan_schedule=instance)
#         if not pdp_queryset or not pbdp_queryset:
#             raise serializers.ValidationError('被复制的日期没有胶料计划或者小料计划')
#         if pdp_queryset:
#             for pdp_obj in pdp_queryset:
#                 pcp_queryset = pdp_obj.pdp_product_classes_plan.all()
#                 if not pcp_queryset:
#                     raise serializers.ValidationError('被复制的日期没有胶料班次计划')
#                 for pcp_obj in pcp_queryset:
#                     mdpco_queryset = MaterialDemanded.objects.filter(plan_classes_uid=pcp_obj.plan_classes_uid)
#                     if not mdpco_queryset:
#                         raise serializers.ValidationError('被复制的日期没有胶料计划的原材料需求量计划')
#         if pbdp_queryset:
#             for pbdp_obj in pbdp_queryset:
#                 pbcp_queryset = pbdp_obj.pdp_product_batching_classes_plan.all()
#                 if not pbcp_queryset:
#                     raise serializers.ValidationError('被复制的日期没有小料班次计划')
#                 for pbcp_obj in pbcp_queryset:
#                     mdpbcp_queryset = MaterialDemanded.objects.filter(plan_classes_uid=pbcp_obj.plan_classes_uid)
#                     if not mdpbcp_queryset:
#                         raise serializers.ValidationError('被复制的日期没有小料计划的原材料需求量计划')
#         return value
#
#     def validate_dst_date(self, value):
#         instance = PlanSchedule.objects.filter(day_time=value).first()
#         if not instance:
#             raise serializers.ValidationError('被新建的日期没有计划时间')
#         pdp_queryset = ProductDayPlan.objects.filter(plan_schedule=instance)
#         pbdp_queryset = ProductBatchingDayPlan.objects.filter(plan_schedule=instance)
#         if not pdp_queryset or not pbdp_queryset:
#             raise serializers.ValidationError('被新建的日期没有胶料计划或者小料计划')
#         if pdp_queryset:
#             for pdp_obj in pdp_queryset:
#                 pcp_queryset = pdp_obj.pdp_product_classes_plan.all()
#                 if not pcp_queryset:
#                     raise serializers.ValidationError('被新建的日期没有胶料班次计划')
#         if pbdp_queryset:
#             for pbdp_obj in pbdp_queryset:
#                 pbcp_queryset = pbdp_obj.pdp_product_batching_classes_plan.all()
#                 if not pbcp_queryset:
#                     raise serializers.ValidationError('被新建的日期没有小料班次计划')
#         return value
#
#     def validate(self, attrs):
#         src_date = attrs['src_date']
#         dst_date = attrs['dst_date']
#         if dst_date < src_date:
#             raise serializers.ValidationError('新建日期不能小于被复制日期')
#         return attrs
#
#     @atomic()
#     def create(self, validated_data):
#         src_date = validated_data.pop('src_date')
#         dst_date = validated_data.pop('dst_date')
#         dps_obj = PlanSchedule.objects.filter(day_time=dst_date).first()
#         sps_obj = PlanSchedule.objects.filter(day_time=src_date).first()
#         pdp_queryset = ProductDayPlan.objects.filter(
#             plan_schedule=dps_obj).first()
#         pbdp_queryset = ProductBatchingDayPlan.objects.filter(
#             plan_schedule=dps_obj.first())
#         if pdp_queryset:
#             for pdp_obj in pdp_queryset:
#                 pcp_queryset = ProductClassesPlan.objects.filter(product_day_plan=pdp_obj)
#                 if pcp_queryset:
#                     for pcp_obj in pcp_queryset:
#                         for pbd_obj in pdp_obj.product_batching.batching_details.all():
#                             MaterialDemanded.objects.create(classes=pcp_obj.classes_detail,
#                                                             material=pbd_obj.material,
#                                                             material_demanded=pbd_obj.actual_weight * pcp_obj.plan_trains,
#                                                             plan_classes_uid=pcp_obj.plan_classes_uid,
#                                                             plan_schedule=pdp_obj.plan_schedule
#                                                             )
#             mr_queryset = MaterialDemanded.objects.filter(plan_classes_uid=src_date, delete_flag=False)
#         delete_pdp_queryset = MaterialRequisition.objects.filter(plan_schedule__day_time=dst_date, delete_flag=False)
#         if delete_pdp_queryset:
#             MaterialRequisition.objects.filter(plan_schedule__day_time=dst_date, delete_flag=False).update(
#                 delete_flag=True,
#                 delete_user=
#                 self.context[
#                     'request'].user)
#             for delete_pdp_obj in delete_pdp_queryset:
#                 MaterialRequisitionClasses.objects.filter(material_requisition=delete_pdp_obj).update(
#                     delete_flag=True,
#                     delete_user=self.context[
#                         'request'].user)
#         for mr_obj in mr_queryset:
#             instance = MaterialRequisition.objects.create(material_demanded=mr_obj.material_demanded,
#                                                           count=mr_obj.count,
#                                                           plan_schedule=ps_obj, unit=mr_obj.unit,
#                                                           created_user=self.context['request'].user
#                                                           )
#             pc_queryset = MaterialRequisitionClasses.objects.filter(material_requisition=mr_obj)
#             for pc_obj in pc_queryset:
#                 MaterialRequisitionClasses.objects.create(material_requisition=instance,
#                                                           sn=pc_obj.sn,
#                                                           weight=pc_obj.weight,
#                                                           unit=pc_obj.unit,
#                                                           classes_detail=pc_obj.classes_detail,
#                                                           created_user=self.context['request'].user)
#         return instance


'''
class MaterialRequisitionCopySerializer(BaseModelSerializer):
    src_date = serializers.DateField(help_text="2020-07-31", write_only=True)
    dst_date = serializers.DateField(help_text="2020-08-01", write_only=True)

    class Meta:
        model = MaterialRequisition
        fields = ('src_date', 'dst_date')

    def validate_src_date(self, value):
        instance = PlanSchedule.objects.filter(day_time=value).first()
        if not instance:
            raise serializers.ValidationError('被复制的日期没有计划时间')
        pdp_obj = MaterialRequisition.objects.filter(plan_schedule=instance)
        if not pdp_obj:
            raise serializers.ValidationError('被复制的日期没有计划')
        return value

    def validate_dst_date(self, value):
        instance = PlanSchedule.objects.filter(day_time=value)
        if not instance:
            raise serializers.ValidationError('新建的日期没有计划时间')
        return value

    def validate(self, attrs):
        src_date = attrs['src_date']
        dst_date = attrs['dst_date']
        if dst_date < src_date:
            raise serializers.ValidationError('新建日期不能小于被复制日期')
        return attrs

    @atomic()
    def create(self, validated_data):

        src_date = validated_data.pop('src_date')
        dst_date = validated_data.pop('dst_date')
        ps_obj = PlanSchedule.objects.filter(day_time=dst_date).first()
        mr_queryset = MaterialRequisition.objects.filter(plan_schedule__day_time=src_date, delete_flag=False)
        delete_pdp_queryset = MaterialRequisition.objects.filter(plan_schedule__day_time=dst_date, delete_flag=False)
        if delete_pdp_queryset:
            MaterialRequisition.objects.filter(plan_schedule__day_time=dst_date, delete_flag=False).update(
                delete_flag=True,
                delete_user=
                self.context[
                    'request'].user)
            for delete_pdp_obj in delete_pdp_queryset:
                MaterialRequisitionClasses.objects.filter(material_requisition=delete_pdp_obj).update(
                    delete_flag=True,
                    delete_user=self.context[
                        'request'].user)
        for mr_obj in mr_queryset:
            instance = MaterialRequisition.objects.create(material_demanded=mr_obj.material_demanded,
                                                          count=mr_obj.count,
                                                          plan_schedule=ps_obj, unit=mr_obj.unit,
                                                          created_user=self.context['request'].user
                                                          )
            pc_queryset = MaterialRequisitionClasses.objects.filter(material_requisition=mr_obj)
            for pc_obj in pc_queryset:
                MaterialRequisitionClasses.objects.create(material_requisition=instance,
                                                          sn=pc_obj.sn,
                                                          weight=pc_obj.weight,
                                                          unit=pc_obj.unit,
                                                          classes_detail=pc_obj.classes_detail,
                                                          created_user=self.context['request'].user)
        return instance
'''
'''
class MaterialRequisitionSerializer(BaseModelSerializer):
    """领料日计划序列化"""
    mr_material_requisition_classes = MaterialRequisitionClassesSerializer(many=True,
                                                                           help_text='{"sn":1,"weight":1,"unit":"1","classes_detail":1}')
    plan_date = serializers.DateField(help_text="2020-07-31", write_only=True)
    material_type = serializers.CharField(source='material_demanded.material.material_type', read_only=True)
    material_no = serializers.CharField(source='material_demanded.material.material_no', read_only=True)
    material_name = serializers.CharField(source='material_demanded.material.material_name', read_only=True)
    # material_demanded = MaterialDemandedSerializer( read_only=True)

    class Meta:
        model = MaterialRequisition
        fields = ('id', 'material_type', 'material_no', 'material_name',
                  'material_demanded', 'count', 'plan_date', 'unit',
                  'mr_material_requisition_classes')
        read_only_fields = COMMON_READ_ONLY_FIELDS

    def validate_plan_date(self, value):
        if not PlanSchedule.objects.filter(day_time=value).first():
            raise serializers.ValidationError('当前计划时间不存在')
        return value

    @atomic()
    def create(self, validated_data):

        pdp_dic = {}
        pdp_dic['material_demanded'] = validated_data.pop('material_demanded')
        pdp_dic['count'] = validated_data.pop('count')
        # pdp_dic['plan_schedule'] = validated_data.pop('plan_schedule')
        pdp_dic['plan_schedule'] = PlanSchedule.objects.filter(day_time=validated_data.pop('plan_date')).first()
        pdp_dic['unit'] = validated_data.pop('unit')
        # instance = MaterialRequisition.objects.create(**pdp_dic)
        pdp_dic['created_user'] = self.context['request'].user
        instance = super().create(pdp_dic)
        details = validated_data['mr_material_requisition_classes']
        for detail in details:
            detail_dic = dict(detail)
            detail_dic['material_requisition'] = instance
            MaterialRequisitionClasses.objects.create(**detail_dic, created_user=self.context['request'].user)
        return instance

    @atomic()
    def update(self, instance, validated_data):

        update_pcp_list = validated_data.pop('mr_material_requisition_classes', None)
        day_time = validated_data.pop('plan_date', None)
        if day_time:
            validated_data['plan_schedule'] = PlanSchedule.objects.filter(day_time=day_time).first()
        else:
            validated_data['plan_schedule'] = instance.plan_schedule
        validated_data['last_updated_user'] = self.context['request'].user
        pdp_obj = super().update(instance, validated_data)
        if update_pcp_list is None:
            return pdp_obj
        MaterialRequisitionClasses.objects.filter(material_requisition=instance).delete()
        for update_pcp in update_pcp_list:
            update_pcp = dict(update_pcp)
            update_pcp['material_requisition'] = instance
            update_pcp['last_updated_user'] = self.context['request'].user
            MaterialRequisitionClasses.objects.create(**update_pcp)
        return pdp_obj
'''
