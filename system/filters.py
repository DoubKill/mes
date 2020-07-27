import django_filters

from system.models import User, GroupExtension


class UserFilter(django_filters.rest_framework.FilterSet):
    num = django_filters.CharFilter(field_name='user_extension__num', lookup_expr='icontains', help_text='工号')
    username = django_filters.CharFilter(field_name='username', lookup_expr='icontains', help_text='用户名')
    is_leave = django_filters.BooleanFilter(field_name='user_extension__is_leave', help_text='是否离职')

    class Meta:
        model = User
        fields = ('num', 'username', 'is_leave')


class GroupExtensionFilter(django_filters.rest_framework.FilterSet):
    id = django_filters.CharFilter(field_name="id", lookup_expr="icontains", help_text="角色")
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains", help_text="角色名称")

    class Meta:
        model = GroupExtension
        fields = {"id", "name"}

