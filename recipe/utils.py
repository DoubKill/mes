from basics.models import GlobalCode


def get_mixed(instance):
    """返回符合条件的对搭物料  instance: 配方实例"""
    stages = list(GlobalCode.objects.filter(delete_flag=False, global_type__use_flag=1, use_flag=1,
                                            global_type__type_name='胶料段次').values_list('global_name', flat=True))
    handle_stages = list(map(lambda x: f'-{x}-', stages))
    detail_names = instance.batching_details.filter(type=1, delete_flag=False).order_by('id')
    f_s, f_stage = [], None
    for s_name in detail_names:
        name_list = s_name.material.material_name.split('-')
        if len(name_list) == 4 and f'-{name_list[1]}-' in handle_stages:
            f_s.append(s_name)
            f_stage = name_list[1]
    # 胶料中含有段次信息的物料不能超过1个
    f_s = f_s[0] if len(f_s) == 1 else []
    return f_s, f_stage
