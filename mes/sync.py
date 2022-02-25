#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2020/08/26 10:05
# @Author : liubowen
# @File : sync.py


"""
    基础数据同步至上辅机
"""
import json
import logging
from datetime import datetime
from doctest import master

import requests
from django.conf import settings
from django.db.models import F
from rest_framework import serializers

from mes.common_code import DecimalEncoder
from plan.models import ProductClassesPlan, ProductDayPlan
from recipe.models import ProductBatching, ProductBatchingDetail, ProductBatchingEquip

logger = logging.getLogger('sync_log')


class BaseInterface(object):
    endpoint = settings.AUXILIARY_URL

    class Backend:
        path = ""

    def request(self):
        if not self.Backend.path:
            raise NotImplementedError("未设置path")
        kwargs = getattr(self, 'data')
        # print(kwargs)
        logger.info(kwargs)
        try:
            headers = {
                "Content-Type": "application/json; charset=UTF-8",
                # "Authorization": kwargs['context']
            }
            # Decimal转换为float
            data = json.dumps(kwargs, cls=DecimalEncoder)
            res = requests.post(self.endpoint + self.Backend.path, headers=headers, data=data, timeout=10)
        except Exception as err:
            logger.error(err)
            raise Exception('上辅机服务错误')
        logger.info(res.text)
        if res.status_code != 201:
            raise Exception(res.text)


# class ProductBatchingDetailSerializer(serializers.ModelSerializer):
#     material = serializers.CharField(source='material.material_no')
#     master = serializers.DictField(default={})
#
#     def to_representation(self, instance):
#         res = super().to_representation(instance)
#         batching_info = ProductBatchingEquip.objects.filter(product_batching=instance.product_batching, is_used=True,
#                                                             material=instance.material, type=instance.type)
#         if not batching_info:
#             raise ValueError('未设置机台投料方式')
#         update_data = {i.equip_no: i.feeding_mode for i in batching_info}
#         res.update({'master': update_data})
#         return res
#
#     class Meta:
#         model = ProductBatchingDetail
#         fields = ('sn', 'material', 'actual_weight', 'standard_error', 'auto_flag', 'type', 'master')


class ProductBatchingSyncInterface(serializers.ModelSerializer, BaseInterface):
    """配方同步序列化器"""
    created_date = serializers.SerializerMethodField()
    factory = serializers.CharField(source='factory.global_no', default=None)
    site = serializers.CharField(source='site.global_no', default=None)
    product_info = serializers.CharField(source='product_info.product_no', default=None)
    dev_type = serializers.CharField(source='dev_type.category_no', default=None)
    stage = serializers.CharField(source='stage.global_no', default=None)
    equip = serializers.CharField(source='equip.equip_no', default=None)
    used_time = serializers.SerializerMethodField()
    batching_details = serializers.SerializerMethodField()
    weight_details = serializers.SerializerMethodField()

    def get_batching_details(self, obj):
        enable_equip = self.context.get('enable_equip')
        handle_batching_details = {}
        batching_equip_infos = ProductBatchingEquip.objects.filter(product_batching=obj, is_used=True)
        for equip_no in enable_equip:
            # P
            feed_p_info = batching_equip_infos.filter(equip_no=equip_no, feeding_mode__startswith='P')\
                .annotate(material_name=F('material__material_name'), sn=F('batching_detail_equip__sn'),
                          actual_weight=F('batching_detail_equip__actual_weight'),
                          standard_error=F('batching_detail_equip__standard_error'))\
                .values('material_name', 'actual_weight', 'standard_error', 'type', 'sn')
            # 炭黑油料投料方式为P需要转换类型, 并且重编sn
            for index, i in enumerate(feed_p_info):
                i['sn'] = index + 1
                if i['type'] != 1:
                    i['type'] = 1
            # C
            feed_c_info = batching_equip_infos.filter(equip_no=equip_no, feeding_mode__startswith='C', type=2) \
                .annotate(material_name=F('material__material_name'), sn=F('batching_detail_equip__sn'),
                          actual_weight=F('batching_detail_equip__actual_weight'),
                          standard_error=F('batching_detail_equip__standard_error')) \
                .values('material_name', 'actual_weight', 'standard_error', 'type', 'sn', 'feeding_mode')
            # O
            feed_o_info = batching_equip_infos.filter(equip_no=equip_no, feeding_mode__startswith='O', type=3) \
                .annotate(material_name=F('material__material_name'), sn=F('batching_detail_equip__sn'),
                          actual_weight=F('batching_detail_equip__actual_weight'),
                          standard_error=F('batching_detail_equip__standard_error')) \
                .values('material_name', 'actual_weight', 'standard_error', 'type', 'sn', 'feeding_mode')
            handle_batching_details[equip_no] = {'P': list(feed_p_info), 'C': list(feed_c_info), 'O': list(feed_o_info)}
        return handle_batching_details

    def get_weight_details(self, obj):
        enable_equip = self.context.get('enable_equip')
        weight_details = {}
        for weight_cnt_type in obj.weight_cnt_types.filter(delete_flag=False):
            # 获取投料方式
            batching_info = ProductBatchingEquip.objects.filter(product_batching=obj,
                                                                cnt_type_detail_equip__weigh_cnt_type=weight_cnt_type,
                                                                is_used=True, type=4, equip_no__in=enable_equip)
            equip_no_list = []
            for i in batching_info:
                if i.equip_no in equip_no_list:
                    continue
                # 走罐体的化工原料
                c_xl = batching_info.filter(equip_no=i.equip_no, feeding_mode__startswith='C')\
                    .annotate(material_name=F('material__material_name'),
                              actual_weight=F('cnt_type_detail_equip__standard_weight'),
                              standard_error=F('cnt_type_detail_equip__standard_error'))\
                    .values('material_name', 'actual_weight', 'standard_error')
                if i.equip_no not in weight_details:
                    weight_details[i.equip_no] = [{'material_name': weight_cnt_type.name,
                                                   'actual_weight': float(weight_cnt_type.cnt_total_weight(i.equip_no)),
                                                   'standard_error': float(weight_cnt_type.total_standard_error),
                                                   'feeding_mode': i.feeding_mode, 'c_xl_tank': list(c_xl)}]
                else:
                    weight_details[i.equip_no].append({'material_name': weight_cnt_type.name,
                                                       'actual_weight': float(weight_cnt_type.cnt_total_weight(i.equip_no)),
                                                       'standard_error': float(weight_cnt_type.total_standard_error),
                                                       'feeding_mode': i.feeding_mode, 'c_xl_tank': list(c_xl)})
                equip_no_list.append(i.equip_no)
        return weight_details

    @staticmethod
    def get_created_date(obj):
        return datetime.strftime(obj.created_date, '%Y-%m-%d %H:%M:%S')

    @staticmethod
    def get_used_time(obj):
        return datetime.strftime(obj.used_time, '%Y-%m-%d %H:%M:%S') if obj.used_time else None

    class Backend:
        path = 'api/v1/datain/recipe-receive/'

    class Meta:
        model = ProductBatching
        fields = ('created_date', 'factory', 'site', 'product_info',
                  'dev_type', 'stage', 'equip', 'used_time', 'precept', 'stage_product_batch_no',
                  'versions', 'used_type', 'batching_weight', 'manual_material_weight',
                  'auto_material_weight', 'production_time_interval', 'batching_details', 'weight_details')


