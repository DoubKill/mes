from rest_framework import pagination


class LimitOffsetPagination(pagination.LimitOffsetPagination):
    """分页器"""
    default_limit = 5
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 5
