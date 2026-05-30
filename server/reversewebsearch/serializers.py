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
    
    class Meta:
        model = WebsearchResults
        fields = ['image_url', 'image', 'query']
        extra_kwargs = {
            'image': {
                'required': False,
                'allow_null': True,
                'help_text': "Upload an image file (provide this OR an image_url)"
            },
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