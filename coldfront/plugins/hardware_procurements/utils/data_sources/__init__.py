from django.utils.module_loading import import_string

from coldfront.plugins.hardware_procurements.conf import settings


"""Methods relating to fetching of hardware procurement data."""


__all__ = [
    'get_data_source',
    'fetch_hardware_procurements',
]


def get_data_source(data_source=None, **kwds):
    klass = import_string(data_source or settings.DATA_SOURCE)
    return klass(**kwds)


def fetch_hardware_procurements(data_source=None, user_data=None, status=None):
    data_source = data_source or get_data_source()
    return data_source.fetch_hardware_procurements(
        user_data=user_data, status=status)
