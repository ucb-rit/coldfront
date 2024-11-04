from django.conf import settings
from django.utils.module_loading import import_string


"""Methods relating to fetching of department data."""


__all__ = [
    'get_data_source',
    'fetch_departments',
    'fetch_departments_for_user',
]


def get_data_source(data_source=None, **kwds):
    klass = import_string(data_source or settings.DEPARTMENT_DATA_SOURCE)
    return klass(**kwds)


def fetch_departments(data_source=None):
    data_source = data_source or get_data_source()
    return data_source.fetch_departments()


def fetch_departments_for_user(user_data, data_source=None):
    data_source = data_source or get_data_source()
    return data_source.fetch_departments_for_user(user_data)
