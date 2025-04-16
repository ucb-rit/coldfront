from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured


DATA_SOURCE_CONFIG = getattr(
    django_settings, 'HARDWARE_PROCUREMENTS_CONFIG', {})

if not DATA_SOURCE_CONFIG:
    raise ImproperlyConfigured(
        'No hardware procurements configuration provided.')
