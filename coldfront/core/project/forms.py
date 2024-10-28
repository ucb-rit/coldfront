from django import forms
from django.core.validators import MinLengthValidator
from django.shortcuts import get_object_or_404
from django.db.models import Q

from coldfront.core.project.models import (Project, ProjectReview,
                                           ProjectUserRoleChoice)
from coldfront.core.project.utils_.new_project_utils import non_denied_new_project_request_statuses, pis_with_new_project_requests_pks, project_pi_pks
from coldfront.core.project.utils_.renewal_utils import non_denied_renewal_request_statuses, pis_with_renewal_requests_pks
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.user.models import UserProfile
from django.contrib.auth.models import User 
from coldfront.core.user.utils_.host_user_utils import eligible_host_project_users
from coldfront.core.utils.common import import_from_settings
from coldfront.core.resource.utils import get_compute_resource_names

import datetime
from flags.state import flag_enabled


EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL = import_from_settings(
    'EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL')
EMAIL_ADMIN_LIST = import_from_settings('EMAIL_ADMIN_LIST', [])
EMAIL_DIRECTOR_EMAIL_ADDRESS = import_from_settings(
    'EMAIL_DIRECTOR_EMAIL_ADDRESS', '')


class ProjectSearchForm(forms.Form):
    """ Search form for the Project list page.
    """
    LAST_NAME = 'Last Name (PI)'
    USERNAME = 'Username (PI)'
    FIELD_OF_SCIENCE = 'Division or Department'
    PROJECT_TITLE = 'Project Title'
    PROJECT_NAME = 'Project Name'
    CLUSTER_NAME = 'Cluster Name'

    last_name = forms.CharField(label=LAST_NAME, max_length=100, required=False)
    username = forms.CharField(label=USERNAME, max_length=100, required=False)
    # field_of_science = forms.CharField(label=FIELD_OF_SCIENCE, max_length=100, required=False)
    project_title = forms.CharField(label=PROJECT_TITLE, max_length=100, required=False)
    project_name = forms.CharField(label=PROJECT_NAME, max_length=100, required=False)
    cluster_name = forms.ChoiceField(label=CLUSTER_NAME,
                                     required=False,
                                     widget=forms.Select())
    show_all_projects = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cluster_name_choices = \
            [('', '-----')] + \
            [(x, x) for x in get_compute_resource_names()]
        self.fields['cluster_name'].choices = cluster_name_choices


class ProjectAddUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    source = forms.CharField(max_length=16, disabled=True)
    role = forms.ModelChoiceField(
        queryset=ProjectUserRoleChoice.objects.all().filter(~Q(name='Principal Investigator')),
        empty_label=None)
    selected = forms.BooleanField(initial=False, required=False)
    user_access_agreement = forms.CharField(max_length=16, required=False, disabled=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._username = kwargs.get('initial', {}).get('username', None)


class ProjectAddUsersToAllocationForm(forms.Form):
    allocation = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={'checked': 'checked'}), required=False)

    def __init__(self, request_user, project_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)

        allocation_query_set = project_obj.allocation_set.filter(
            status__name__in=['Active', 'New', 'Renewal Requested', ], resources__is_allocatable=True, is_locked=False)
        allocation_choices = [(allocation.id, "%s (%s) %s" % (allocation.get_parent_resource.name, allocation.get_parent_resource.resource_type.name,
                                                              allocation.description if allocation.description else '')) for allocation in allocation_query_set]
        allocation_choices.insert(0, ('__select_all__', 'Select All'))
        if allocation_query_set:
            self.fields['allocation'].choices = allocation_choices
            self.fields['allocation'].help_text = '<br/>Select allocations to add selected users to.'
        else:
            self.fields['allocation'].widget = forms.HiddenInput()


class ProjectUserUpdateForm(forms.Form):
    role = forms.ModelChoiceField(
        queryset=ProjectUserRoleChoice.objects.all().filter(~Q(name='Principal Investigator')),
        empty_label=None)
    enable_notifications = forms.BooleanField(initial=False, required=False)


