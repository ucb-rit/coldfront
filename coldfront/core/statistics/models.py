from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from model_utils.models import TimeStampedModel


class Node(TimeStampedModel):
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name


class CPU(models.Model):
    timestamp = models.DateTimeField(blank=True, null=True)
    host = models.ForeignKey(
        Node, on_delete=models.CASCADE, blank=True, null=True)
    usage_guest = models.FloatField(default=None, blank=True, null=True)
    usage_guest_nice = models.FloatField(default=None, blank=True, null=True)
    usage_idle = models.FloatField(default=None, blank=True, null=True)
    usage_iowait = models.FloatField(default=None, blank=True, null=True)
    usage_irq = models.FloatField(default=None, blank=True, null=True)
    usage_nice = models.FloatField(default=None, blank=True, null=True)
    usage_softirq = models.FloatField(default=None, blank=True, null=True)
    usage_steal = models.FloatField(default=None, blank=True, null=True)
    usage_system = models.FloatField(default=None, blank=True, null=True)
    usage_user = models.FloatField(default=None, blank=True, null=True)

    class Meta:
        unique_together = ('timestamp', 'host')


class Job(TimeStampedModel):
    jobslurmid = models.CharField(primary_key=True, max_length=150)
    submitdate = models.DateTimeField(blank=True, null=True)
    startdate = models.DateTimeField(blank=True, null=True)
    enddate = models.DateTimeField(blank=True, null=True)
    userid = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True)
    accountid = models.ForeignKey(
        Project, on_delete=models.CASCADE, blank=True, null=True)
    amount = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_MAX_PLACES,
        default=settings.ALLOCATION_MIN,
        validators=[
            MaxValueValidator(settings.ALLOCATION_MAX),
            MinValueValidator(settings.ALLOCATION_MIN)
        ],
        blank=True,
        null=True
    )
    jobstatus = models.CharField(max_length=50, blank=True, null=True)
    partition = models.CharField(max_length=50, blank=True, null=True)
    qos = models.CharField(max_length=50, blank=True, null=True)
    nodes = models.ManyToManyField(Node)
    num_cpus = models.IntegerField(default=None, blank=True, null=True)
    num_req_nodes = models.IntegerField(default=None, blank=True, null=True)
    num_alloc_nodes = models.IntegerField(default=None, blank=True, null=True)
    raw_time = models.FloatField(default=None, blank=True, null=True)
    cpu_time = models.FloatField(default=None, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['startdate'], name='job_startdate_idx'),
        ]

    def __str__(self):
        return self.jobslurmid


class ProjectTransaction(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='transactions')
    date_time = models.DateTimeField(
        blank=True, null=True, default=timezone.now)
    allocation = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_MAX_PLACES,
        default=settings.ALLOCATION_MIN,
        validators=[
            MaxValueValidator(settings.ALLOCATION_MAX),
            MinValueValidator(settings.ALLOCATION_MIN)
        ],
        blank=True,
        null=True)

    class Meta:
        verbose_name = 'Project Transaction'


class ProjectUserTransaction(models.Model):
    project_user = models.ForeignKey(
        ProjectUser, on_delete=models.CASCADE, related_name='transactions')
    date_time = models.DateTimeField(
        blank=True, null=True, default=timezone.now)
    allocation = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_MAX_PLACES,
        default=settings.ALLOCATION_MIN,
        validators=[
            MaxValueValidator(settings.ALLOCATION_MAX),
            MinValueValidator(settings.ALLOCATION_MIN)
        ],
        blank=True,
        null=True)

    class Meta:
        verbose_name = 'Project User Transaction'


class JobWaitHeatmap30d(models.Model):
    """Precomputed 30-day median queue wait times by partition and CPU bucket."""
    generated_at = models.DateTimeField()
    partition = models.CharField(max_length=50)
    cpu_bucket = models.CharField(max_length=20)
    p50_wait_seconds = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=2,
        help_text='Median wait time in seconds'
    )
    sample_size = models.IntegerField(
        help_text='Number of jobs in this bucket'
    )

    class Meta:
        verbose_name = 'Job Wait Heatmap (30-day)'
        indexes = [
            models.Index(fields=['generated_at'], name='heatmap_generated_at_idx'),
        ]

    def __str__(self):
        return f'{self.partition} / {self.cpu_bucket} - {self.p50_wait_seconds}s'
