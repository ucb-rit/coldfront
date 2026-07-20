from collections import defaultdict
from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand, CommandError

from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.project.models import Project
from coldfront.core.resource.utils import get_primary_compute_resource_name
from coldfront.core.statistics.models import Job


PACIFIC = ZoneInfo('America/Los_Angeles')

# Maximum seconds between a job's startdate and the nearest positive usage-history
# diff before we flag the match as suspicious.
TIMESTAMP_THRESHOLD_SECONDS = 300


class Command(BaseCommand):
    """Compute the SU deduction for a project that received a preemptive
    allocation from the current allowance year.

    Prints supporting evidence and the add_service_units_to_project
    invocation needed to apply the deduction. Read-only; makes no changes
    to the database.

    Background
    ----------
    When SUs from the upcoming allowance year are granted early via
    add_service_units_to_project, the project's jobs consume those SUs
    during the previous year. After the year reset, we must subtract what
    was consumed from the project's current-year quota.

    The deduction is:

        deduction = max(U - (E - A) - previous_allowance, 0)

    where:
      U                  = AllocationAttributeUsage.value at end of the
                           previous year (last history snapshot before
                           year_cutoff)
      E                  = sum of estimated SU charges at submission time
                           for jobs that started before year_cutoff but
                           ended after it ("boundary jobs")
      A                  = sum of actual SU charges for those boundary jobs
                           (Job.amount, now holding the final value after
                           the completion PUT)
      previous_allowance = the project's normal SU grant for the previous
                           year, before the preemptive addition
                           (--previous_allowance argument)

    U - (E - A) is the true total consumption in the previous year.
    Subtracting previous_allowance isolates only the portion consumed from
    the preemptively borrowed current-year SUs. If true consumption did not
    exceed the normal grant, the deduction is 0.

    If there are no boundary jobs (E = A = 0), deduction = max(U - previous_allowance, 0).

    The (E - A) correction accounts for the fact that E was charged to the
    old usage counter (and is therefore included in U), but the normal
    post-completion correction was clamped to 0 after the year reset and
    never applied. Without the correction we would over-deduct by (E - A).

    Recovering E
    ------------
    Job has no HistoricalRecords, so E_i (the estimated cost at submission)
    is gone once the completion PUT overwrites Job.amount with the actual
    cost. We recover E_i from positive diffs in the AllocationAttributeUsage
    history: each job submission fires a save() that increases the usage
    counter by E_i. We match each boundary job to the closest positive diff
    entry by timestamp (using job.startdate as the reference).
    """

    help = (
        'Compute the SU deduction for a project that received a preemptive '
        'allocation from the current allowance year. Prints supporting '
        'evidence and the add_service_units_to_project invocation to apply '
        'the deduction. Read-only.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--project_name',
            required=True,
            type=str,
            help='Name of the project to compute the deduction for.',
        )
        parser.add_argument(
            '--previous_allowance',
            required=True,
            type=int,
            help=(
                "The project's normal SU grant for the previous year, "
                'before the preemptive addition was made. Only consumption '
                'above this amount is charged to the current year.'
            ),
        )
        parser.add_argument(
            '--year_cutoff_date',
            required=True,
            type=str,
            help=(
                'Date (YYYY-MM-DD) on which the allowance year reset ran, '
                'in US/Pacific local time. Midnight on this date is used as '
                'the exclusive upper bound for the previous year. '
                'Example: "2026-06-01"'
            ),
        )

    def handle(self, *args, **options):
        project_name = options['project_name']
        previous_allowance = Decimal(options['previous_allowance'])
        year_cutoff_date_str = options['year_cutoff_date']

        try:
            cutoff_date = date.fromisoformat(year_cutoff_date_str)
        except ValueError:
            raise CommandError(
                f'Could not parse --year_cutoff_date "{year_cutoff_date_str}". '
                f'Use YYYY-MM-DD format, e.g. "2026-06-01".'
            )
        # Midnight US/Pacific on the reset date — ZoneInfo handles DST automatically.
        year_cutoff = datetime.combine(cutoff_date, time.min, tzinfo=PACIFIC)

        try:
            project = Project.objects.get(name=project_name)
        except Project.DoesNotExist:
            raise CommandError(f'Project "{project_name}" does not exist.')

        try:
            accounting_allocation_objects = get_accounting_allocation_objects(project)
        except ObjectDoesNotExist:
            resource_name = get_primary_compute_resource_name()
            raise CommandError(
                f'Project "{project_name}" has no active allocation to '
                f'"{resource_name}".'
            )

        allocation_attribute = accounting_allocation_objects.allocation_attribute
        allocation_attribute_usage = (
            accounting_allocation_objects.allocation_attribute_usage
        )
        current_allowance = Decimal(allocation_attribute.value)

        # U: last usage value before the year reset
        pre_reset_entry = (
            allocation_attribute_usage.history
            .filter(history_date__lt=year_cutoff)
            .order_by('-history_date', '-history_id')
            .first()
        )
        if pre_reset_entry is None:
            raise CommandError(
                f'No usage history found before {year_cutoff_date_str} for '
                f'project "{project_name}".'
            )
        U = Decimal(str(pre_reset_entry.value))

        # Boundary jobs: started before the cutoff, ended on or after it
        boundary_jobs = list(
            Job.objects.filter(
                accountid=project,
                startdate__lt=year_cutoff,
                enddate__gte=year_cutoff,
            ).order_by('startdate')
        )

        A = sum(
            (Decimal(str(job.amount)) for job in boundary_jobs),
            Decimal('0'),
        )

        E, e_per_job, ambiguous_jobs = self._compute_E(
            allocation_attribute_usage, boundary_jobs, year_cutoff
        )

        true_consumption = U - (E - A)
        deduction = max(true_consumption - previous_allowance, Decimal('0'))
        deduction_int = int(deduction)  # truncates toward zero (floor for positive)

        # --- Output ---
        out = self.stdout.write
        out('')
        out(f'Project:             {project_name}')
        out(f'Year cutoff:         {year_cutoff_date_str}')
        out(f'Previous allowance:  {previous_allowance:.2f} SUs  (normal grant before preemptive addition)')
        out(f'Current allowance:   {current_allowance:.2f} SUs')
        out('')
        out(
            f'U (usage at '
            f'{pre_reset_entry.history_date.strftime("%Y-%m-%d %H:%M:%S %Z")}): '
            f'{U:.2f} SUs'
        )
        out('')

        if boundary_jobs:
            out(f'Boundary jobs ({len(boundary_jobs)}):')
            col = '  {:<20}  {:<26}  {:<26}  {:>12}  {:>12}'
            out(col.format('Job ID', 'Start (UTC)', 'End (UTC)',
                           'E_i (est.)', 'A_i (actual)'))
            out('  ' + '-' * 102)
            for job in boundary_jobs:
                e_i = e_per_job.get(job.jobslurmid, Decimal('0'))
                a_i = Decimal(str(job.amount))
                out(col.format(
                    job.jobslurmid,
                    str(job.startdate),
                    str(job.enddate),
                    f'{e_i:.2f}',
                    f'{a_i:.2f}',
                ))
            out('')
            if ambiguous_jobs:
                out(self.style.WARNING(
                    'WARNING: E_i is uncertain for the following jobs. '
                    'Verify manually before applying the deduction.'
                ))
                for job_id, note in ambiguous_jobs:
                    out(self.style.WARNING(f'  {job_id}: {note}'))
                out('')
        else:
            out('Boundary jobs: none')
            out('')

        w = 12
        out(f'E (total estimated boundary SUs):    {E:>{w}.2f}')
        out(f'A (total actual boundary SUs):       {A:>{w}.2f}')
        out('')
        out(f'Prev. year consumption (U - (E-A)):  {true_consumption:>{w}.2f}')
        out(f'Normal grant (previous_allowance):  -{previous_allowance:>{w}.2f}')
        out('                                    ' + '-' * (w + 1))
        out(f'Consumed from preemptive allocation: {deduction:>{w}.2f}')
        out(f'Deduction (floored to int):          {deduction_int:>{w}d}')
        out('')
        out('To apply the deduction, run:')
        out('')
        out(
            f'  python manage.py add_service_units_to_project \\\n'
            f'    --project_name {project_name} \\\n'
            f'    --amount -{deduction_int} \\\n'
            f'    --reason "<your reason here>"'
        )
        out('')

    def _compute_E(self, allocation_attribute_usage, boundary_jobs, year_cutoff):
        """Estimate E_i for each boundary job from pre-reset usage history diffs.

        Returns:
            E           Decimal  — total estimated SUs across all boundary jobs
            e_per_job   dict     — {jobslurmid: Decimal E_i}
            ambiguous   list     — [(jobslurmid, note)] for uncertain matches
        """
        if not boundary_jobs:
            return Decimal('0'), {}, []

        # All pre-reset history entries in ascending chronological order
        entries = list(
            allocation_attribute_usage.history
            .filter(history_date__lt=year_cutoff)
            .order_by('history_date', 'history_id')
        )

        # Positive diffs correspond to job submissions (usage increased by E_i).
        # Negative diffs correspond to job completions or corrections.
        positive_diffs = []  # [(history_date, diff_value)]
        for prev, curr in zip(entries, entries[1:]):
            d = Decimal(str(curr.value)) - Decimal(str(prev.value))
            if d > 0:
                positive_diffs.append((curr.history_date, d))

        e_per_job = {}
        ambiguous = []

        if not positive_diffs:
            for job in boundary_jobs:
                ambiguous.append((
                    job.jobslurmid,
                    'no positive diffs found in pre-reset usage history',
                ))
                e_per_job[job.jobslurmid] = Decimal('0')
            return Decimal('0'), e_per_job, ambiguous

        def closest_idx(job):
            return min(
                range(len(positive_diffs)),
                key=lambda i: abs(
                    (positive_diffs[i][0] - job.startdate).total_seconds()
                ),
            )

        # Map each boundary job to the index of its nearest positive diff entry
        job_to_idx = {job.jobslurmid: closest_idx(job) for job in boundary_jobs}

        # Detect diff entries claimed by more than one boundary job
        idx_to_jobs = defaultdict(list)
        for job in boundary_jobs:
            idx_to_jobs[job_to_idx[job.jobslurmid]].append(job)

        for job in boundary_jobs:
            idx = job_to_idx[job.jobslurmid]
            diff_date, diff_value = positive_diffs[idx]
            delta_s = abs((diff_date - job.startdate).total_seconds())
            competing = [
                j for j in idx_to_jobs[idx] if j.jobslurmid != job.jobslurmid
            ]

            if competing:
                names = ', '.join(j.jobslurmid for j in competing)
                ambiguous.append((
                    job.jobslurmid,
                    f'shares diff entry ({diff_date}, +{diff_value:.2f} SUs) '
                    f'with job(s) {names}; cannot split automatically — '
                    f'E_i set to 0, inspect history manually',
                ))
                e_per_job[job.jobslurmid] = Decimal('0')
            elif delta_s > TIMESTAMP_THRESHOLD_SECONDS:
                ambiguous.append((
                    job.jobslurmid,
                    f'nearest positive diff is {delta_s:.0f}s from startdate '
                    f'(threshold {TIMESTAMP_THRESHOLD_SECONDS}s); '
                    f'using ({diff_date}, +{diff_value:.2f} SUs) — verify',
                ))
                e_per_job[job.jobslurmid] = diff_value
            else:
                e_per_job[job.jobslurmid] = diff_value

        E = sum(e_per_job.values(), Decimal('0'))
        return E, e_per_job, ambiguous
