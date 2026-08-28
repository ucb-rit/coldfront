from collections import defaultdict
from datetime import datetime, timezone
import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import OperationalError, connection
from django.views.generic import TemplateView
from flags.state import flag_enabled

from coldfront.plugins.analytics.permissions import user_can_view_analytics

logger = logging.getLogger(__name__)


CACHE_TTL = 3600  # 1 hour

# Tableau-10 palette — enough for ~15 partitions
_COLORS = [
    "#4e79a7",
    "#f28e2b",
    "#e15759",
    "#76b7b2",
    "#59a14f",
    "#edc948",
    "#b07aa1",
    "#ff9da7",
    "#9c755f",
    "#bab0ac",
    "#a0cbe8",
    "#ffbe7d",
    "#fabfd2",
    "#8cd17d",
    "#b6992d",
]

# GPU partition lists — hard-coded per deployment tier rather than a setting,
# since this plugin is a short-lived bridge to the analytics lakehouse.
_BRC_GPU_PARTITIONS = ("savio3_gpu", "savio4_gpu")
_LRC_GPU_PARTITIONS = ("es0", "es1", "es2")


_MISCONFIGURED = (
    "Analytics plugin requires either BRC_ONLY or LRC_ONLY flag to be enabled."
)


def _cluster_tag():
    """Short identifier for cache key scoping."""
    if flag_enabled("BRC_ONLY"):
        return "brc"
    if flag_enabled("LRC_ONLY"):
        return "lrc"
    raise ImproperlyConfigured(_MISCONFIGURED)


def _cpu_partition_clause(alias=""):
    """Return (sql_fragment, params) to filter to the deployment's CPU partitions."""
    col = f"{alias}.partition" if alias else "partition"
    if flag_enabled("BRC_ONLY"):
        return f"AND {col} LIKE %s", ["savio%"]
    if flag_enabled("LRC_ONLY"):
        return f"AND {col} LIKE %s", ["lr%"]
    raise ImproperlyConfigured(_MISCONFIGURED)


def _gpu_partition_clause():
    """Return (sql_fragment, params) to filter to the deployment's GPU partitions."""
    if flag_enabled("BRC_ONLY"):
        placeholders = ", ".join(["%s"] * len(_BRC_GPU_PARTITIONS))
        return f"AND partition IN ({placeholders})", list(_BRC_GPU_PARTITIONS)
    if flag_enabled("LRC_ONLY"):
        placeholders = ", ".join(["%s"] * len(_LRC_GPU_PARTITIONS))
        return f"AND partition IN ({placeholders})", list(_LRC_GPU_PARTITIONS)
    raise ImproperlyConfigured(_MISCONFIGURED)


def _cpu_qos_clause():
    """Return (sql_fragment, params) to filter QoS to the deployment's CPU prefix.

    Mirrors the partition filter so condo QoSes running on cluster partitions
    are excluded from the CPU wait-time view by default.
    """
    if flag_enabled("BRC_ONLY"):
        return "AND qos LIKE %s", ["savio%"]
    if flag_enabled("LRC_ONLY"):
        return "AND qos LIKE %s", ["lr%"]
    raise ImproperlyConfigured(_MISCONFIGURED)


def _gpu_qos_clause():
    """Return (sql_fragment, params) to filter QoS to the deployment's GPU-native prefix.

    BRC GPU QoSes start with 'savio'; LRC GPU QoSes start with 'es'.
    Condo QoSes (condo_*) are excluded by default; omit to show all.
    """
    if flag_enabled("BRC_ONLY"):
        return "AND qos LIKE %s", ["savio%"]
    if flag_enabled("LRC_ONLY"):
        return "AND qos LIKE %s", ["es%"]
    raise ImproperlyConfigured(_MISCONFIGURED)


# SQL templates — {prefix_clause} is injected at query time.
# Using .format() is safe because the SQL contains no { } characters
# other than the placeholder.
_WAIT_TIMES_SQL = """
SELECT
    partition,
    qos,
    COUNT(*) AS jobs,
    ROUND(
        percentile_cont(0.5)
            WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (startdate - submitdate)) / 60.0)
        ::numeric, 1
    ) AS p50_wait_min,
    ROUND(
        percentile_cont(0.9)
            WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (startdate - submitdate)) / 60.0)
        ::numeric, 1
    ) AS p90_wait_min
FROM statistics_job
WHERE
    startdate  >= NOW() - INTERVAL %s
    AND submitdate IS NOT NULL
    AND startdate  IS NOT NULL
    AND startdate  > submitdate
    AND qos        NOT LIKE '%%_lowprio'
    {prefix_clause}
    {qos_clause}
GROUP BY partition, qos
HAVING COUNT(*) >= %s
ORDER BY partition, p50_wait_min DESC;
"""