class ProjectReviewForm(forms.Form):
    reason = forms.CharField(label='Reason for not updating project information', widget=forms.Textarea(attrs={
                             'placeholder': 'If you have no new information to provide, you are required to provide a statement explaining this in this box. Thank you!'}), required=False)
    acknowledgement = forms.BooleanField(
        label='By checking this box I acknowledge that I have updated my project to the best of my knowledge', initial=False, required=True)

    def __init__(self, project_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)
        now = datetime.datetime.now(datetime.timezone.utc)

        """
        if project_obj.grant_set.exists():
            latest_grant = project_obj.grant_set.order_by('-modified')[0]
            grant_updated_in_last_year = (
                now - latest_grant.created).days < 365
        else:
            grant_updated_in_last_year = None
        """

        """
        if project_obj.publication_set.exists():
            latest_publication = project_obj.publication_set.order_by(
                '-created')[0]
            publication_updated_in_last_year = (
                now - latest_publication.created).days < 365
        else:
            publication_updated_in_last_year = None
        """

        """
        if grant_updated_in_last_year or publication_updated_in_last_year:
            self.fields['reason'].widget = forms.HiddenInput()
        else:
            self.fields['reason'].required = True
        """


class ProjectReviewEmailForm(forms.Form):
    cc = forms.CharField(
        required=False
    )
    email_body = forms.CharField(
        required=True,
        widget=forms.Textarea
    )

    def __init__(self, pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_review_obj = get_object_or_404(ProjectReview, pk=int(pk))
        self.fields['email_body'].initial = 'Dear {} managers \n{}'.format(
            project_review_obj.project.name,
            EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL)
        self.fields['cc'].initial = ', '.join(
            [EMAIL_DIRECTOR_EMAIL_ADDRESS] + EMAIL_ADMIN_LIST)


class ProjectReviewUserJoinForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    role = forms.CharField(max_length=30, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)
    reason = forms.CharField(max_length=1000, required=False, disabled=True)


class ProjectUpdateForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = (
            'title', 'description',) #'field_of_science',


class DisabledChoicesSelectWidget(forms.Select):

    def __init__(self, *args, **kwargs):
        self.disabled_choices = kwargs.pop('disabled_choices', set())
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None,
                      attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex,
            attrs=attrs)
        try:
            if int(str(value)) in self.disabled_choices:
                option['attrs']['disabled'] = True
        except Exception:
            pass
        return option


class MemorandumSignedForm(forms.Form):

    status = forms.ChoiceField(
        choices=(
            ('', 'Select one.'),
            ('Pending', 'Pending'),
            ('Complete', 'Complete'),
        ),
        help_text='If you are unsure, leave the status as "Pending".',
        label='Status',
        required=True)


class ReviewDenyForm(forms.Form):

    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision. It will be included in the '
            'notification email.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=True,
        widget=forms.Textarea(attrs={'rows': 3}))

class ReviewDenyForm(forms.Form):

    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision. It will be included in the '
            'notification email.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=True,
        widget=forms.Textarea(attrs={'rows': 3}))


class ReviewStatusForm(forms.Form):

    status = forms.ChoiceField(
        choices=(
            ('', 'Select one.'),
            ('Pending', 'Pending'),
            ('Approved', 'Approved'),
            ('Denied', 'Denied'),
        ),
        help_text='If you are unsure, leave the status as "Pending".',
        label='Status',
        required=True)
    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision. This field is only required '
            'for denials, since it will be included in the notification '
            'email.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}))

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status', 'Pending')
        # Require justification for denials.
        if status == 'Denied':
            justification = cleaned_data.get('justification', '')
            if not justification.strip():
                raise forms.ValidationError(
                    'Please provide a justification for your decision.')
        return cleaned_data


# note: from coldfront\core\project\forms_\new_project_forms\request_forms.py
class PIChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return f'{obj.first_name} {obj.last_name} ({obj.email})'

