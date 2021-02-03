import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.dispatch import receiver

from equipment.models import EquipMaintenanceOrder, InformContent, PlatformConfig
import logging

from equipment.task import send_ding_msg

logger = logging.getLogger('send_log')


# @receiver(post_save, sender=EquipMaintenanceOrder)
def equip_maintenance_order_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    if created:
        try:
            pc_obj = PlatformConfig.objects.filter(platform='mes测试', delete_flag=False).first()
            if not pc_obj:
                pc_obj = PlatformConfig.objects.get(id=1)
            ic_obj = InformContent.objects.create(platform=pc_obj,
                                                  content=pc_obj.tag + f':\n{instance.equip_part.equip.equip_no}的{instance.equip_part.name}发生故障，初步原因为{instance.first_down_reason}')

            mm = send_ding_msg(url=pc_obj.url, secret=pc_obj.private_key, msg=ic_obj.content, isAtAll=True)
            if mm['errcode'] == 0:
                ic_obj.sent_flag = True
                ic_obj.save()
            else:
                logger.error(f"{mm}")
        except Exception as e:
            logger.error(f"{e}")
