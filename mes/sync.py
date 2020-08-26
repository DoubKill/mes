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
        logger.info(kwargs)
        try:
            headers = {
                       "Content-Type": "application/json; charset=UTF-8",
                       }
            res = requests.post(self.endpoint+self.Backend.path, headers=headers, json=kwargs)
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
        fields = ('sn', 'material', 'actual_weight', 'standard_error', 'auto_flag')


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
        return datetime.strftime(obj.used_time, '%Y-%m-%d %H:%M:%S')

    class Backend:
        path = 'api/v1/recipe/recipe-receive/'

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

    class Backend:
        path = 'api/v1/recipe/recipe-obsolete/'

    class Meta:
        model = ProductBatching
        fields = ('stage_product_batch_no', )