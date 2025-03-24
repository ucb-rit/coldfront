from django.conf import settings as django_settings


# TODO: Comment
DATA_SOURCE = getattr(
    django_settings,
    'HARDWARE_PROCUREMENTS_DATA_SOURCE',
    # TODO: Define this.
    'coldfront.plugins.hardware_procurements.utils.data_sources.backends.dummy.DummyDataSourceBackend')


# TODO: Comment
# TODO: Pull this from parent settings.
DATA_SOURCE_CONFIG = {
    'sheet_id': '',
    'sheet_tab': '',
    'sheet_columns': {
        'pi_email_col': '',
        'pi_name_col': '',
        'poc_email_col': '',
        'poc_name_col': '',
        'hardware_type_col': '',
        'status_col': '',
        'hardware_specification_details_col': '',
    },
}
