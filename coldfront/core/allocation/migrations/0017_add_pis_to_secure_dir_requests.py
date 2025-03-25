from django.db import migrations


def set_request_pis_to_requesters(apps, schema_editor):
    """Prior to this migration, only PIs could request new secure
    directories. Set the PI of each existing request to be equal to the
    requester."""
    SecureDirRequest = apps.get_model('allocation', 'SecureDirRequest')
    for secure_dir_request in SecureDirRequest.objects.all():
        secure_dir_request.pi = secure_dir_request.requester
        secure_dir_request.save()


def unset_request_pis(apps, schema_editor):
    """Unset the PI for all requests."""
    SecureDirRequest = apps.get_model('allocation', 'SecureDirRequest')
    for secure_dir_request in SecureDirRequest.objects.all():
        secure_dir_request.pi = None
        secure_dir_request.save()


class Migration(migrations.Migration):

    dependencies = [
        ('allocation', '0016_securedirrequest_pi'),
    ]

    operations = [
        migrations.RunPython(
            set_request_pis_to_requesters, unset_request_pis)
    ]
