import uuid
from django.db import models


class RobotAnalysis(models.Model):
    VERDICT_CHOICES = [
        ('real', 'Real News'),
        ('fake', 'Fake News'),
        ('suspicious', 'Suspicious'),
        ('unconfirmed', 'Unconfirmed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    websearch_result = models.OneToOneField(
        'reversewebsearch.WebsearchResults',
        on_delete=models.CASCADE,
        related_name='robot_analysis'
    )

    verdict = models.CharField(max_length=20, choices=VERDICT_CHOICES)
    confidence_score = models.FloatField(help_text="0.0 (lowest) to 1.0 (highest confidence)")
    short_summary = models.CharField(
        max_length=300, blank=True, default="",
        help_text="One-sentence summary of the verdict"
    )
    explanation = models.TextField(help_text="Detailed reasoning from the LLM")
    key_evidence = models.JSONField(default=list, blank=True, help_text="List of key evidence items")
    research_queries = models.JSONField(
        default=list, blank=True,
        help_text="List of SearXNG search queries generated for this analysis"
    )
    research_report = models.JSONField(
        default=dict, blank=True,
        help_text="Research report with summary, sources, images, and videos from SearXNG"
    )
    llm_raw_response = models.JSONField(default=dict, blank=True, null=True)
    llm_prompt = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Robot Analyses"

    def __str__(self):
        return f"RobotAnalysis[{self.verdict}] for {self.websearch_result} — {self.confidence_score:.0%}"