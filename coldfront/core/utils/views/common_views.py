"""Common utility views for ColdFront."""

from django.http import JsonResponse
from django.db import connection


def health_check(_request):
    """
    Health check endpoint for container orchestration.

    Checks database connectivity and returns appropriate status.

    Returns:
        200 OK with {"status": "healthy"} if database is accessible
        500 Internal Server Error with error details if database is unavailable
    """
    # Check database connectivity
    try:
        connection.ensure_connection()
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected'
        }, status=200)
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'database': f'error: {str(e)}'
        }, status=500)

    # TODO: Add Redis connectivity check if needed.
