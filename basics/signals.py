from django.db.models.signals import post_save
from django.dispatch import receiver

from basics.models import GlobalCodeType, GlobalCode, WorkSchedulePlan, PlanSchedule, Equip, ClassesDetail, \
    WorkSchedule, EquipCategoryAttribute
from recipe.models import Material, ProductInfo, MaterialAttribute, MaterialSupplier
from system.models import DataSynchronization


TYPE_CHOICE = (
        (1, '公共代码类型'),
        (2, '公共代码'),
        (3, '倒班管理'),
        (4, '倒班条目'),
        (5, '设备种类属性'),
        (6, '设备'),
        (7, '排班管理'),
        (8, '排班详情'),
        (9, '原材料'),
        (10, '胶料代码'),
        (11, '原材料属性'),
        (12, '原材料产地'))


@receiver(post_save, sender=GlobalCodeType)
def global_type_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    if not created:
        """更新了数据则需要从同步表中删除此记录"""
        DataSynchronization.objects.filter(type=1, obj_id=instance.id).delete()


@receiver(post_save, sender=GlobalCode)
def global_code_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    if not created:
        """更新了数据则需要从同步表中删除此记录"""
        DataSynchronization.objects.filter(type=2, obj_id=instance.id).delete()


@receiver(post_save, sender=WorkSchedule)
def work_schedule_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    if not created:
        """更新了数据则需要从同步表中删除此记录"""
        DataSynchronization.objects.filter(type=3, obj_id=instance.id).delete()


@receiver(post_save, sender=ClassesDetail)
def class_detail_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    if not created:
        """更新了数据则需要从同步表中删除此记录"""
        DataSynchronization.objects.filter(type=4, obj_id=instance.id).delete()


@receiver(post_save, sender=EquipCategoryAttribute)
def equip_attr_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    if not created:
        """更新了数据则需要从同步表中删除此记录"""
        DataSynchronization.objects.filter(type=5, obj_id=instance.id).delete()


@receiver(post_save, sender=Equip)
def equip_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    if not created:
        """更新了数据则需要从同步表中删除此记录"""
        DataSynchronization.objects.filter(type=6, obj_id=instance.id).delete()


@receiver(post_save, sender=PlanSchedule)
def plan_schedule_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    if not created:
        """更新了数据则需要从同步表中删除此记录"""
        DataSynchronization.objects.filter(type=7, obj_id=instance.id).delete()


@receiver(post_save, sender=WorkSchedulePlan)
def work_schedule_plan_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    if not created:
        """更新了数据则需要从同步表中删除此记录"""
        DataSynchronization.objects.filter(type=8, obj_id=instance.id).delete()


@receiver(post_save, sender=Material)
def material_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    if not created:
        """更新了数据则需要从同步表中删除此记录"""
        DataSynchronization.objects.filter(type=9, obj_id=instance.id).delete()


@receiver(post_save, sender=ProductInfo)
def material_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    if not created:
        """更新了数据则需要从同步表中删除此记录"""
        DataSynchronization.objects.filter(type=10, obj_id=instance.id).delete()


@receiver(post_save, sender=MaterialAttribute)
def material_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    if not created:
        """更新了数据则需要从同步表中删除此记录"""
        DataSynchronization.objects.filter(type=11, obj_id=instance.id).delete()


@receiver(post_save, sender=MaterialSupplier)
def material_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    if not created:
        """更新了数据则需要从同步表中删除此记录"""
        DataSynchronization.objects.filter(type=12, obj_id=instance.id).delete()