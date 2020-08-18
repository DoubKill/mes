import django_filters

from recipe.models import Material, ProductInfo, ProductBatching, MaterialAttribute


class MaterialFilter(django_filters.rest_framework.FilterSet):
    material_type_id = django_filters.NumberFilter(field_name='material_type', help_text='原材料类别')
    used_flag = django_filters.BooleanFilter(field_name='used_flag', help_text='是否使用')

    class Meta:
        model = Material
        fields = ('material_type_id', 'used_flag')


class ProductInfoFilter(django_filters.rest_framework.FilterSet):
    product_no = django_filters.CharFilter(field_name='product_no', help_text='原材料类别', lookup_expr='icontains')
    factory_id = django_filters.NumberFilter(field_name='factory_id', help_text='产地id')

    class Meta:
        model = ProductInfo
        fields = ('product_no', 'factory_id')


class ProductBatchingFilter(django_filters.rest_framework.FilterSet):
    factory_id = django_filters.NumberFilter(field_name='product_info__factory_id', help_text='产地id')
    stage_id = django_filters.NumberFilter(field_name='stage_id', help_text='段次id')
    stage_product_batch_no = django_filters.CharFilter(field_name='stage_product_batch_no', lookup_expr='icontains',
                                                       help_text='胶料编码')
    dev_type = django_filters.NumberFilter(field_name='dev_type_id', help_text='炼胶机类型id')

    class Meta:
        model = ProductBatching
        fields = ('factory_id', 'stage_id', 'stage_product_batch_no', 'dev_type')


class MaterialAttributeFilter(django_filters.rest_framework.FilterSet):
    material_no = django_filters.NumberFilter(field_name='material__material_no', help_text='原材料编码')

    class Meta:
        model = MaterialAttribute
        fields = ('material_no',)
