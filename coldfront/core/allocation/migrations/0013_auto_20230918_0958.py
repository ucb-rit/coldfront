# Generated by Django 3.2.5 on 2023-09-18 09:58

import coldfront.core.utils.mou
from django.db import migrations, models
import gdstorage.storage


class Migration(migrations.Migration):

    dependencies = [
        ('allocation', '0012_cluster_access_request_remove_host_user_and_billing_activity'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='historicalallocation',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical allocation', 'verbose_name_plural': 'historical allocations'},
        ),
        migrations.AlterModelOptions(
            name='historicalallocationattribute',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical allocation attribute', 'verbose_name_plural': 'historical allocation attributes'},
        ),
        migrations.AlterModelOptions(
            name='historicalallocationattributetype',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical allocation attribute type', 'verbose_name_plural': 'historical allocation attribute types'},
        ),
        migrations.AlterModelOptions(
            name='historicalallocationattributeusage',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical allocation attribute usage', 'verbose_name_plural': 'historical allocation attribute usages'},
        ),
        migrations.AlterModelOptions(
            name='historicalallocationuser',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical allocation user', 'verbose_name_plural': 'historical Allocation User Status'},
        ),
        migrations.AlterModelOptions(
            name='historicalallocationuserattribute',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical allocation user attribute', 'verbose_name_plural': 'historical allocation user attributes'},
        ),
        migrations.AlterModelOptions(
            name='historicalallocationuserattributeusage',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical allocation user attribute usage', 'verbose_name_plural': 'historical allocation user attribute usages'},
        ),
        migrations.AlterModelOptions(
            name='historicalclusteraccessrequest',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical cluster access request', 'verbose_name_plural': 'historical cluster access requests'},
        ),
        migrations.AddField(
            model_name='allocationadditionrequest',
            name='mou_file',
            field=models.FileField(null=True, storage=gdstorage.storage.GoogleDriveStorage(permissions=()), upload_to=coldfront.core.utils.mou.upload_to_func),
        ),
        migrations.AddField(
            model_name='securedirrequest',
            name='department',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='securedirrequest',
            name='mou_file',
            field=models.FileField(null=True, storage=gdstorage.storage.GoogleDriveStorage(permissions=()), upload_to=coldfront.core.utils.mou.upload_to_func),
        ),
        migrations.AlterField(
            model_name='historicalallocation',
            name='history_date',
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterField(
            model_name='historicalallocationattribute',
            name='history_date',
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterField(
            model_name='historicalallocationattributetype',
            name='history_date',
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterField(
            model_name='historicalallocationattributeusage',
            name='history_date',
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterField(
            model_name='historicalallocationuser',
            name='history_date',
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterField(
            model_name='historicalallocationuserattribute',
            name='history_date',
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterField(
            model_name='historicalallocationuserattributeusage',
            name='history_date',
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterField(
            model_name='historicalclusteraccessrequest',
            name='history_date',
            field=models.DateTimeField(db_index=True),
        ),
    ]