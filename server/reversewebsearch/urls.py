from django.urls import path
from .views import ReverseImageSearchView, ReverseSearchProgressView

urlpatterns = [
    path('reverse-search/', ReverseImageSearchView.as_view(), name='reverse-search'),
    path('reverse-search/progress/<str:task_id>/', ReverseSearchProgressView.as_view(), name='reverse-search-progress'),
]
