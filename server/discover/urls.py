from django.urls import path
from .views import GenerateResearchView, ResearchProgressView

urlpatterns = [
    path('discover/generate/', GenerateResearchView.as_view(), name='discover-generate'),
    path('discover/progress/<str:task_id>/', ResearchProgressView.as_view(), name='discover-progress'),
]