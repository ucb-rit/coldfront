from django.conf import settings as django_settings


DEPARTMENT_DISPLAY_NAME = getattr(
    django_settings, 'DEPARTMENTS_DEPARTMENT_DISPLAY_NAME', 'Departments')

DEPARTMENT_DATA_SOURCE = getattr(
    django_settings, 'DEPARTMENTS_DEPARTMENT_DATA_SOURCE',
    'coldfront.plugins.departments.utils.data_sources.backends.dummy.DummyDataSourceBackend')
