# from coldfront.core.utils.common import display_time_zone_current_date

from datetime import datetime
from django.conf import settings

import re
import requests


def api_date_str_to_date(date_str):
    """Return a date object, parsed from the given string, which is
    expected to be of the form: %Y-%m-%d."""
    date_format = '%Y-%m-%d'
    return datetime.strptime(date_str, date_format).date()


def get_project_activity_pair_data(project_id, activity_id):
    """Return the data for the given (Project ID, Activity ID) pair,
    retrieved from the external API. If the pair is invalid, return an
    empty dictionary."""
    api_url = settings.LBL_BILLING_API_URL
    params = {
        'project_id': project_id,
        'activity_id': activity_id,
    }
    response = requests.get(api_url, params=params)
    json = response.json()
    return json['results'] or {}


def is_billing_id_well_formed(billing_id):
    """Return whether the given string is a valid billing ID."""
    return bool(re.match(settings.LBL_BILLING_ID_REGEX, billing_id))


def is_project_activity_pair_valid(project_id, activity_id):
    """Return whether the given (Project ID, Activity ID) pair is
    valid."""
    pair_data = get_project_activity_pair_data(project_id, activity_id)
    if not pair_data:
        return False

    # TODO: Use this method once it is available.
    # current_date = display_time_zone_current_date()
    from coldfront.core.utils.common import utc_now_offset_aware
    import pytz
    current_date = utc_now_offset_aware().astimezone(
        pytz.timezone('America/Los_Angeles')).date()

    project_start_date = api_date_str_to_date(pair_data['project_start_dt'])
    project_end_date = api_date_str_to_date(pair_data['project_end_dt'])

    activity_start_date = api_date_str_to_date(pair_data['activity_start_dt'])
    activity_end_date = api_date_str_to_date(pair_data['activity_end_dt'])

    return (
        pair_data['project_status_cd_ds'] == 'Open' and
        project_start_date <= current_date <= project_end_date and
        pair_data['activity_status_cd_ds'] == 'Open' and
        activity_start_date <= current_date <= activity_end_date)
