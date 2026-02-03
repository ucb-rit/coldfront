from django.conf import settings


def get_email_admin_notification_recipients(domain, event):
    """Return the list of administrator email addresses to notify for
    the given domain and event type. Return the empty list if either the
    domain or the event is not "registered"."""
    return settings.EMAIL_ADMIN_NOTIFICATION_RECIPIENTS.get(
        domain, {}).get(event, [])
