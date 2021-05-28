# Generated by Django 2.2.13 on 2020-10-01 21:10

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_expiringtoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='cluster_uid',
            field=models.CharField(blank=True, max_length=10, null=True, unique=True, validators=[django.core.validators.MinLengthValidator(3), django.core.validators.RegexValidator(message='Cluster UID must be numeric.', regex='^[0-9]+$')]),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='middle_name',
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
