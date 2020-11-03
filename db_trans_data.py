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
        pass

