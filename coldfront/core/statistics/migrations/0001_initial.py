# Generated by Django 2.2.13 on 2020-09-04 21:27

from decimal import Decimal
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('project', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(max_length=30, unique=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('jobslurmid', models.CharField(max_length=150, primary_key=True, serialize=False)),
                ('submitdate', models.DateTimeField(blank=True, null=True)),
                ('startdate', models.DateTimeField(blank=True, null=True)),
                ('enddate', models.DateTimeField(blank=True, null=True)),
                ('amount', models.DecimalField(blank=True, decimal_places=2, default=Decimal('0.00'), max_digits=11, null=True, validators=[django.core.validators.MaxValueValidator(Decimal('100000000.00')), django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('jobstatus', models.CharField(blank=True, max_length=50, null=True)),
                ('partition', models.CharField(blank=True, max_length=50, null=True)),
                ('qos', models.CharField(blank=True, max_length=50, null=True)),
                ('num_cpus', models.IntegerField(blank=True, default=None, null=True)),
                ('num_req_nodes', models.IntegerField(blank=True, default=None, null=True)),
                ('num_alloc_nodes', models.IntegerField(blank=True, default=None, null=True)),
                ('raw_time', models.FloatField(blank=True, default=None, null=True)),
                ('cpu_time', models.FloatField(blank=True, default=None, null=True)),
                ('accountid', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='project.Project')),
                ('nodes', models.ManyToManyField(to='statistics.Node')),
                ('userid', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CPU',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(blank=True, null=True)),
                ('usage_guest', models.FloatField(blank=True, default=None, null=True)),
                ('usage_guest_nice', models.FloatField(blank=True, default=None, null=True)),
                ('usage_idle', models.FloatField(blank=True, default=None, null=True)),
                ('usage_iowait', models.FloatField(blank=True, default=None, null=True)),
                ('usage_irq', models.FloatField(blank=True, default=None, null=True)),
                ('usage_nice', models.FloatField(blank=True, default=None, null=True)),
                ('usage_softirq', models.FloatField(blank=True, default=None, null=True)),
                ('usage_steal', models.FloatField(blank=True, default=None, null=True)),
                ('usage_system', models.FloatField(blank=True, default=None, null=True)),
                ('usage_user', models.FloatField(blank=True, default=None, null=True)),
                ('host', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='statistics.Node')),
            ],
            options={
                'unique_together': {('timestamp', 'host')},
            },
        ),
    ]