class ReviewEligibilityForm(ReviewStatusForm):

    PI = PIChoiceField(
        label='Principal Investigator',
        queryset=User.objects.none(),
        required=False,
        widget=DisabledChoicesSelectWidget(),
        help_text= 'Please confirm the PI for this project. If the PI is ' \
                   'listed, select them from the dropdown and do not fill ' \
                   'out the PI information fields. If the PI is not ' \
                   'listed, empty the field and provide the PI\'s ' \
                   'information below.')
    first_name = forms.CharField(max_length=30, required=False)
    middle_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(max_length=100, required=False)

    field_order=['PI', 'first_name', 'middle_name', 'last_name', 'email',
                 'status', 'justification']

    def __init__(self, *args, **kwargs):
        self.computing_allowance = kwargs.pop('computing_allowance', None)
        self.allocation_period = kwargs.pop('allocation_period', None)
        super().__init__(*args, **kwargs)
        if self.computing_allowance is not None:
            self.computing_allowance = ComputingAllowance(
                self.computing_allowance)
            self.disable_pi_choices()
        self.exclude_pi_choices()

    def clean(self):
        cleaned_data = super().clean()
        pi = self.cleaned_data['PI']
        if pi is not None and pi not in self.fields['PI'].queryset:
            raise forms.ValidationError(f'Invalid selection {pi.username}.')
        return cleaned_data

    def disable_pi_choices(self):
        """Prevent certain Users, who should be displayed, from being
        selected as PIs."""
        disable_user_pks = set()

        if self.computing_allowance.is_one_per_pi() and self.allocation_period:
            # Disable any PI who has:
            #     (a) an existing Project with the allowance*,
            #     (b) a new project request for a Project with the allowance
            #         during the AllocationPeriod*, or
            #     (c) an allowance renewal request for a Project with the
            #         allowance during the AllocationPeriod*.
            # * Projects/requests must have ineligible statuses.
            resource = self.computing_allowance.get_resource()
            project_status_names = ['New', 'Active', 'Inactive']
            disable_user_pks.update(
                project_pi_pks(
                    computing_allowance=resource,
                    project_status_names=project_status_names))
            new_project_request_status_names = list(
                non_denied_new_project_request_statuses().values_list(
                    'name', flat=True))
            disable_user_pks.update(
                pis_with_new_project_requests_pks(
                    self.allocation_period,
                    computing_allowance=resource,
                    request_status_names=new_project_request_status_names))
            renewal_request_status_names = list(
                non_denied_renewal_request_statuses().values_list(
                    'name', flat=True))
            disable_user_pks.update(
                pis_with_renewal_requests_pks(
                    self.allocation_period,
                    computing_allowance=resource,
                    request_status_names=renewal_request_status_names))

        if flag_enabled('LRC_ONLY'):
            # On LRC, PIs must be LBL employees.
            non_lbl_employees = set(
                [user.pk for user in User.objects.all()
                 if not is_lbl_employee(user)])
            disable_user_pks.update(non_lbl_employees)

        self.fields['PI'].widget.disabled_choices = disable_user_pks

    def exclude_pi_choices(self):
        """Exclude certain Users from being displayed as PI options."""
        # Exclude any user that does not have an email address or is inactive.
        self.fields['PI'].queryset = User.objects.exclude(
            Q(email__isnull=True) | Q(email__exact='') | Q(is_active=False))

    @staticmethod
    def label_from_instance(obj):
        return f'{obj.first_name} {obj.last_name} ({obj.email})'

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status', 'Pending')
        # Require justification for denials.
        if status == 'Denied':
            justification = cleaned_data.get('justification', '')
            if not justification.strip():
                raise forms.ValidationError(
                    'Please provide a justification for your decision.')
        return cleaned_data


class JoinRequestSearchForm(forms.Form):
    project_name = forms.CharField(label='Project Name',
                                   max_length=100, required=False)
    username = forms.CharField(
        label='Username', max_length=100, required=False)
    email = forms.CharField(label='Email', max_length=100, required=False)


class ProjectSelectHostUserForm(forms.Form):

    host_user = forms.ChoiceField(
        label='Host User',
        choices=[],
        widget=forms.Select(),
        required=True)

    def __init__(self, *args, **kwargs):
        project_name = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        if project_name:
            project = Project.objects.get(name=project_name)
            eligible_hosts = eligible_host_project_users(project)
            choices = [('', 'Select a host user.')]
            for project_user in eligible_hosts:
                user = project_user.user
                choices.append((
                    user,
                    f'{user.first_name} {user.last_name} ({user.username})'
                ))
            self.fields['host_user'].choices = choices
