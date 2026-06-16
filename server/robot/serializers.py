from rest_framework import serializers
from .models import RobotAnalysis


class RobotAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for RobotAnalysis model — used in history detail views."""
    class Meta:
        model = RobotAnalysis
        fields = [
            'id', 'verdict', 'confidence_score', 'short_summary',
            'explanation', 'key_evidence', 'research_queries',
            'research_report', 'created_at'
        ]
