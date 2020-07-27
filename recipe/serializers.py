from rest_framework import serializers

from recipe.models import Material

COMMON_READ_ONLY_FIELDS = ('created_date', 'last_updated_date', 'delete_date',
                           'delete_flag', 'created_user', 'last_updated_user',
                           'delete_user')


class MaterialSerializer(serializers.ModelSerializer):
    material_type_name = serializers.CharField(source='material_type.global_name', read_only=True)
    packet_unit_name = serializers.CharField(source='packet_unit.global_name', read_only=True)
    created_user_name = serializers.CharField(source='created_user.username', read_only=True)

    def create(self, validated_data):
        validated_data['created_user'] = self.context['request'].user
        return super().create(validated_data)

    class Meta:
        model = Material
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS