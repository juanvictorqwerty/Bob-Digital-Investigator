import uuid
from django.db import models

class WebsearchResults(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey('authentication.CustomUser', on_delete=models.CASCADE)
    
    # 1. Removed relative "../" path. Files will go to the "reversewebsearch" folder inside your MinIO bucket.
    image = models.ImageField(upload_to='reversewebsearch/')
    
    query = models.CharField(max_length=255)
    results = models.JSONField(default=dict, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Websearch Results"

    def __str__(self):
        return f"Query: {self.query} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
