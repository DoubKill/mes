from django.views.generic import TemplateView


class TitleMixin:

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['namePath'] = self.name_path
        return context


class GlobalCodesManageView(TitleMixin, TemplateView):
    template_name = 'gui/global_codes_manage.html'
    name_path = ['基础信息管理', '公用代码管理']


class UserManageView(TitleMixin, TemplateView):
    template_name = 'gui/user_manage.html'
    name_path = ['基础信息管理', '用户管理']
