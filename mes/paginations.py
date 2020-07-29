from collections import OrderedDict
from datetime import datetime

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DefaultPageNumberPagination(PageNumberPagination):
    """
    继承基础分页，并在返回值里面新增sys_time
    """
    page_size = 10
    max_page_size = 1000
    page_size_query_param = "page_size"
    page_size_query_description = "自定义每页显示条数（最大%s条,默认%s条）" % (max_page_size, page_size)
    page_query_description = "翻页/页数"

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('sys_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class SinglePageNumberPagination(PageNumberPagination):
    """
    继承基础分页，只返回results
    """
    page_size = 1000
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('results', data)
        ]))
