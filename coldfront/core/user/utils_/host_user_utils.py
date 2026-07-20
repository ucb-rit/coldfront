from django.contrib.auth.models import User
from django.db.models import Q

from allauth.account.models import EmailAddress


def eligible_host_project_users(project):
    """Return a list of ProjectUser objects associated with the given
    Project that are eligible to be hosts for external users.

    In particular, return active PIs who are LBL employees."""
    active_pis = project.projectuser_set.filter(
        role__name='Principal Investigator', status__name='Active').distinct()
    return [pi for pi in active_pis if is_lbl_employee(pi.user)]


def host_user_lbl_email(user):
    """Given a User, return the LBL email address of the user's host
    user if they have one, else None."""
    host_user = user.userprofile.host_user
    if not host_user:
        return None
    return lbl_email_address(host_user)


def is_lbl_employee(user):
    """Return whether the given User is an LBL employee."""
    return bool(lbl_email_address(user))


def lbl_employees():
    """Return a queryset of Users who are LBL employees.

    A user is considered an LBL employee if their primary email ends
    with '@lbl.gov', or if they have a verified EmailAddress ending
    with '@lbl.gov'. Bulk queryset equivalent of is_lbl_employee().
    """
    domain = '@lbl.gov'
    lbl_email_user_ids = EmailAddress.objects.filter(
        verified=True, email__endswith=domain
    ).values('user_id')
    return User.objects.filter(
        Q(email__endswith=domain) | Q(pk__in=lbl_email_user_ids)
    )


def lbl_email_address(user):
    """Return the LBL email address (str) of the given User if they have
    one, else None."""
    assert isinstance(user, User)
    email_domain = '@lbl.gov'
    if user.email.endswith(email_domain):
        return user.email
    email_addresses = EmailAddress.objects.filter(
        user=user, verified=True, email__endswith=email_domain).order_by(
            'email')
    if not email_addresses.exists():
        return None
    return email_addresses.first().email


def needs_host(user):
    """Return whether the given User needs a host user."""
    assert isinstance(user, User)
    return not bool(user.userprofile.host_user)
