from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class TitleMixin:

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['namePath'] = self.name_path
        return context


class GlobalCodesManageView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/global_codes_manage.html'
    name_path = ['基础信息管理', '公用代码管理']


class UserManageView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/user_manage.html'
    name_path = ['基础信息管理', '用户管理']


class GroupManageView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/group_manage.html'
    name_path = ['基础信息管理', '角色管理']


class UsersByGroupManageView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/users_by_group_manage.html'
    name_path = ['基础信息管理', '角色别用户管理']