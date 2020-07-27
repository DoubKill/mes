import django_filters

from recipe.models import Material


class MaterialFilter(django_filters.rest_framework.FilterSet):
    material_type_id = django_filters.NumberFilter(field_name='material_type', help_text='原材料类别')

    class Meta:
        model = Material
        fields = ('material_type_id', )