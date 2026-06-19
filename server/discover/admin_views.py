"""
Admin views for Prometheus/Grafana integration.
Provides raw metrics endpoints for debugging, and pointing to Grafana.
"""
import requests
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.conf import settings


@staff_member_required
def metrics_backend_raw(request):
    """Return raw backend Prometheus metrics as text for debugging."""
    try:
        backend_url = f"{request.scheme}://{request.get_host()}/metrics"
        resp = requests.get(backend_url, timeout=5)
        if resp.status_code == 200:
            return JsonResponse({"metrics": resp.text, "error": None})
        return JsonResponse({"metrics": "", "error": f"Status {resp.status_code}"})
    except Exception as e:
        return JsonResponse({"metrics": "", "error": str(e)})


@staff_member_required
def metrics_frontend_raw(request):
    """Return raw frontend Prometheus metrics as text for debugging."""
    frontend_url = getattr(settings, 'FRONTEND_URL', '').rstrip('/')
    if not frontend_url:
        frontend_url = "http://localhost:3000"
    try:
        resp = requests.get(f"{frontend_url}/api/metrics", timeout=5)
        if resp.status_code == 200:
            return JsonResponse({"metrics": resp.text, "error": None})
        return JsonResponse({"metrics": "", "error": f"Status {resp.status_code}"})
    except Exception as e:
        return JsonResponse({"metrics": "", "error": str(e)})