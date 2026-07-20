import copy
from datetime import datetime, timedelta

from coldfront.core.utils.common import display_time_zone_date_to_utc_datetime


def job_query_filtering(job_list, data):
    status = data.get("status")
    if status:
        if status == "COMPLETING":
            job_list = job_list.filter(jobstatus__in=["COMPLETED", "COMPLETING"])
        else:
            job_list = job_list.filter(jobstatus__icontains=status)

    if data.get("jobslurmid"):
        job_list = job_list.filter(jobslurmid__icontains=data.get("jobslurmid"))

    if data.get("project_name"):
        job_list = job_list.filter(accountid__name=data.get("project_name"))

    if data.get("username"):
        job_list = job_list.filter(userid__username=data.get("username"))

    if data.get("partition"):
        job_list = job_list.filter(partition=data.get("partition"))

    if data.get("submitdate_after"):
        after = display_time_zone_date_to_utc_datetime(data.get("submitdate_after"))
        job_list = job_list.filter(submitdate__gte=after)

    if data.get("submitdate_before"):
        before = display_time_zone_date_to_utc_datetime(
            data.get("submitdate_before") + timedelta(days=1)
        )
        job_list = job_list.filter(submitdate__lt=before)

    return job_list


class JobSearchFilterSessionStorage:
    """A class that stores job search filters in the user's session for
    retrieval."""

    def __init__(self, request):
        self._request = request
        self._session_key = "job_search_filters"
        self._date_keys = ("submitdate_after", "submitdate_before")
        self._date_format = "%m/%d/%Y"

    def get(self):
        if self._session_key not in self._request.session:
            return {}

        serialized_filters = self._request.session[self._session_key]

        return self._deserialize_filters(serialized_filters)

    def set(self, filters):
        self._request.session[self._session_key] = self._serialize_filters(filters)

    def _deserialize_filters(self, filters):
        filters_copy = copy.deepcopy(filters)
        for date_key in self._date_keys:
            serialized_date = filters_copy.get(date_key, None)
            if serialized_date is not None:
                filters_copy[date_key] = datetime.strptime(
                    serialized_date, self._date_format
                ).date()
        return filters_copy

    def _serialize_filters(self, filters):
        filters_copy = copy.deepcopy(filters)
        for date_key in self._date_keys:
            unserialized_date = filters_copy.get(date_key, None)
            if unserialized_date is not None:
                filters_copy[date_key] = datetime.strftime(
                    unserialized_date, self._date_format
                )
        return filters_copy