class ProductObsoleteInterface(serializers.ModelSerializer, BaseInterface):
    """
    配方弃用
    """
    dev_type = serializers.CharField(source='dev_type.category_no')

    class Backend:
        path = 'api/v1/recipe/recipe-obsolete/'

    class Meta:
        model = ProductBatching
        fields = ('stage_product_batch_no', 'dev_type')


class ProductClassesPlanSync(serializers.ModelSerializer):
    created_date = serializers.SerializerMethodField()
    work_schedule_plan = serializers.CharField(source='work_schedule_plan.work_schedule_plan_no')
    equip = serializers.CharField(source='equip.equip_no')
    product_batching = serializers.CharField(source='product_batching.stage_product_batch_no')

    @staticmethod
    def get_created_date(obj):
        return datetime.strftime(obj.created_date, '%Y-%m-%d %H:%M:%S')

    class Meta:
        model = ProductClassesPlan
        fields = (
            'created_date', 'sn', 'plan_trains', 'time', 'weight', 'unit', 'work_schedule_plan', 'plan_classes_uid',
            'note', 'equip', 'product_batching', 'status')


class ProductDayPlanSyncInterface(serializers.ModelSerializer):
    product_batching = serializers.CharField(source='product_batching.stage_product_batch_no')
    plan_schedule = serializers.CharField(source='plan_schedule.plan_schedule_no')
    equip = serializers.CharField(source='equip.equip_no')

    class Meta:
        model = ProductDayPlan
        fields = ('equip', 'product_batching', 'plan_schedule')


class ProductClassesPlanSyncInterface(serializers.ModelSerializer, BaseInterface):
    """计划同步序列化器"""

    equip = serializers.CharField(source='equip.equip_no')
    work_schedule_plan = serializers.CharField(source='work_schedule_plan.work_schedule_plan_no')
    product_batching = serializers.CharField(source='product_batching.stage_product_batch_no')
    product_day_plan = ProductDayPlanSyncInterface(read_only=True)

    class Backend:
        path = 'api/v1/plan/plan-receive/'

    class Meta:
        model = ProductClassesPlan
        fields = ('product_day_plan',
                  'sn', 'plan_trains', 'time', 'weight', 'unit', 'work_schedule_plan',
                  'plan_classes_uid', 'note', 'equip',
                  'product_batching',)
