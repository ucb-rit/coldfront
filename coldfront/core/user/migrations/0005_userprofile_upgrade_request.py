# Generated by Django 2.2.13 on 2021-01-28 18:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_userprofile_access_agreement_signed_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='upgrade_request',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
