from coldfront.plugins.analytics.permissions import user_can_view_analytics


def analytics_nav_visibility(request):
    """Inject ANALYTICS_VISIBLE into every template context.

    Delegates to user_can_view_analytics — the single source of truth for
    who may access analytics pages.
    """
    return {"ANALYTICS_VISIBLE": user_can_view_analytics(request.user)}
