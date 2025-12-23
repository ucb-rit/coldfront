"""Common utility views for ColdFront."""

from django.http import JsonResponse


def health_check(_request):
    """
    Health check endpoint for container orchestration.

    Returns a simple 200 OK to indicate the container is running.
    Database connectivity is validated by the application startup.

    Returns:
        200 OK with {"status": "healthy"}
    """
    return JsonResponse({
        'status': 'healthy'
    }, status=200)
