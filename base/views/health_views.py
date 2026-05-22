from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health_check(request):
    """Lightweight ping for Render cold-start warmup and uptime checks."""
    return Response({"status": "ok"})
