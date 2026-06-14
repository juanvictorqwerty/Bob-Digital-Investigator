# reversewebsearch/serializers.py
from rest_framework import serializers
from .models import WebsearchResults


class ReverseImageSearchSerializer(serializers.ModelSerializer):
    """
    Serializer for reverse image search requests.
    Uses ModelSerializer to render individual fields in DRF browsable API.
    """
    image_url = serializers.URLField(
        required=False, 
        allow_null=True,
        help_text="URL of the image to search (provide this OR upload an image file)"
    )
    
    image = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Upload an image file (provide this OR an image_url)"
    )
    
    class Meta:
        model = WebsearchResults
        fields = ['image_url', 'image', 'query']
        extra_kwargs = {
            'query': {
                'required': False,
                'allow_blank': True,
                'help_text': "Optional search query to refine results"
            }
        }

    def validate(self, data):
        image_url = data.get('image_url')
        image = data.get('image')
        
        if not image_url and not image:
            raise serializers.ValidationError(
                {"non_field_errors": ["Either image_url or image must be provided."]}
            )
        if image_url and image:
            raise serializers.ValidationError(
                {"non_field_errors": ["Provide either image_url or image, not both."]}
            )
        return data


class WebsearchResultListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing history items - lightweight, no heavy results data.
    """
    image_url = serializers.SerializerMethodField()
    image_thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = WebsearchResults
        fields = ['id', 'alias', 'query', 'image_url', 'image_thumbnail', 'created_at']

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None

    def get_image_thumbnail(self, obj):
        if obj.image:
            # Cloudinary can auto-transform for thumbnails
            return obj.image.build_url(width=80, height=80, crop="fill")
        return None


class WebsearchResultDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for full detail of a search result including all results data.
    """
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = WebsearchResults
        fields = ['id', 'alias', 'query', 'image_url', 'results', 'created_at', 'updated_at']

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


class WebsearchResultAliasSerializer(serializers.ModelSerializer):
    """
    Serializer for updating only the alias field.
    """
    class Meta:
        model = WebsearchResults
        fields = ['alias']
