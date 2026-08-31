def user_can_view_analytics(user):
    """Return True if user may access analytics views.

    Grants access to superusers, staff, and members of the
    'analytics_viewers' group.  Anonymous users always return False.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name="analytics_viewers").exists()
