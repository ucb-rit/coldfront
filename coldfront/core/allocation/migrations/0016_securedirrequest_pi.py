# Generated by Django 3.2.5 on 2024-04-23 15:43

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('allocation', '0015_allocationrenewalrequest_renewal_survey_answers'),
    ]

    operations = [
        migrations.AddField(
            model_name='securedirrequest',
            name='pi',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='secure_dir_request_pi', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='securedirrequest',
            name='requester',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='secure_dir_request_requester', to=settings.AUTH_USER_MODEL),
        ),
    ]
