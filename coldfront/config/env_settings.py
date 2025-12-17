from datetime import date

from django.core.exceptions import ImproperlyConfigured

import environ


# TODO: Organize settings.


# TODO: Add comments.
env = environ.Env()


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DJANGO__DEBUG', default=True)

SECRET_KEY = env('DJANGO__SECRET_KEY')

ALLOWED_HOSTS = env.list('DJANGO__ALLOWED_HOSTS')

PORTAL_NAME = env('HPCS__PORTAL_NAME')
PROGRAM_NAME_LONG = env('HPCS__PROGRAM_NAME_LONG')
PROGRAM_NAME_SHORT = env('HPCS__PROGRAM_NAME_SHORT')
PRIMARY_CLUSTER_NAME = env('HPCS__PRIMARY_CLUSTER_NAME')

CENTER_NAME = PROGRAM_NAME_SHORT + ' HPC Resources'
CENTER_USER_GUIDE = env('COLDFRONT__CENTER_USER_GUIDE')
CENTER_LOGIN_GUIDE = env('COLDFRONT__CENTER_LOGIN_GUIDE')
CENTER_HELP_EMAIL = env('COLDFRONT__CENTER_HELP_EMAIL')

CENTER_BASE_URL = env('COLDFRONT__CENTER_BASE_URL', default='')  # TODO: It's not getting picked up when set to "" in values.yaml. Not sure why.
CENTER_HELP_URL = CENTER_BASE_URL + '/help'
CENTER_PROJECT_RENEWAL_HELP_URL = CENTER_BASE_URL + '/help'

EMAIL_HOST = env('DJANGO__EMAIL_HOST')
EMAIL_PORT = env.int('DJANGO__EMAIL_PORT')
EMAIL_SUBJECT_PREFIX = env('DJANGO__EMAIL_SUBJECT_PREFIX')

EMAIL_ADMIN_LIST = env.list('COLDFRONT__EMAIL_ADMIN_LIST')
EMAIL_SENDER = env('COLDFRONT__EMAIL_SENDER')
EMAIL_TICKET_SYSTEM_ADDRESS = env('COLDFRONT__EMAIL_TICKET_SYSTEM_ADDRESS')
EMAIL_DIRECTOR_EMAIL_ADDRESS = env('COLDFRONT__EMAIL_DIRECTOR_EMAIL_ADDRESS')
EMAIL_PROJECT_REVIEW_CONTACT = env('COLDFRONT__EMAIL_PROJECT_REVIEW_CONTACT')
EMAIL_DEVELOPMENT_EMAIL_LIST = env.list(
    'COLDFRONT__EMAIL_DEVELOPMENT_EMAIL_LIST')
EMAIL_OPT_OUT_INSTRUCTION_URL = CENTER_BASE_URL + '/optout'
EMAIL_SIGNATURE = env('COLDFRONT__EMAIL_SIGNATURE')

EMAIL_FROM = env('HPCS__EMAIL_FROM')
EMAIL_ADMIN = env('HPCS__EMAIL_ADMIN')
DEFAULT_FROM_EMAIL = EMAIL_FROM

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env('DJANGO__DATABASES_DEFAULT_NAME'),
        'USER': env('DJANGO__DATABASES_DEFAULT_USER'),
        'PASSWORD': env('DJANGO__DATABASES_DEFAULT_PASSWORD'),
        'HOST': env('DJANGO__DATABASES_DEFAULT_HOST'),
        'PORT': env('DJANGO__DATABASES_DEFAULT_PORT'),
    },
}


# TODO: These should be streamed to a persistent, centralized location.
LOG_PATH = env('HPCS__LOG_PATH')
API_LOG_PATH = env('HPCS__API_LOG_PATH')

STREAM_LOGS_TO_STDOUT = env.bool('HPCS__STREAM_LOGS_TO_STDOUT', default=True)

