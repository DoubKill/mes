from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class TitleMixin:

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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


class EquipBaseInfoManageView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/equip_base_info_manage.html'
    name_path = ['基础信息管理', '设备基础信息管理']


# 倒班时间管理
class ChangeShiftsManageView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/change_shifts_manage.html'
    name_path = ['基础信息管理', '倒班时间管理']


class FactoryScheduleManageView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/factory_schedule_manage.html'
    name_path = ['基础信息管理', '工厂排班管理']


class EquipCategoryManageView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/equip_category_manage.html'
    name_path = ['基础信息管理', '设备种类']


class EquipManageView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/equip_manage.html'
    name_path = ['基础信息管理', '设备基础信息']


class MaterialBaseInfoManageView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/material_base_info_manage.html'
    name_path = ['配方管理', '原材料基本信息管理']


class RubberRecipeStandardManageView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/rubber_recipe_standard_manage.html'
    name_path = ['配方管理', '胶料配方标准管理']


class RubberMaterialStandardManageView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/rubber_material_standard_manage.html'
    name_path = ['配方管理', '胶料配料标准管理']


class RubberScheduleDailyPlanView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/rubber_schedule_daily_plan.html'
    name_path = ['生产计划管理', '排产胶料日计划']

class RubberSmallStuffDailyPlanView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/rubber_smallStuff_daily_plan.html'
    name_path = ['生产计划管理', '排产配料小料日计划']

class SearchRubberInfoView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/search_rubber_info.html'
    name_path = ['配方管理', '查询胶料主信息']


class MaterialRequisitionsPlanView(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/material_requisitions_plan.html'
    name_path = ['生产计划管理', '排产领料计划']

class InternalMixerProduction(TitleMixin, LoginRequiredMixin, TemplateView):
    template_name = 'gui/internal_mixer_production.html'
    name_path = ['生产管理', '密炼生产履历']