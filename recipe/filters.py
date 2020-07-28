import django_filters

from recipe.models import Material, ProductInfo


class MaterialFilter(django_filters.rest_framework.FilterSet):
    material_type_id = django_filters.NumberFilter(field_name='material_type', help_text='原材料类别')

    class Meta:
        model = Material
        fields = ('material_type_id', )


class ProductInfoFilter(django_filters.rest_framework.FilterSet):
    product_no = django_filters.NumberFilter(field_name='product_no', help_text='原材料类别', lookup_expr='icontains')
    factory_id = django_filters.NumberFilter(field_name='factory_id', help_text='产地id')
    used_type_id = django_filters.NumberFilter(field_name='used_type_id', help_text='状态id')

    class Meta:
        model = ProductInfo
        fields = ('product_no', 'factory_id', 'used_type_id')