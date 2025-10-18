from django.conf import settings as django_settings


ADMIN_EMAIL_LIST = getattr(
    django_settings, 'CLUSTER_STORAGE_ADMIN_EMAIL_LIST', [])
