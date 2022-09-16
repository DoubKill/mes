import django_filters

from system.models import User, GroupExtension, Section, UserOperationLog


class UserFilter(django_filters.rest_framework.FilterSet):
    num = django_filters.CharFilter(field_name='num', lookup_expr='icontains', help_text='工号')
    username = django_filters.CharFilter(field_name='username', lookup_expr='icontains', help_text='用户名')
    groups = django_filters.CharFilter(field_name='group_extensions', help_text='角色id')
    is_leave = django_filters.BooleanFilter(field_name='user_extension__is_leave', help_text='是否离职')
    section_name = django_filters.CharFilter(field_name='section__name', lookup_expr='icontains', help_text='部门')

    class Meta:
        model = User
        fields = ('num', 'username', 'is_leave', 'groups', 'is_active', 'section_id', 'section_name', 'is_superuser')


class GroupExtensionFilter(django_filters.rest_framework.FilterSet):
    group_code = django_filters.CharFilter(field_name="group_code", lookup_expr="icontains", help_text="角色代码")
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains", help_text="角色名称")

    class Meta:
        model = GroupExtension
        fields = {"group_code", "name", 'use_flag', 'section_id'}


class SectionFilter(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(field_name='name', help_text='名称', lookup_expr='icontains')
    section_id = django_filters.CharFilter(field_name='section_id', help_text="编码", lookup_expr='icontains')

    class Meta:
        model = Section
        fields = ('name', 'section_id', 'parent_section_id')


class UserOperationLogFilter(django_filters.rest_framework.FilterSet):
    st = django_filters.CharFilter(field_name='create_time', help_text='开始时间', lookup_expr='gte')
    et = django_filters.CharFilter(field_name='create_time', help_text='结束时间', lookup_expr='lte')
    operator = django_filters.CharFilter(field_name='operator', help_text='操作人', lookup_expr='icontains')
    menu_name = django_filters.CharFilter(field_name='menu_name', help_text='界面名称', lookup_expr='icontains')

    class Meta:
        model = UserOperationLog
        fields = ('st', 'et', 'operator', 'menu_name')