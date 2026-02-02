import os

from datetime import date

from django.core.exceptions import ImproperlyConfigured

import environ


# Try to read .env from multiple locations in order
env = environ.Env()
env_file_paths = [
    os.path.join(os.path.dirname(__file__), '.env'),
    '/etc/coldfront/.env',
]
for env_file in env_file_paths:
    if os.path.exists(env_file):
        env.read_env(env_file)
        break


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

CENTER_BASE_URL = env('COLDFRONT__CENTER_BASE_URL', default='')
CENTER_HELP_URL = CENTER_BASE_URL + '/help'
CENTER_PROJECT_RENEWAL_HELP_URL = CENTER_BASE_URL + '/help'

EMAIL_HOST = env('DJANGO__EMAIL_HOST')
EMAIL_PORT = env.int('DJANGO__EMAIL_PORT')
EMAIL_SUBJECT_PREFIX = env('DJANGO__EMAIL_SUBJECT_PREFIX')
# A list of admin email addresses to be notified about new requests and other
# events.
# Note: This has been replaced by EMAIL_ADMIN_NOTIFICATION_RECIPIENTS. The
# setting is retained for base Coldfront compatibility.
EMAIL_ADMIN_LIST = []
# A nested dict mapping domain -> event -> list of recipient admin email
# addresses. Example:
# {
#   "new_project_requests": {
#     "agreement_uploaded": ["admin@example.com"]
#   }
# }
EMAIL_ADMIN_NOTIFICATION_RECIPIENTS = env.json(
    'HPCS__EMAIL_ADMIN_NOTIFICATION_RECIPIENTS', default={})
EMAIL_SENDER = env('COLDFRONT__EMAIL_SENDER')
EMAIL_TICKET_SYSTEM_ADDRESS = env('COLDFRONT__EMAIL_TICKET_SYSTEM_ADDRESS')
EMAIL_DIRECTOR_EMAIL_ADDRESS = env('COLDFRONT__EMAIL_DIRECTOR_EMAIL_ADDRESS')
EMAIL_PROJECT_REVIEW_CONTACT = env('COLDFRONT__EMAIL_PROJECT_REVIEW_CONTACT')
EMAIL_DEVELOPMENT_EMAIL_LIST = env.list(
    'COLDFRONT__EMAIL_DEVELOPMENT_EMAIL_LIST')
EMAIL_OPT_OUT_INSTRUCTION_URL = CENTER_BASE_URL + '/optout'
EMAIL_SIGNATURE = env('COLDFRONT__EMAIL_SIGNATURE').replace('\\n', '\n')

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

LOG_PATH = env('HPCS__LOG_PATH')
API_LOG_PATH = env('HPCS__API_LOG_PATH')

STREAM_LOGS_TO_STDOUT = env.bool('HPCS__STREAM_LOGS_TO_STDOUT', default=True)

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

_cache_backend_short = env('DJANGO__CACHES_DEFAULT_BACKEND_SHORT', default='dummy')

if _cache_backend_short == 'redis':
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
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
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
FILE_STORAGE = env.json('HPCS__FILE_STORAGE')

#------------------------------------------------------------------------------
# Billing settings
#------------------------------------------------------------------------------

# TODO: Encapsulate the backend and dict into one parent dict.
# TODO: Make a new feature flag for whether billing should be enabled (instead
#  of LRC_ONLY).
# TODO: Use an alias for the backend instead of the full path.

if (env.bool('DJANGO_FLAGS__LRC_ONLY_VALUE') and
        env('HPCS__BILLING_VALIDATOR_BACKEND', default=None) is not None):

    # The class to use for validating billing IDs.
    BILLING_VALIDATOR_BACKEND = env('HPCS__BILLING_VALIDATOR_BACKEND')

    if 'oracle' in BILLING_VALIDATOR_BACKEND:
        # Credentials for the Oracle billing database.
        ORACLE_BILLING_DB = {
            'dsn': env('HPCS__ORACLE_BILLING_DB_DSN'),
            'user': env('HPCS__ORACLE_BILLING_DB_USER'),
            'password': env('HPCS__ORACLE_BILLING_DB_PASSWORD'),
        }

#------------------------------------------------------------------------------
# Renewal Survey settings
#------------------------------------------------------------------------------

RENEWAL_SURVEY = env.json('HPCS__RENEWAL_SURVEY')

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
# CILogon settings
#------------------------------------------------------------------------------

CILOGON_APP_CLIENT_ID = env('HPCS__CILOGON_APP_CLIENT_ID')
CILOGON_APP_SECRET = env('HPCS__CILOGON_APP_SECRET')

#------------------------------------------------------------------------------
# django-constance settings
#------------------------------------------------------------------------------

if env.bool('HPCS__DJANGO_CONSTANCE_ENABLED', default=False):

    CONSTANCE_CONFIG = {
        'FEEDBACK_FORM_URL': ('', 'The URL to the feedback form.'),
        'DOCS_GETTING_HELP_URL': (
            '', 'The URL to the documentation page on getting help.'),
        'LAUNCH_DATE': (date(1970, 1, 1), 'The date the portal was launched.'),
        'ANNOUNCEMENTS_ALERT_HTML': (
            '',
            'The HTML contents of an announcements alert on the home page.'),
    }

    CONSTANCE_REDIS_CONNECTION = {
        'host': env('HPCS__REDIS_HOST'),
        'port': env.int('HPCS__REDIS_PORT'),
        'db': env.int('HPCS__REDIS_DB'),
        'password': env('HPCS__REDIS_PASSWORD', default=''),
    }

#------------------------------------------------------------------------------
# django-debug-toolbar settings
#------------------------------------------------------------------------------

