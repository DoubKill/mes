
import os
import sys

import django
from django.db.transaction import atomic

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()


from init_data import permission_data
from system.models import Permissions


@atomic()
def main():
    for item in permission_data:
        if Permissions.objects.filter(id=item['id']).exists():
            Permissions.objects.filter(id=item['id']).update(**item)
        else:
            Permissions.objects.create(**item)
    Permissions.objects.filter(id__in=[133, 134, 137, 138, 139, 140, 141, 142,
                                       143, 144, 145, 146, 147, 148, 149, 254,
                                       255, 256, 257, 258, 259, 260, 261, 262,
                                       263, 264, 265, 266, 267, 394, 396, 397,
                                       398, 399, 400, 401, 402, 403, 404, 405,
                                       406, 407]).delete()


if __name__ == '__main__':
    main()