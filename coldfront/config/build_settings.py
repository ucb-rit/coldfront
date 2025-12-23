"""
Minimal Django settings for Docker image build.

This file provides just enough configuration to run collectstatic during
the Docker build process. All values are dummy/minimal and will be overridden
at runtime by env_settings.py or the appropriate environment-specific settings.

This follows the same pattern as env_settings.py - only set the top-level
variables, and let local_settings.py do the composition work.
"""

#------------------------------------------------------------------------------
# Security
#------------------------------------------------------------------------------

SECRET_KEY = 'build-time-insecure-secret-key-will-be-overridden-at-runtime'

#------------------------------------------------------------------------------
# Portal/Program Information
#------------------------------------------------------------------------------

PORTAL_NAME = 'Build Portal'
PROGRAM_NAME_LONG = 'Build Program'
PROGRAM_NAME_SHORT = 'Build'
PRIMARY_CLUSTER_NAME = 'build-cluster'

CENTER_NAME = PROGRAM_NAME_SHORT + ' HPC Resources'
CENTER_USER_GUIDE = 'http://localhost/guide'
CENTER_LOGIN_GUIDE = 'http://localhost/login'
CENTER_HELP_EMAIL = 'build@localhost'
CENTER_BASE_URL = 'http://localhost'
CENTER_HELP_URL = CENTER_BASE_URL + '/help'
CENTER_PROJECT_RENEWAL_HELP_URL = CENTER_BASE_URL + '/help'

#------------------------------------------------------------------------------
# Email Configuration
#------------------------------------------------------------------------------

EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_SUBJECT_PREFIX = '[Build] '
EMAIL_ADMIN_LIST = ['admin@localhost']
EMAIL_SENDER = 'build@localhost'
EMAIL_TICKET_SYSTEM_ADDRESS = 'tickets@localhost'
EMAIL_DIRECTOR_EMAIL_ADDRESS = 'director@localhost'
EMAIL_PROJECT_REVIEW_CONTACT = 'review@localhost'
EMAIL_DEVELOPMENT_EMAIL_LIST = ['dev@localhost']
EMAIL_OPT_OUT_INSTRUCTION_URL = CENTER_BASE_URL + '/optout'
EMAIL_SIGNATURE = 'Build Portal Team'
EMAIL_FROM = 'build@localhost'
EMAIL_ADMIN = 'admin@localhost'

#------------------------------------------------------------------------------
# Logging Configuration
#------------------------------------------------------------------------------

LOG_PATH = '/tmp/build.log'
API_LOG_PATH = '/tmp/build_api.log'
STREAM_LOGS_TO_STDOUT = True

#------------------------------------------------------------------------------
# Extra Apps/Middleware (pattern from env_settings.py)
#------------------------------------------------------------------------------

# These will be added to EXTRA_APPS and EXTRA_MIDDLEWARE by local_settings.py
EXTRA_EXTRA_APPS = []
EXTRA_EXTRA_MIDDLEWARE = []

#------------------------------------------------------------------------------
# Notification Settings
#------------------------------------------------------------------------------

REQUEST_APPROVAL_CC_LIST = []
PROJECT_USER_REMOVAL_REQUEST_PROCESSED_EMAIL_ADMIN_LIST = []

#------------------------------------------------------------------------------
# Security & Access Control
#------------------------------------------------------------------------------

ALLOW_ALL_JOBS = False

#------------------------------------------------------------------------------
# BRC-Specific Settings
#------------------------------------------------------------------------------

VECTOR_PI_USERNAME = 'build-vector-pi'
SAVIO_PROJECT_FOR_VECTOR_USERS = 'build-savio-project'

#------------------------------------------------------------------------------
# Django All-Auth settings
#------------------------------------------------------------------------------

CILOGON_APP_CLIENT_ID = 'build-client-id'
CILOGON_APP_SECRET = 'build-secret'

#------------------------------------------------------------------------------
# Redis (for django-constance and caching)
#------------------------------------------------------------------------------

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_PASSWORD = 'build-redis-password'