if env.bool('HPCS__ENABLE_DJANGO_DEBUG_TOOLBAR', default=False):

    EXTRA_EXTRA_APPS += [
        'debug_toolbar'
    ]

    EXTRA_EXTRA_MIDDLEWARE += [
        'debug_toolbar.middleware.DebugToolbarMiddleware'
    ]

    # IP addresses that can view the django debug toolbar.
    INTERNAL_IPS = env.list(
        'HPCS__DJANGO_DEBUG_TOOLBAR_INTERNAL_IPS', default=[])

    if DEBUG:
        # For Docker support
        import socket
        hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
        INTERNAL_IPS = [ip[: ip.rfind('.')] + '.1' for ip in ips] + ['10.0.2.2']

    DISABLE_PANELS = {
        'debug_toolbar.panels.history.HistoryPanel',
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',
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
    'FACULTY_STORAGE_ALLOCATIONS_ENABLED': [
        {
            'condition': 'app installed',
            'value': 'coldfront.plugins.faculty_storage_allocations'
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
    DEPARTMENTS_DEPARTMENT_DATA_SOURCE = env(
        'HPCS__PLUGIN_DEPARTMENTS_DEPARTMENT_DATA_SOURCE')

#------------------------------------------------------------------------------
# Plugin: faculty_storage_allocations
#------------------------------------------------------------------------------

if env.bool('HPCS__PLUGIN_FACULTY_STORAGE_ALLOCATIONS_ENABLED', default=False):

    EXTRA_EXTRA_APPS += [
        'coldfront.plugins.faculty_storage_allocations'
    ]

    # A dict mapping event -> list of recipient admin email addresses. Example:
    # {
    #   "request_created": ["admin@example.com"]
    # }
    FACULTY_STORAGE_ALLOCATIONS_EMAIL_ADMIN_NOTIFICATION_RECIPIENTS = env.json(
        'HPCS__PLUGIN_FACULTY_STORAGE_ALLOCATIONS_EMAIL_ADMIN_NOTIFICATION_RECIPIENTS',
        default={})
    # If enabled, a list of email addresses of PIs that are eligible to request
    # storage.
    FACULTY_STORAGE_ALLOCATIONS_ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = env.bool(
        'HPCS__PLUGIN_FACULTY_STORAGE_ALLOCATIONS_ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED',
        default=False)
    FACULTY_STORAGE_ALLOCATIONS_ELIGIBLE_PI_EMAIL_WHITELIST = env.list(
        'HPCS__PLUGIN_FACULTY_STORAGE_ALLOCATIONS_ELIGIBLE_PI_EMAIL_WHITELIST')

#------------------------------------------------------------------------------
# Plugin: hardware_procurements
#------------------------------------------------------------------------------

if env.bool('HPCS__PLUGIN_HARDWARE_PROCUREMENTS_ENABLED', default=False):

    EXTRA_EXTRA_APPS += [
        'coldfront.plugins.hardware_procurements'
    ]

    HARDWARE_PROCUREMENTS_CONFIG = env.json(
        'HPCS__HARDWARE_PROCUREMENTS_CONFIG', default={})

#------------------------------------------------------------------------------
# django-googledrive-storage settings
#------------------------------------------------------------------------------

if FILE_STORAGE['backend'] == 'google_drive':

    EXTRA_EXTRA_APPS += [
        'gdstorage',
    ]

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
# django-q settings
#------------------------------------------------------------------------------

_django_q_job_queue_mode = env('HPCS__DJANGO_Q_JOB_QUEUE_MODE', default='sync')

if _django_q_job_queue_mode == 'async':
    Q_CLUSTER = {
        'redis': {
            'host': env('HPCS__REDIS_HOST'),
            'port': env.int('HPCS__REDIS_PORT'),
            'db': env.int('HPCS__REDIS_DB'),
            'password': env('HPCS__REDIS_PASSWORD', default=''),
        },
        # No task may run longer than 'timeout' seconds.
        # Tasks that time out are retried after 'retry' seconds since the task
        # originally began.
        # 'retry' must be greater than 'timeout'.
        # This configuration assumes that no task runs longer than 24 hours. If
        # it times out, it will be retried a day after the timeout.
        # Docs: https://django-q2.readthedocs.io/en/master/configure.html#retry
        'retry': 2 * 24 * 60 * 60,
        'timeout': 24 * 60 * 60,
    }
else:
    Q_CLUSTER = {
        'sync': True,
        'timeout': 24 * 60 * 60,
    }

#------------------------------------------------------------------------------
# django-maintenance-mode settings
#------------------------------------------------------------------------------

# Note: This should be the last-defined middleware.
EXTRA_EXTRA_MIDDLEWARE += [
    'maintenance_mode.middleware.MaintenanceModeMiddleware',
]

if env.bool('HPCS__ENABLE_MAINTENANCE_MODE', default=False):
    MAINTENANCE_MODE = True
    # In maintenance mode, users may still log in by manually accessing the
    # login URLs. All other views are blocked for non-staff, non-superuser
    # users.
    MAINTENANCE_MODE_IGNORE_STAFF = True
    MAINTENANCE_MODE_IGNORE_SUPERUSER = True
    MAINTENANCE_MODE_IGNORE_URLS = [
        r'^/accounts/cilogon/login/$',
        r'^/accounts/cilogon/login/callback/$',
        # TODO: Uncomment this line to allow API access in maintenance mode.
        #  Users authenticated for the API via token authentication are treated
        #  as anonymous, so they are blocked unless they are staff or superuser.
        # TODO: Make this configurable via the environment.
        # r'^/api',
        r'^/user/logout$',  # Note: There is no trailing slash.
    ]
    MAINTENANCE_MODE_STATE_FILE_PATH = '/tmp/maintenance_mode_state.txt'
else:
    MAINTENANCE_MODE = False
