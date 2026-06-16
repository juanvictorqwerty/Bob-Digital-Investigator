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
    Merges RobotAnalysis research data (research_report, research_queries) into
    the results JSON so the frontend has it when viewing from history.
    """
    image_url = serializers.SerializerMethodField()
    results = serializers.SerializerMethodField()

    class Meta:
        model = WebsearchResults
        fields = ['id', 'alias', 'query', 'image_url', 'results', 'created_at', 'updated_at']

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None

    def get_results(self, obj):
        results = obj.results or {}
        # Check if there's a RobotAnalysis record
        robot_analysis = getattr(obj, 'robot_analysis', None)
        if robot_analysis:
            # Ensure robot_analysis dict exists in results
            if 'robot_analysis' not in results or not isinstance(results['robot_analysis'], dict):
                results['robot_analysis'] = {}
            # Always inject the analysis id so the frontend can trigger research
            results['robot_analysis']['id'] = str(robot_analysis.id)
            # Inject verdict data from the RobotAnalysis record
            results['robot_analysis']['verdict'] = robot_analysis.verdict
            results['robot_analysis']['confidence'] = robot_analysis.confidence_score
            results['robot_analysis']['short_summary'] = robot_analysis.short_summary
            results['robot_analysis']['explanation'] = robot_analysis.explanation
            results['robot_analysis']['key_evidence'] = robot_analysis.key_evidence
            results['robot_analysis']['llm_used'] = bool(robot_analysis.llm_raw_response)
            # Only inject research data when it exists
            if robot_analysis.research_report:
                results['robot_analysis']['research_report'] = robot_analysis.research_report
                results['robot_analysis']['research_queries'] = robot_analysis.research_queries
        return results


class WebsearchResultAliasSerializer(serializers.ModelSerializer):
    """
    Serializer for updating only the alias field.
    """
    class Meta:
        model = WebsearchResults
        fields = ['alias']
