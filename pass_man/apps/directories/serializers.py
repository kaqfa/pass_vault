"""
Serializers for Directory model.
"""

from rest_framework import serializers
from apps.directories.models import Directory

class DirectorySerializer(serializers.ModelSerializer):
    """Serializer for Directory model."""
    
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Directory.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Directory
        fields = [
            'id', 'name', 'description', 'parent', 'group',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True}
        }

class DirectoryTreeSerializer(serializers.ModelSerializer):
    """Serializer for Directory model with recursive children."""
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Directory
        fields = [
            'id', 'name', 'description', 'group', 'children'
        ]
        
    def get_children(self, obj):
        """Get children directories recursively."""
        children = obj.subdirectories.all()
        return DirectoryTreeSerializer(children, many=True).data
