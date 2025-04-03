from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured


# TODO: Comment
DATA_SOURCE = getattr(
    django_settings,
    'HARDWARE_PROCUREMENTS_DATA_SOURCE',
    # TODO: Define this.
    'coldfront.plugins.hardware_procurements.utils.data_sources.backends.dummy.DummyDataSourceBackend')


# TODO: Comment
DATA_SOURCE_CONFIG = getattr(
    django_settings, 'HARDWARE_PROCUREMENTS_CONFIG', {})

if not DATA_SOURCE_CONFIG:
    raise ImproperlyConfigured(
        'No hardware procurements configuration provided.')
