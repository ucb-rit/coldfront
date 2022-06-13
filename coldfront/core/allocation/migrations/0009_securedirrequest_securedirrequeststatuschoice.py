# Generated by Django 3.2.5 on 2022-06-13 18:24

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0018_add_project_allocation_request_times'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('allocation', '0008_secure_dir_manage_user_request'),
    ]

    operations = [
        migrations.CreateModel(
            name='SecureDirRequestStatusChoice',
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
            name='SecureDirRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('data_description', models.TextField()),
                ('rdm_consultation', models.TextField(null=True)),
                ('request_time', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True)),
                ('approval_time', models.DateTimeField(blank=True, null=True)),
                ('completion_time', models.DateTimeField(blank=True, null=True)),
                ('pi', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requested_pi', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='project.project')),
                ('requester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='allocation.securedirrequeststatuschoice')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
