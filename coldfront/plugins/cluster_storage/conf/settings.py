from django.conf import settings as django_settings


ADMIN_EMAIL_LIST = getattr(
    django_settings, 'CLUSTER_STORAGE_ADMIN_EMAIL_LIST', [])


ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = getattr(
    django_settings, 'CLUSTER_STORAGE_ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED',
    False)
ELIGIBLE_PI_EMAIL_WHITELIST = getattr(
    django_settings, 'CLUSTER_STORAGE_ELIGIBLE_PI_EMAIL_WHITELIST', [])
