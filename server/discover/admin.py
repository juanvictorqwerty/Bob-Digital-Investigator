from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from .admin_views import metrics_backend_raw, metrics_frontend_raw


# Use custom admin index template with monitoring links
admin.site.index_template = 'admin/discover_admin_index.html'


# Helper to inject monitoring links into admin context
original_each_context = admin.site.each_context


def patched_each_context(self, request):
    context = original_each_context(request)
    context['grafana_url'] = 'http://localhost:3001'
    context['prometheus_url'] = 'http://localhost:9090'
    return context


admin.site.each_context = patched_each_context.__get__(admin.site, type(admin.site))


# Add custom admin URLs for raw metrics endpoints
# We need to use admin_view() for staff_member_required + permissions
original_get_urls = admin.site.get_urls


def patched_get_urls(self):
    urls = original_get_urls()
    custom_urls = [
        path('metrics/backend-raw/',
             self.admin_view(metrics_backend_raw),
             name='metrics-backend-raw'),
        path('metrics/frontend-raw/',
             self.admin_view(metrics_frontend_raw),
             name='metrics-frontend-raw'),
    ]
    return custom_urls + urls


admin.site.get_urls = patched_get_urls.__get__(admin.site, type(admin.site))