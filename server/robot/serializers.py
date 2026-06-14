from rest_framework import serializers
from .models import RobotAnalysis


class RobotAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for RobotAnalysis model — used in history detail views."""
    class Meta:
        model = RobotAnalysis
        fields = [
            'id', 'verdict', 'confidence_score', 'explanation',
            'key_evidence', 'created_at'
        ]