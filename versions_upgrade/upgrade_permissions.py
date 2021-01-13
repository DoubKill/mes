
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


if __name__ == '__main__':
    main()