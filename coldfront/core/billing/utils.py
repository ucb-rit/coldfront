from django.conf import settings

import re


def is_billing_id_well_formed(billing_id):
    """Return whether the given string is a valid billing ID."""
    return bool(re.match(settings.LBL_BILLING_ID_REGEX, billing_id))
