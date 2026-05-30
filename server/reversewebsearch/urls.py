from django.urls import path
from .views import ReverseImageSearchView

urlpatterns = [
    path('reverse-search/', ReverseImageSearchView.as_view(), name='reverse-search'),
]