# TODO: Ideally, come up with an approach wherein admins may subscribe to
#  individual types of events.
# A list of admin email addresses to CC when certain requests are approved.
REQUEST_APPROVAL_CC_LIST = env.list('HPCS__REQUEST_APPROVAL_CC_LIST')
# A list of admin email addresses to notify when a project-user removal request
# is processed.
PROJECT_USER_REMOVAL_REQUEST_PROCESSED_EMAIL_ADMIN_LIST = env.list(
    'HPCS__PROJECT_USER_REMOVAL_REQUEST_PROCESSED_EMAIL_ADMIN_LIST')



# A setting that, when true, allows all jobs, bypassing all checks at job
# submission time.
ALLOW_ALL_JOBS = env.bool('HPCS__ALLOW_ALL_JOBS', default=False)



# Extra apps to be included.
EXTRA_EXTRA_APPS = []
# Extra middleware to be included.
EXTRA_EXTRA_MIDDLEWARE = []

#------------------------------------------------------------------------------
# Django Cache settings
#------------------------------------------------------------------------------

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': (
            f'redis://{env("HPCS__REDIS_HOST")}:{env.int("HPCS__REDIS_PORT")}/'
            f'{env.int("HPCS__REDIS_DB")}'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'DB': env.int('HPCS__REDIS_DB'),
            'PASSWORD': env('HPCS__REDIS_PASSWORD', default=''),
        },
        'TIMEOUT': env.int('DJANGO__CACHES_DEFAULT_TIMEOUT')
    }
}

#------------------------------------------------------------------------------
# BRC Vector Settings
#------------------------------------------------------------------------------

# The username of the user to set as the PI for all Vector projects.
VECTOR_PI_USERNAME = env('HPCS__VECTOR_PI_USERNAME')

# The name of the Savio project to which all Vector users are given access.
SAVIO_PROJECT_FOR_VECTOR_USERS = env('HPCS__SAVIO_PROJECT_FOR_VECTOR_USERS')

#------------------------------------------------------------------------------
# File Storage Settings
#------------------------------------------------------------------------------

# An absolute path to the local filesystem directory holding user-uploaded
# files.
if env('DJANGO__MEDIA_ROOT', default=None) is not None:
    MEDIA_ROOT = env('DJANGO__MEDIA_ROOT')

# A dict denoting where and how user-uploaded files (currently only MOUs) should
# be stored.
FILE_STORAGE = env.json('HPCS__FILE_STORAGE', default=None)
if FILE_STORAGE is not None:
    if FILE_STORAGE['backend'] == 'google_drive':
        EXTRA_EXTRA_APPS += [
            'gdstorage'
        ]

        # TODO: Store the JSON as a secret and then read it from the environment.
        # An absolute path to a private JSON key file for a Google service account.
        GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE = env(
            'DJANGO_GOOGLEDRIVE_STORAGE__GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE')

        # The base path files will be uploaded to in Google Drive. (E.g., if the
        # root is '/a/b/', and the specified upload path is 'c/file.txt', the file
        # will be uploaded to '/a/b/c/file.txt'. The base path is ignored if the
        # specified upload path is absolute.
        GOOGLE_DRIVE_STORAGE_MEDIA_ROOT = env(
            'DJANGO_GOOGLEDRIVE_STORAGE__GOOGLE_DRIVE_STORAGE_MEDIA_ROOT')

#------------------------------------------------------------------------------
# Billing settings
#------------------------------------------------------------------------------

# TODO: Handle for LRC.
# TODO: Encapsulate the backend and dict into one parent dict.
# TODO: Make a new feature flag for whether billing should be enabled.
# TODO: Update the oracle backend to take the settings as a parameter.
# TODO: Use an alias for the backend instead of the full path?

if env('HPCS__BILLING_VALIDATOR_BACKEND', default=None) is not None:
    BILLING_VALIDATOR_BACKEND = env('HPCS__BILLING_VALIDATOR_BACKEND')

    # TODO: This is a temporary approach. Use an alias moving forward.
    if 'oracle' in BILLING_VALIDATOR_BACKEND:
        ORACLE_BILLING_DB = {
            'dsn': env('HPCS__ORACLE_BILLING_DB_DSN'),
            'user': env('HPCS__ORACLE_BILLING_DB_USER'),
            'password': env('HPCS__ORACLE_BILLING_DB_PASSWORD'),
        }