_GPU_WAIT_TIMES_SQL = """
SELECT
    partition,
    qos,
    COUNT(*) AS jobs,
    ROUND(
        percentile_cont(0.5)
            WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (startdate - submitdate)) / 60.0)
        ::numeric, 1
    ) AS p50_wait_min,
    ROUND(
        percentile_cont(0.9)
            WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (startdate - submitdate)) / 60.0)
        ::numeric, 1
    ) AS p90_wait_min
FROM statistics_job
WHERE
    startdate  >= NOW() - INTERVAL %s
    AND submitdate IS NOT NULL
    AND startdate  IS NOT NULL
    AND startdate  > submitdate
    {prefix_clause}
    {qos_clause}
GROUP BY partition, qos
HAVING COUNT(*) >= %s
ORDER BY partition, p50_wait_min DESC;
"""

_MONTHLY_JOBS_SQL = """
SELECT
    partition,
    to_char(date_trunc('month', startdate), 'YYYY-MM') AS month,
    COUNT(*) AS jobs
FROM statistics_job
WHERE
    startdate >= date_trunc('month', NOW()) - INTERVAL %s
    {prefix_clause}
GROUP BY partition, month
ORDER BY month, partition;
"""


_TOP_USAGE_USERS_SQL = """
SELECT
    sj.partition,
    au.username       AS name,
    COUNT(*)          AS job_count,
    COALESCE(SUM(sj.amount),   0) AS amount,
    COALESCE(SUM(sj.cpu_time), 0) AS cpu_time,
    COALESCE(SUM(sj.raw_time), 0) AS raw_time
FROM statistics_job sj
JOIN auth_user au ON au.id = sj.userid_id
WHERE sj.startdate >= NOW() - INTERVAL %s
    AND sj.enddate IS NOT NULL
    {prefix_clause}
GROUP BY sj.partition, au.username
ORDER BY sj.partition, cpu_time DESC;
"""

_TOP_USAGE_PROJECTS_SQL = """
SELECT
    sj.partition,
    pp.name          AS name,
    COUNT(*)         AS job_count,
    COALESCE(SUM(sj.amount),   0) AS amount,
    COALESCE(SUM(sj.cpu_time), 0) AS cpu_time,
    COALESCE(SUM(sj.raw_time), 0) AS raw_time
FROM statistics_job sj
JOIN project_project pp ON pp.id = sj.accountid_id
WHERE sj.startdate >= NOW() - INTERVAL %s
    AND sj.enddate IS NOT NULL
    {prefix_clause}
GROUP BY sj.partition, pp.name
ORDER BY sj.partition, cpu_time DESC;
"""


def _fmt(minutes):
    """Format a float number of minutes as a human-readable duration string."""
    if minutes is None:
        return "N/A"
    minutes = float(minutes)
    if minutes < 1:
        secs = round(minutes * 60)
        return f"{secs}s" if secs > 0 else "~0s"
    m = round(minutes)
    if m < 60:
        return f"{m}m"
    h, rem = divmod(m, 60)
    if h < 24:
        return f"{h}h {rem}m" if rem else f"{h}h"
    d, rh = divmod(h, 24)
    parts = [f"{d}d"]
    if rh:
        parts.append(f"{rh}h")
    if rem:
        parts.append(f"{rem}m")
    return " ".join(parts)


def _month_label(ym):
    """'2025-09' → 'Sep 2025'"""
    return datetime.strptime(ym, "%Y-%m").strftime("%b %Y")


class AnalyticsAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Allow access to superusers, staff, and members of 'analytics_viewers'."""

    def test_func(self):
        return user_can_view_analytics(self.request.user)


class CpuQueueWaitTimesView(AnalyticsAccessMixin, TemplateView):
    template_name = "analytics/queue_wait_times.html"

    _VALID_DAYS = {30, 90, 180, 365}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            days = int(self.request.GET.get("days", 30))
        except (ValueError, TypeError):
            days = 30
        if days not in self._VALID_DAYS:
            days = 30

        try:
            min_jobs = int(self.request.GET.get("min_jobs", 20))
            min_jobs = max(1, min(min_jobs, 10000))
        except (ValueError, TypeError):
            min_jobs = 20

        show_all_qos = self.request.GET.get("show_all_qos") == "1"

        cluster = _cluster_tag()
        prefix_clause, prefix_params = _cpu_partition_clause()
        qos_clause, qos_params = ("", []) if show_all_qos else _cpu_qos_clause()
        context["page_title"] = "CPU Queue Wait Times"
        context["days"] = days
        context["min_jobs"] = min_jobs
        context["valid_days"] = sorted(self._VALID_DAYS)
        context["show_all_qos"] = show_all_qos
        context["cache_ttl_hours"] = CACHE_TTL // 3600

        all_tag = "all" if show_all_qos else "filtered"
        cache_key = f"analytics:wait_times:{days}:{min_jobs}:{all_tag}:{cluster}"
        cached = cache.get(cache_key)
        if cached is not None:
            context.update(cached)
            return context

        sql_params = [f"{days} days", *prefix_params, *qos_params, min_jobs]
        sql = _WAIT_TIMES_SQL.format(prefix_clause=prefix_clause, qos_clause=qos_clause)

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, sql_params)
                db_rows = cursor.fetchall()
        except OperationalError:
            logger.exception("analytics: queue wait times query failed")
            context["error"] = (
                "Database query failed. Please try again later or contact support."
            )
            return context

        rows = [
            {
                "partition": partition or "",
                "qos": qos or "",
                "jobs": int(jobs),
                "p50_wait_min": float(p50) if p50 is not None else 0.0,
                "p90_wait_min": float(p90) if p90 is not None else 0.0,
                "p50_display": _fmt(p50),
                "p90_display": _fmt(p90),
            }
            for partition, qos, jobs, p50, p90 in db_rows
        ]

        payload = {
            "rows": rows,
            "generated_at": datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            ),
        }
        cache.set(cache_key, payload, CACHE_TTL)
        context.update(payload)
        return context


class MonthlyJobCountsView(AnalyticsAccessMixin, TemplateView):
    template_name = "analytics/monthly_job_counts.html"

    _VALID_MONTHS = {3, 6, 12, 24}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            months_n = int(self.request.GET.get("months", 12))
        except (ValueError, TypeError):
            months_n = 12
        if months_n not in self._VALID_MONTHS:
            months_n = 12

        cluster = _cluster_tag()
        prefix_clause, prefix_params = _cpu_partition_clause()
        context["months_n"] = months_n
        context["valid_months"] = sorted(self._VALID_MONTHS)
        context["cache_ttl_hours"] = CACHE_TTL // 3600

        cache_key = f"analytics:monthly_jobs:{months_n}:{cluster}"
        cached = cache.get(cache_key)
        if cached is not None:
            context.update(cached)
            return context

        sql_params = [f"{months_n - 1} months", *prefix_params]
        sql = _MONTHLY_JOBS_SQL.format(prefix_clause=prefix_clause)

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, sql_params)
                db_rows = cursor.fetchall()
        except OperationalError:
            logger.exception("analytics: monthly job counts query failed")
            context["error"] = (
                "Database query failed. Please try again later or contact support."
            )
            return context

        all_months = sorted({row[1] for row in db_rows})
        all_partitions = sorted({row[0] for row in db_rows})

        pivot = defaultdict(lambda: defaultdict(int))
        for partition, month, jobs in db_rows:
            pivot[partition][month] = int(jobs)

        month_labels = [_month_label(m) for m in all_months]

        datasets = [
            {
                "label": partition,
                "data": [pivot[partition].get(m, 0) for m in all_months],
                "backgroundColor": _COLORS[i % len(_COLORS)],
                "borderWidth": 0,
            }
            for i, partition in enumerate(all_partitions)
        ]

        table_rows = [
            {
                "partition": partition,
                "counts": [pivot[partition].get(m, 0) for m in all_months],
                "total": sum(pivot[partition].get(m, 0) for m in all_months),
            }
            for partition in all_partitions
        ]

        col_totals = [
            sum(pivot[p].get(m, 0) for p in all_partitions) for m in all_months
        ]

        payload = {
            "month_labels": month_labels,
            "table_rows": table_rows,
            "col_totals": col_totals,
            "grand_total": sum(col_totals),
            "months_json": json.dumps(month_labels),
            "datasets_json": json.dumps(datasets),
            "generated_at": datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            ),
        }
        cache.set(cache_key, payload, CACHE_TTL)
        context.update(payload)
        return context


class GpuQueueWaitTimesView(AnalyticsAccessMixin, TemplateView):
    template_name = "analytics/queue_wait_times.html"

    _VALID_DAYS = {30, 90, 180, 365}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            days = int(self.request.GET.get("days", 30))
        except (ValueError, TypeError):
            days = 30
        if days not in self._VALID_DAYS:
            days = 30

        try:
            min_jobs = int(self.request.GET.get("min_jobs", 20))
            min_jobs = max(1, min(min_jobs, 10000))
        except (ValueError, TypeError):
            min_jobs = 20

        show_all_qos = self.request.GET.get("show_all_qos") == "1"

        cluster = _cluster_tag()
        prefix_clause, prefix_params = _gpu_partition_clause()
        qos_clause, qos_params = ("", []) if show_all_qos else _gpu_qos_clause()
        context["page_title"] = "GPU Queue Wait Times"
        context["page_description"] = (
            "Median and p90 queue wait times by GPU partition and QOS. "
            "Lowprio QOS are included (unlike CPU wait times). "
            "Condo QOS are excluded by default — use the toggle to include them."
        )
        context["days"] = days
        context["min_jobs"] = min_jobs
        context["valid_days"] = sorted(self._VALID_DAYS)
        context["show_all_qos"] = show_all_qos
        context["cache_ttl_hours"] = CACHE_TTL // 3600

        all_tag = "all" if show_all_qos else "filtered"
        cache_key = f"analytics:gpu_wait_times:{days}:{min_jobs}:{all_tag}:{cluster}"
        cached = cache.get(cache_key)
        if cached is not None:
            context.update(cached)
            return context

        sql_params = [f"{days} days", *prefix_params, *qos_params, min_jobs]
        sql = _GPU_WAIT_TIMES_SQL.format(
            prefix_clause=prefix_clause, qos_clause=qos_clause
        )

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, sql_params)
                db_rows = cursor.fetchall()
        except OperationalError:
            logger.exception("analytics: GPU queue wait times query failed")
            context["error"] = (
                "Database query failed. Please try again later or contact support."
            )
            return context

        rows = [
            {
                "partition": partition or "",
                "qos": qos or "",
                "jobs": int(jobs),
                "p50_wait_min": float(p50) if p50 is not None else 0.0,
                "p90_wait_min": float(p90) if p90 is not None else 0.0,
                "p50_display": _fmt(p50),
                "p90_display": _fmt(p90),
            }
            for partition, qos, jobs, p50, p90 in db_rows
        ]

        payload = {
            "rows": rows,
            "generated_at": datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            ),
        }
        cache.set(cache_key, payload, CACHE_TTL)
        context.update(payload)
        return context


def _run_top_usage_sql(sql_template, days):
    """Execute one of the top-usage SQL templates and return raw DB rows."""
    prefix_clause, prefix_params = _cpu_partition_clause(alias="sj")
    params = [f"{days} days", *prefix_params]
    sql = sql_template.format(prefix_clause=prefix_clause)
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def _rows_to_dicts(raw_rows):
    return [
        {
            "partition": partition or "",
            "name": name or "",
            "job_count": int(job_count),
            "amount": float(amount),
            "cpu_time": float(cpu_time),
            "raw_time": float(raw_time),
        }
        for partition, name, job_count, amount, cpu_time, raw_time in raw_rows
    ]


class TopUsageView(AnalyticsAccessMixin, TemplateView):
    template_name = "analytics/top_usage.html"

    _VALID_DAYS = {30, 90, 180, 365}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            days = int(self.request.GET.get("days", 30))
        except (ValueError, TypeError):
            days = 30
        if days not in self._VALID_DAYS:
            days = 30

        cluster = _cluster_tag()
        context["days"] = days
        context["valid_days"] = sorted(self._VALID_DAYS)
        context["cache_ttl_hours"] = CACHE_TTL // 3600

        cache_key = f"analytics:top_usage:{days}:{cluster}"
        cached = cache.get(cache_key)
        if cached is not None:
            context.update(cached)
            return context

        try:
            user_rows = _run_top_usage_sql(_TOP_USAGE_USERS_SQL, days)
            project_rows = _run_top_usage_sql(_TOP_USAGE_PROJECTS_SQL, days)
        except OperationalError:
            logger.exception("analytics: top usage query failed")
            context["error"] = (
                "Database query failed. Please try again later or contact support."
            )
            return context

        payload = {
            "users_json": json.dumps(_rows_to_dicts(user_rows)),
            "projects_json": json.dumps(_rows_to_dicts(project_rows)),
            "generated_at": datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            ),
        }
        cache.set(cache_key, payload, CACHE_TTL)
        context.update(payload)
        return context
