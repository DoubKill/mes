#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2020/08/26 10:05
# @Author : liubowen
# @File : sync.py


"""
    基础数据同步至上辅机
"""

import logging
from datetime import datetime

import requests
from django.conf import settings
from rest_framework import serializers

from plan.models import ProductClassesPlan, ProductDayPlan
from recipe.models import ProductBatching, ProductBatchingDetail

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
            res = requests.post(self.endpoint + self.Backend.path, headers=headers, json=kwargs)
        except Exception as err:
            logger.error(err)
            raise Exception('上辅机服务错误')
        logger.info(res.text)
        if res.status_code != 201:
            raise Exception(res.text)


class ProductBatchingDetailSerializer(serializers.ModelSerializer):
    material = serializers.CharField(source='material.material_no')

    class Meta:
        model = ProductBatchingDetail
        fields = ('sn', 'material', 'actual_weight', 'standard_error', 'auto_flag', 'type')


class ProductBatchingSyncInterface(serializers.ModelSerializer, BaseInterface):
    """配方同步序列化器"""
    created_date = serializers.SerializerMethodField()
    factory = serializers.CharField(source='factory.global_no')
    site = serializers.CharField(source='site.global_no')
    product_info = serializers.CharField(source='product_info.product_no')
    dev_type = serializers.CharField(source='dev_type.category_no', default=None)
    stage = serializers.CharField(source='stage.global_no')
    equip = serializers.CharField(source='equip.equip_no', default=None)
    used_time = serializers.SerializerMethodField()
    batching_details = ProductBatchingDetailSerializer(many=True)

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
                  'auto_material_weight', 'production_time_interval', 'batching_details')


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


class ProductBatchingDetailSyncInterface(serializers.ModelSerializer):
    material = serializers.CharField(source='material.material_no')

    class Meta:
        model = ProductBatchingDetail
        fields = ('product_batching', 'sn', 'material', 'actual_weight', 'standard_error', 'auto_flag', 'type')


class ProductBatchingSyncInterface(serializers.ModelSerializer):
    batching_details = ProductBatchingDetailSyncInterface(many=True)

    class Meta:
        model = ProductBatching
        fields = (
            'factory', 'site', 'product_info', 'precept', 'stage_product_batch_no', 'dev_type', 'stage', 'versions',
            'used_type', 'batching_weight', 'manual_material_weight', 'auto_material_weight', 'volume', 'submit_user',
            'submit_time', 'reject_user', 'reject_time', 'used_user', 'used_time', 'obsolete_user', 'obsolete_time',
            'production_time_interval',
            'equip', 'batching_type', 'batching_details')


class ProductDayPlanSyncInterface(serializers.ModelSerializer):
    product_batching = serializers.CharField(source='product_batching.stage_product_batch_no')

    class Meta:
        model = ProductDayPlan
        fields = ('equip', 'product_batching', 'plan_schedule')


class ProductClassesPlanSyncInterface(serializers.ModelSerializer, BaseInterface):
    """计划同步序列化器"""

    equip = serializers.CharField(source='equip.equip_no')
    work_schedule_plan = serializers.CharField(source='work_schedule_plan.work_schedule_plan_no')
    product_batching = ProductBatchingSyncInterface(read_only=True)
    product_day_plan = ProductDayPlanSyncInterface(read_only=True)

    class Backend:
        path = 'api/v1/plan/plan-receive/'

    class Meta:
        model = ProductClassesPlan
        fields = ('product_day_plan',
                  'sn', 'plan_trains', 'time', 'weight', 'unit', 'work_schedule_plan',
                  'plan_classes_uid', 'note', 'equip',
                  'product_batching')
