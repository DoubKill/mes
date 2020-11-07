# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/10/30
name: 
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from django.apps import apps

models = apps.get_models()

for model in models:
    if "django" in models.__str__:
        continue
    query_set = model.objects.all()
    all_count = query_set.count()
    for x in range(all_count // 1000 + 1):
        temp_set = query_set[x*1000:(x+1)*1000]
        model.objects.using("bak").bulk_create(list(temp_set))
