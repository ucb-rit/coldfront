# Generated by Django 3.2.5 on 2024-03-05 19:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('allocation', '0012_cluster_access_request_remove_host_user_and_billing_activity'),
    ]

    operations = [
        migrations.AddField(
            model_name='allocationrenewalrequest',
            name='renewal_survey_answers',
            field=models.JSONField(default=dict),
        ),
    ]