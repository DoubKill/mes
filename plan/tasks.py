"""
    定时将计划数据下发到快检系统
"""
import os
import sys

import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from django.db.models import Max
import pymssql

from plan.models import ClassesPlanIssue, ProductClassesPlan


data_bases = [
    {"server": "10.4.23.140", "user": "guozi", "password": "mes2020", "name": "NIDAS3"},
    {"server": "10.4.23.141", "user": "guozi", "password": "mes2020", "name": "NIDAS3"}
]


def main():
    max_plan_id = ClassesPlanIssue.objects.aggregate(max_id=Max('product_classes_plan_id'))['max_id']
    classes_plans = ProductClassesPlan.objects.filter(delete_flag=False)
    if max_plan_id:
        classes_plans = classes_plans.filter(id__gt=max_plan_id, delete_flag=False)
    for classes_plan in classes_plans:
        ClassesPlanIssue.objects.get_or_create(product_classes_plan=classes_plan)

    for classes_issue in ClassesPlanIssue.objects.filter(status__in=(2, 3)):
        for data_base in data_bases:
            try:
                server = data_base['server']
                user = data_base['user']
                password = data_base['password']
                name = data_base['name']
                sql = """insert into production_info (classes, equip_no, product_no, plan_trains, factory_date) 
                values ('{}', '{}', '{}', {}, '{}');""".format(
                    classes_issue.product_classes_plan.work_schedule_plan.classes.global_name,
                    classes_issue.product_classes_plan.equip.equip_no,
                    classes_issue.product_classes_plan.product_batching.stage_product_batch_no,
                    classes_issue.product_classes_plan.plan_trains,
                    str(classes_issue.product_classes_plan.work_schedule_plan.plan_schedule.day_time))
                conn = pymssql.connect(server, user, password, name, autocommit=True)
                cur = conn.cursor()
                cur.execute(sql)
            except Exception:
                classes_issue.status = 3
        classes_issue.status = 1
        classes_issue.save()


if __name__ == '__main__':
    main()