import django_filters

from recipe.models import Material, ProductInfo, ProductBatching, MaterialAttribute, ZCMaterial


class MaterialFilter(django_filters.rest_framework.FilterSet):
    material_type_name = django_filters.CharFilter(field_name='material_type__global_name', help_text='原材料类别名称')
    material_type_id = django_filters.NumberFilter(field_name='material_type', help_text='原材料类别')
    # use_flag = django_filters.BooleanFilter(field_name='use_flag', help_text='是否使用')
    material_no = django_filters.CharFilter(field_name='material_no', help_text='原材料代码', lookup_expr='icontains')
    material_name = django_filters.CharFilter(field_name='material_name', help_text='原材料名称', lookup_expr='icontains')
    eq_material_no = django_filters.CharFilter(field_name='material_no', help_text='原材料代码(判等查询)')
    eq_material_name = django_filters.CharFilter(field_name='material_name', help_text='原材料名称(判等查询)')

    class Meta:
        model = Material
        fields = ('material_type_id', 'use_flag', 'material_no', 'material_name', 'material_type_name',
                  'eq_material_no', 'eq_material_name')


class ProductInfoFilter(django_filters.rest_framework.FilterSet):
    product_no = django_filters.CharFilter(field_name='product_no', help_text='胶料编码', lookup_expr='icontains')
    product_name = django_filters.CharFilter(field_name='product_name', help_text='胶料名称', lookup_expr='icontains')

    class Meta:
        model = ProductInfo
        fields = ('product_no', 'product_name')


class ProductBatchingFilter(django_filters.rest_framework.FilterSet):
    stage_product_batch_no = django_filters.CharFilter(field_name='stage_product_batch_no', lookup_expr='icontains',
                                                       help_text='胶料编码')
    used_type = django_filters.NumberFilter(field_name='used_type', help_text=""" (1, '编辑'), (2, '提交'), (3, '校对'), 
                                                                                  (4, '启用'), (5, '驳回'), (6, '废弃')
                                                                              """)

    class Meta:
        model = ProductBatching
        fields = ('stage_product_batch_no', 'used_type')


class MaterialAttributeFilter(django_filters.rest_framework.FilterSet):
    material_no = django_filters.CharFilter(field_name='material__material_no', help_text='原材料编码',
                                            lookup_expr='icontains')
    material_type = django_filters.CharFilter(field_name='material__material_type__global_name', help_text='原材料类型')

    class Meta:
        model = MaterialAttribute
        fields = ('material_no', 'material_type')


class ZCMaterialFilter(django_filters.rest_framework.FilterSet):
    material_no = django_filters.CharFilter(field_name='material_no', help_text='原材料编码', lookup_expr='icontains')
    material_name = django_filters.CharFilter(field_name='material_name', help_text='原材料名称', lookup_expr='icontains')

    class Meta:
        model = ZCMaterial
        fields = ('material_no', 'material_name')


class ERPMaterialFilter(django_filters.rest_framework.FilterSet):
    material_type_name = django_filters.CharFilter(field_name='material_type__global_name', help_text='原材料类别名称')
    material_type_id = django_filters.NumberFilter(field_name='material_type', help_text='原材料类别')
    material_no = django_filters.CharFilter(field_name='material_no', help_text='原材料代码', lookup_expr='icontains')
    material_name = django_filters.CharFilter(field_name='material_name', help_text='原材料名称', lookup_expr='icontains')
    for_short = django_filters.CharFilter(field_name='for_short', help_text='原材料简称', lookup_expr='icontains')

    class Meta:
        model = Material
        fields = ('material_type_id', 'use_flag', 'material_no',
                  'material_name', 'material_type_name', 'for_short')