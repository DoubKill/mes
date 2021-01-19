import datetime
import json
import os
import django



os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()


from rest_framework_extensions.cache.decorators import get_cache
from quality.serializers import BatchProductNoDaySerializer, BatchProductNoMonthSerializer, BatchCommonSerializer, \
    BatchMonthSerializer
from quality.models import BatchProductNo, BatchMonth
from django.utils import timezone


def batch_month():
    batches = BatchMonth.objects.filter(date__gte=start_time,
                                        date__lte=end_time)
    if batches:
        batches = BatchCommonSerializer.batch_annotate(batches)
        batches = batches.order_by('date')
    ret_data = BatchMonthSerializer(batches, many=True, context={'start_time': start_time, 'end_time': end_time}).data
    response_triple = (
        json.dumps(ret_data).encode("utf-8"),
        200,
        {'content-type': ('Content-Type', 'application/json'), 'vary': ('Vary', 'Accept'),
         'allow': ('Allow', 'GET, HEAD, OPTIONS')}
    )
    return response_triple

def batch_product_no_day():
    date = timezone.now()
    temp = BatchProductNo.objects.filter(
        batch__batch_month__date__year=date.year,
        batch__batch_month__date__month=date.month).distinct()
    ret_data = BatchProductNoDaySerializer(temp, many=True, context={'date': date}).data
    response_triple = (
        json.dumps(ret_data).encode("utf-8"),
        200,
        {'content-type': ('Content-Type', 'application/json'), 'vary': ('Vary', 'Accept'),
         'allow': ('Allow', 'GET, HEAD, OPTIONS')}
    )
    return response_triple


def batch_product_no_month():
    temp = BatchProductNo.objects.filter(
        batch__batch_month__date__gte=start_time,
        batch__batch_month__date__lte=end_time).distinct()
    ret_data = BatchProductNoMonthSerializer(temp, many=True, context={'start_time': start_time, 'end_time': end_time}).data
    response_triple = (
        json.dumps(ret_data).encode("utf-8"),
        200,
        {'content-type': ('Content-Type', 'application/json'), 'vary': ('Vary', 'Accept'),
         'allow': ('Allow', 'GET, HEAD, OPTIONS')}
    )
    return response_triple


if __name__ == '__main__':
    cache = get_cache("default")
    start_time = timezone.now() - datetime.timedelta(days=365)
    end_time = timezone.now()

    response_month = batch_month()
    cache.set("738a4a0b1e10c32a161e2c009249e0d7", response_month, 600)

    response_triple_month = batch_product_no_month()
    cache.set("5732516a6d2a1dba7bc19883a26ab3d3", response_triple_month, 600)

    response_triple_all = batch_product_no_day()
    cache.set("c764db64603ea41acb1f464913c02ee7", response_triple_all, 600)