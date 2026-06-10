from django.urls import path
from .views import (
    ReverseImageSearchView,
    ReverseSearchProgressView,
    HistoryListView,
    HistoryDetailView,
    HistoryAliasUpdateView,
)

urlpatterns = [
    path('reverse-search/', ReverseImageSearchView.as_view(), name='reverse-search'),
    path('reverse-search/progress/<str:task_id>/', ReverseSearchProgressView.as_view(), name='reverse-search-progress'),
    path('history/', HistoryListView.as_view(), name='history-list'),
    path('history/<uuid:pk>/', HistoryDetailView.as_view(), name='history-detail'),
    path('history/<uuid:pk>/alias/', HistoryAliasUpdateView.as_view(), name='history-alias-update'),
]
