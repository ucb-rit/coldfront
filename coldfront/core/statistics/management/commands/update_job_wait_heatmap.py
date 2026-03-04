from coldfront.core.statistics.models import Job, JobWaitHeatmap30d
from coldfront.core.statistics.utils_.queue_wait_analytics import get_cpu_bucket_sql_case
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
import logging


class Command(BaseCommand):
    help = 'Update 30-day job wait time heatmap summary table'
    logger = logging.getLogger(__name__)

    MINIMUM_SAMPLE_SIZE = 20
    DAYS = 30  # Fixed 30-day window to match JobWaitHeatmap30d model

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show results without updating database'
        )

    def handle(self, *args, **options):
        days = self.DAYS
        dry_run = options['dry_run']

        start_time = timezone.now()
        self.stdout.write(f'Computing {days}-day wait time heatmap...')

        # Compute aggregations using raw SQL for performance
        # Uses percentile_cont for median calculation
        sql = f"""
            SELECT
                partition,
                cpu_bucket,
                percentile_cont(0.5) WITHIN GROUP (
                    ORDER BY EXTRACT(EPOCH FROM (startdate - submitdate))
                ) AS p50_wait_seconds,
                COUNT(*) as sample_size
            FROM (
                SELECT
                    partition,
                    startdate,
                    submitdate,
                    {get_cpu_bucket_sql_case()} AS cpu_bucket
                FROM statistics_job
                WHERE startdate >= NOW() - INTERVAL '{days} days'
                    AND startdate IS NOT NULL
                    AND submitdate IS NOT NULL
            ) sub
            GROUP BY partition, cpu_bucket
            HAVING COUNT(*) >= {self.MINIMUM_SAMPLE_SIZE}
            ORDER BY partition, cpu_bucket;
        """

        with connection.cursor() as cursor:
            cursor.execute(sql)
            results = cursor.fetchall()

        self.stdout.write(f'Found {len(results)} partition/bucket combinations')

        if dry_run:
            for row in results:
                partition, cpu_bucket, p50_seconds, sample_size = row
                self.stdout.write(
                    f'  {partition:20s} {cpu_bucket:12s} '
                    f'p50={p50_seconds:8.1f}s  n={sample_size}'
                )
            self.stdout.write(self.style.WARNING('DRY RUN - no changes made'))
            return

        # Clear old data and insert new
        JobWaitHeatmap30d.objects.all().delete()

        generated_at = timezone.now()
        heatmap_objects = []
        for row in results:
            partition, cpu_bucket, p50_seconds, sample_size = row
            heatmap_objects.append(JobWaitHeatmap30d(
                generated_at=generated_at,
                partition=partition,
                cpu_bucket=cpu_bucket,
                p50_wait_seconds=p50_seconds,
                sample_size=sample_size
            ))

        JobWaitHeatmap30d.objects.bulk_create(heatmap_objects)

        elapsed = (timezone.now() - start_time).total_seconds()
        message = (
            f'Successfully updated heatmap with {len(heatmap_objects)} entries '
            f'in {elapsed:.1f}s'
        )
        self.stdout.write(self.style.SUCCESS(message))
        self.logger.info(message)