#------------------------------------------------------------------------------
# Renewal Survey settings
#------------------------------------------------------------------------------

RENEWAL_SURVEY = env.json('HPCS__RENEWAL_SURVEY', default={})

#------------------------------------------------------------------------------
# SSL settings
#------------------------------------------------------------------------------

# Use a secure cookie for the session cookie (HTTPS only).
SESSION_COOKIE_SECURE = env.bool('DJANGO__SESSION_COOKIE_SECURE', default=False)

#------------------------------------------------------------------------------
# Sentry settings
#------------------------------------------------------------------------------

# Configure Sentry.

if env('HPCS__SENTRY_DSN', default=''):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import ignore_logger

    sentry_sdk.init(
        dsn=env('HPCS__SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        sample_rate=0.1,
        traces_sample_rate=0.001,
        send_default_pii=True)

    # Ignore noisy loggers.
    ignore_logger('coldfront.api')
    ignore_logger('coldfront.core.utils.middleware')

#------------------------------------------------------------------------------
# Django All-Auth settings
#------------------------------------------------------------------------------

# TODO: This isn't really a Django All-Auth setting...

CILOGON_APP_CLIENT_ID = env('HPCS__CILOGON_APP_CLIENT_ID')
CILOGON_APP_SECRET = env('HPCS__CILOGON_APP_SECRET')

#------------------------------------------------------------------------------
# django-constance settings
#------------------------------------------------------------------------------

CONSTANCE_CONFIG = {
    'FEEDBACK_FORM_URL': ('', 'The URL to the feedback form.'),
    'DOCS_GETTING_HELP_URL': (
        '', 'The URL to the documentation page on getting help.'),
    'LAUNCH_DATE': (date(1970, 1, 1), 'The date the portal was launched.'),
}
CONSTANCE_REDIS_CONNECTION = {
    'host': env('HPCS__REDIS_HOST'),
    'port': env.int('HPCS__REDIS_PORT'),
    'db': env.int('HPCS__REDIS_DB'),
    'password': env('HPCS__REDIS_PASSWORD', default=''),
}

#------------------------------------------------------------------------------
# django-q settings
#------------------------------------------------------------------------------

Q_CLUSTER = {
    'redis': {
        'host': env('HPCS__REDIS_HOST'),
        'port': env.int('HPCS__REDIS_PORT'),
        'db': env.int('HPCS__REDIS_DB'),
        'password': env('HPCS__REDIS_PASSWORD', default=''),
    }
}

#------------------------------------------------------------------------------
# django-flags settings
#------------------------------------------------------------------------------

FLAGS = {
    'ALLOCATION_RENEWAL_FOR_NEXT_PERIOD_REQUESTABLE': [
        {
            'condition': 'during month',
            'value': env(
                'DJANGO_FLAGS__ALLOCATION_RENEWAL_FOR_NEXT_PERIOD_REQUESTABLE_VALUE'),
        },
    ],
    'BASIC_AUTH_ENABLED': [
        {
            'condition': 'boolean',
            'value': env.bool(
                'DJANGO_FLAGS__BASIC_AUTH_ENABLED_VALUE', default=False),
        },
    ],
    'BRC_ONLY': [
        {
            'condition': 'boolean',
            'value': env.bool(
                'DJANGO_FLAGS__BRC_ONLY_VALUE', default=False),
        },
    ],
    'HARDWARE_PROCUREMENTS_ENABLED': [
        {
            'condition': 'app installed',
            'value': 'coldfront.plugins.hardware_procurements',
        },
    ],
    'LINK_LOGIN_ENABLED': [
        {
            'condition': 'boolean',
            'value': env.bool(
                'DJANGO_FLAGS__LINK_LOGIN_ENABLED_VALUE', default=False),
        },
    ],
    'LRC_ONLY': [
        {
            'condition': 'boolean',
            'value': env.bool(
                'DJANGO_FLAGS__LRC_ONLY_VALUE', default=False),
        },
    ],
    'MOU_GENERATION_ENABLED': [
        {
            'condition': 'boolean',
            'value': env.bool(
                'DJANGO_FLAGS__MOU_GENERATION_ENABLED_VALUE', default=False),
        },
    ],
    'MULTIPLE_EMAIL_ADDRESSES_ALLOWED': [
        {
            'condition': 'boolean',
            'value': env.bool(
                'DJANGO_FLAGS__MULTIPLE_EMAIL_ADDRESSES_ALLOWED_VALUE',
                default=False),
        },
    ],
    'RENEWAL_SURVEY_ENABLED': [
        {
            'condition': 'boolean',
            'value': env.bool(
                'DJANGO_FLAGS__RENEWAL_SURVEY_ENABLED_VALUE', default=False),
        },
    ],
    'SECURE_DIRS_REQUESTABLE': [
        {
            'condition': 'boolean',
            'value': env.bool(
                'DJANGO_FLAGS__SECURE_DIRS_REQUESTABLE_VALUE', default=False),
        },
    ],
    'SERVICE_UNITS_PURCHASABLE': [
        {
            'condition': 'boolean',
            'value': env.bool(
                'DJANGO_FLAGS__SERVICE_UNITS_PURCHASABLE_VALUE', default=False),
        },
    ],
    'SSO_ENABLED': [
        {
            'condition': 'boolean',
            'value': env.bool('DJANGO_FLAGS__SSO_ENABLED_VALUE', default=False),
        },
    ],
    'USER_DEPARTMENTS_ENABLED': [
        {
            'condition': 'app installed',
            'value': 'coldfront.plugins.departments',
        },
    ],
}


# Enforce that boolean flags are consistent with each other.
if not (FLAGS['BRC_ONLY'][0]['value'] ^ FLAGS['LRC_ONLY'][0]['value']):
    raise ImproperlyConfigured(
        'Exactly one of BRC_ONLY, LRC_ONLY should be enabled.')
if not (
        FLAGS['BASIC_AUTH_ENABLED'][0]['value'] ^
        FLAGS['SSO_ENABLED'][0]['value']):
    raise ImproperlyConfigured(
        'Exactly one of BASIC_AUTH_ENABLED, SSO_ENABLED should be enabled.')
if (not FLAGS['SSO_ENABLED'][0]['value'] and
        FLAGS['LINK_LOGIN_ENABLED'][0]['value']):
    raise ImproperlyConfigured(
        'LINK_LOGIN_ENABLED should only be enabled when SSO_ENABLED is '
        'enabled.')

#------------------------------------------------------------------------------
# Plugin: departments
#------------------------------------------------------------------------------

if env.bool('HPCS__PLUGIN_DEPARTMENTS_ENABLED', default=False):
    EXTRA_EXTRA_APPS += [
        'coldfront.plugins.departments'
    ]

    DEPARTMENTS_DEPARTMENT_DISPLAY_NAME = env(
        'HPCS__PLUGIN_DEPARTMENTS_DEPARTMENT_DISPLAY_NAME')

    def get_departments_data_source(short_name):
        """Return the dotted path to the class to use as the data source
        backend for departments, based on the given short name. Raise an
        ImproperlyConfigured exception if the short name is
        unexpected."""
        prefix = 'coldfront.plugins.departments.utils.data_sources.backends'
        if short_name == 'calnet_ldap':
            return f'{prefix}.calnet_ldap.CalNetLdapDataSourceBackend'
        elif short_name == 'dummy':
            return f'{prefix}.dummy.DummyDataSourceBackend'
        else:
            raise ImproperlyConfigured('Unknown departments data source.')

    DEPARTMENTS_DEPARTMENT_DATA_SOURCE = get_departments_data_source(
        env('HPCS__PLUGIN_DEPARTMENTS_DEPARTMENT_DATA_SOURCE'))
