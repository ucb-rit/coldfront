# Generated by Django 3.2.5 on 2022-06-24 20:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('resource', '0003_add_resource_is_unique_per_project'),
        ('project', '0019_projectuserjoinrequest_host_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalsavioprojectallocationrequest',
            name='computing_allowance',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='resource.resource'),
        ),
        migrations.AddField(
            model_name='savioprojectallocationrequest',
            name='computing_allowance',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='computing_allowance', to='resource.resource'),
        ),
    ]
