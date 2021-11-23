# Generated by Django 3.2.5 on 2021-10-23 20:41

import coldfront.core.allocation.models
from decimal import Decimal
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0014_project_allocation_request_rename_mou_to_recharge'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('allocation', '0005_add_review_cluster_account_permission'),
    ]

    operations = [
        migrations.CreateModel(
            name='AllocationPeriod',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AllocationRenewalRequestStatusChoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(max_length=64)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='AllocationRenewalRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('num_service_units', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=11, validators=[django.core.validators.MinValueValidator(Decimal('0.00')), django.core.validators.MaxValueValidator(Decimal('100000000.00'))])),
                ('request_time', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True)),
                ('approval_time', models.DateTimeField(blank=True, null=True)),
                ('completion_time', models.DateTimeField(blank=True, null=True)),
                ('state', models.JSONField(default=coldfront.core.allocation.models.allocation_renewal_request_state_schema)),
                ('extra_fields', models.JSONField(default=dict)),
                ('allocation_period', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='allocation.allocationperiod')),
                ('new_project_request', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='project.savioprojectallocationrequest')),
                ('pi', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allocation_renewal_pi', to=settings.AUTH_USER_MODEL)),
                ('post_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allocation_renewal_post_project', to='project.project')),
                ('pre_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allocation_renewal_pre_project', to='project.project')),
                ('requester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allocation_renewal_requester', to=settings.AUTH_USER_MODEL)),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='allocation.allocationrenewalrequeststatuschoice')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
