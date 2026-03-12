"""Utilities for queue wait time analytics."""


def get_cpu_bucket(num_cpus):
    """
    Map CPU count to logarithmic bucket.

    HPC jobs span 1-1024+ CPUs; linear buckets are useless.
    Use log scale to group similar resource requests.

    Args:
        num_cpus: Number of CPUs for the job

    Returns:
        String bucket label (e.g., '1', '2-4', '5-16', etc.)
    """
    if num_cpus is None:
        return None
    if num_cpus == 1:
        return '1'
    elif num_cpus <= 4:
        return '2-4'
    elif num_cpus <= 16:
        return '5-16'
    elif num_cpus <= 64:
        return '17-64'
    elif num_cpus <= 256:
        return '65-256'
    elif num_cpus <= 1024:
        return '257-1024'
    else:
        return '1024+'


def get_cpu_bucket_sql_case(table_alias=None):
    """
    Return SQL CASE expression for CPU bucketing.

    For use in raw SQL queries or Django ORM annotations.

    Args:
        table_alias: Optional table alias (e.g., 'j' for 'j.num_cpus')

    Returns:
        String containing SQL CASE expression
    """
    column = f"{table_alias}.num_cpus" if table_alias else "num_cpus"
    return f"""
    CASE
        WHEN {column} = 1 THEN '1'
        WHEN {column} <= 4 THEN '2-4'
        WHEN {column} <= 16 THEN '5-16'
        WHEN {column} <= 64 THEN '17-64'
        WHEN {column} <= 256 THEN '65-256'
        WHEN {column} <= 1024 THEN '257-1024'
        ELSE '1024+'
    END
    """


# Define bucket order for display
CPU_BUCKET_ORDER = ['1', '2-4', '5-16', '17-64', '65-256', '257-1024', '1024+']
