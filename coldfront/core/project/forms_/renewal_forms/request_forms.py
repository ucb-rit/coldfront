from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.forms import DisabledChoicesSelectWidget
from coldfront.core.project.forms_.new_project_forms.request_forms import PooledProjectChoiceField
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.new_project_utils import non_denied_new_project_request_statuses
from coldfront.core.project.utils_.new_project_utils import pis_with_new_project_requests_pks
from coldfront.core.project.utils_.renewal_utils import non_denied_renewal_request_statuses
from coldfront.core.project.utils_.renewal_utils import pis_with_renewal_requests_pks
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface

from flags.state import flag_enabled
from django import forms
from django.utils.safestring import mark_safe
from django.core.validators import MinLengthValidator


class ProjectRenewalPIChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        user = obj.user
        return f'{user.first_name} {user.last_name} ({user.email})'


class ProjectRenewalPISelectionForm(forms.Form):

    PI = ProjectRenewalPIChoiceField(
        label='Principal Investigator',
        queryset=ProjectUser.objects.none(),
        required=True,
        widget=DisabledChoicesSelectWidget())

    def __init__(self, *args, **kwargs):
        self.computing_allowance = kwargs.pop('computing_allowance', None)
        self.allocation_period_pk = kwargs.pop('allocation_period_pk', None)
        self.project_pks = kwargs.pop('project_pks', None)
        super().__init__(*args, **kwargs)

        if not (self.computing_allowance and self.allocation_period_pk
                and self.project_pks):
            return

        self.computing_allowance = ComputingAllowance(self.computing_allowance)
        self.allocation_period = AllocationPeriod.objects.get(
            pk=self.allocation_period_pk)

        role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')
        status = ProjectUserStatusChoice.objects.get(name='Active')

        pi_project_users = ProjectUser.objects.prefetch_related('user').filter(
            project__pk__in=self.project_pks, role=role, status=status
        ).order_by('user__last_name', 'user__first_name')

        self.fields['PI'].queryset = pi_project_users
        self.disable_pi_choices(pi_project_users)

    def disable_pi_choices(self, pi_project_users):
        """Prevent certain of the given ProjectUsers, who should be
        displayed, from being selected for renewal."""
        disable_project_user_pks = set()
        if self.computing_allowance.is_one_per_pi():
            # Disable any PI who has:
            #    (a) a new project request for a Project during the
            #        AllocationPeriod*, or
            #    (b) an AllocationRenewalRequest during the AllocationPeriod*.
            # * Requests must have ineligible statuses.
            resource = self.computing_allowance.get_resource()
            disable_user_pks = set()
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
            for project_user in pi_project_users:
                if project_user.user.pk in disable_user_pks:
                    disable_project_user_pks.add(project_user.pk)
        self.fields['PI'].widget.disabled_choices = disable_project_user_pks


class ProjectRenewalPoolingPreferenceForm(forms.Form):

    UNPOOLED_TO_UNPOOLED = AllocationRenewalRequest.UNPOOLED_TO_UNPOOLED
    UNPOOLED_TO_POOLED = AllocationRenewalRequest.UNPOOLED_TO_POOLED
    POOLED_TO_POOLED_SAME = AllocationRenewalRequest.POOLED_TO_POOLED_SAME
    POOLED_TO_POOLED_DIFFERENT = \
        AllocationRenewalRequest.POOLED_TO_POOLED_DIFFERENT
    POOLED_TO_UNPOOLED_OLD = AllocationRenewalRequest.POOLED_TO_UNPOOLED_OLD
    POOLED_TO_UNPOOLED_NEW = AllocationRenewalRequest.POOLED_TO_UNPOOLED_NEW

    SHORT_DESCRIPTIONS = {
        UNPOOLED_TO_UNPOOLED: 'Stay Unpooled',
        UNPOOLED_TO_POOLED: 'Start Pooling',
        POOLED_TO_POOLED_SAME: 'Stay Pooled, Same Project',
        POOLED_TO_POOLED_DIFFERENT: 'Pool with Different Project',
        POOLED_TO_UNPOOLED_OLD: 'Unpool, Renew Existing Project',
        POOLED_TO_UNPOOLED_NEW: 'Unpool, Create New Project',
    }

    non_pooled_choices = [
        (UNPOOLED_TO_UNPOOLED,
            'Renew the PI\'s allowance under the same project.'),
        (UNPOOLED_TO_POOLED,
            'Pool the PI\'s allowance under a different project.'),
    ]

    pooled_choices = [
        (POOLED_TO_POOLED_SAME,
            'Continue pooling the PI\'s allowance under the same project.'),
        (POOLED_TO_POOLED_DIFFERENT,
            'Pool the PI\'s allowance under a different project.'),
        (POOLED_TO_UNPOOLED_OLD,
            ('Stop pooling the PI\'s allowance. Select another project owned '
             'by the PI to renew under.')),
        (POOLED_TO_UNPOOLED_NEW,
            ('Stop pooling the PI\'s allowance. Create a new project to '
             'renew under.')),
    ]

    preference = forms.ChoiceField(choices=[], widget=forms.RadioSelect())

    def __init__(self, *args, **kwargs):
        # Raise an exception if 'currently_pooled' is not provided.
        self.currently_pooled = kwargs.pop('currently_pooled')
        super().__init__(*args, **kwargs)
        if self.currently_pooled:
            choices = self.pooled_choices
        else:
            choices = self.non_pooled_choices
        self.fields['preference'].choices = choices


class ProjectRenewalProjectSelectionForm(forms.Form):

    project = PooledProjectChoiceField(
        empty_label=None,
        queryset=Project.objects.none(),
        required=True,
        widget=forms.Select())

    def __init__(self, *args, **kwargs):
        self.computing_allowance = kwargs.pop('computing_allowance', None)
        # Raise an exception if certain kwargs are not provided.
        for key in ('pi_pk', 'non_owned_projects', 'exclude_project_pk'):
            if key not in kwargs:
                raise KeyError(f'No {key} is provided.')
            else:
                setattr(self, key, kwargs.pop(key))
        super().__init__(*args, **kwargs)

        if not self.computing_allowance:
            return
        computing_allowance_interface = ComputingAllowanceInterface()
        self.computing_allowance = ComputingAllowance(self.computing_allowance)

        role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')
        status = ProjectUserStatusChoice.objects.get(name='Active')

        project_pks = list(
            ProjectUser.objects.select_related(
                'project'
            ).filter(
                user__pk=self.pi_pk, role=role, status=status
            ).values_list('project__pk', flat=True))

        _filter = {
            'name__startswith': computing_allowance_interface.code_from_name(
                self.computing_allowance.get_name()),
        }
        exclude = {'pk': self.exclude_project_pk}
        if self.non_owned_projects:
            # # Only include Projects where this user is not a PI.
            # exclude['pk__in'] = project_pks
            # A PI may wish to pool their allocation under a Project they are
            # already a PI on. Allow this.
            pass
        else:
            # Only include Projects where this user is a PI.
            _filter['pk__in'] = project_pks
        self.fields['project'].queryset = Project.objects.filter(
            **_filter).exclude(**exclude).order_by('name')

class ProjectRenewalSurveyForm(forms.Form):
    
    def __init__(self, *args, **kwargs):
        disable_fields = kwargs.pop('disable_fields', False)
        super().__init__(*args, **kwargs)
        self._update_field_attributes()
        if disable_fields:
            for field in self.fields:
                self.fields[field].disabled = True

    def _update_field_attributes(self):
        """Update field attributes with deployment-specific content."""
        if flag_enabled('BRC_ONLY'):
            self._update_brc_survey_fields()

        elif flag_enabled('LRC_ONLY'):
            self._update_lrc_survey_fields()

    def _update_brc_survey_fields(self):
        self.fields['which_brc_services_used'] = forms.MultipleChoiceField(
                choices=(
                    ('savio_hpc', (
                        'Savio High Performance Computing and consulting')),
                    ('condo_storage', (
                        'Condo storage on Savio')),
                    ('srdc', (
                        'Secure Research Data & Computing (SRDC)')),
                    ('aeod', (
                        'Analytic Environments on Demand')),
                    ('cloud_consulting', (
                        'Cloud consulting (e.g., Amazon, Google, Microsoft, ' 
                        'XSEDE, UCB\'s Cloud Working Group)')),
                    ('other', (
                        'Other BRC consulting (e.g. assessing the '
                        'computation platform or resources appropriate '
                        'for your research workflow)')),
                    ('none', (
                        'None of the above')),
                ),
                label='1. Which Berkeley Research Computing services have you'
                 ' used? (Check all that apply.)',
                required=True,
                widget=forms.CheckboxSelectMultiple())
            
        self.fields['publications_supported_by_brc'] = forms.CharField(
                label='2. Please list any publications (including papers, books, '
                'dissertations, theses, and public presentations) that you '
                'authored or co-authored, that have been supported by '
                'Berkeley Research Computing resources and/or consulting. '
                'Please provide a bibliographic reference, URL or DOI for '
                'each publication/presentation. Please write \'N/A\' if this does not apply.',
                required=True,
                validators=[MinLengthValidator(20)],
                widget=forms.Textarea(attrs={'rows': 3}))

        self.fields['grants_supported_by_brc'] = forms.CharField(
                label='3. Please list any grant(s) or other competitively-'
                'awarded funding that has been or will be supported by '
                'Berkeley Research Computing resources and/or consulting. '
                'Please provide the name of the funding agency, the award '
                'number or other identifier, and the amount of funding awarded. '
                'Please write \'N/A\' if this does not apply.',
                required=True,
                widget=forms.Textarea(attrs={'rows': 3}))
            
        self.fields['recruitment_or_retention_cases'] = forms.CharField(
                label='4. Please list any recruitment or retention cases you '
                'are aware of in which the availability of the Savio '
                'high-performance computing cluster or other Berkeley '
                'Research Computing services -- such as Condo Storage, '
                'Analytic Environments on Demand (AEoD), or Cloud Computing '
                'Support  -- played a role? Please indicate the recruitment / '
                'retention case role (faculty, postdoc, or graduate student), '
                'department, sponsoring faculty member, and outcome. This '
                'information will not be shared publicly, except as a '
                'component of aggregated statistics. '
                'Please write \'N/A\' if this does not apply.',
                required=True,
                widget=forms.Textarea(attrs={'rows': 3}))
            
        self.fields['classes_being_taught'] = forms.CharField(
                label='5. Please list any classes (course number and semester) '
                'for which you were/will be an instructor, and that were or '
                'will be supported by the Berkeley Research Computing Program. '
                'Please indicate whether an Instructional Computing Allowance '
                '(ICA) was, is, or will be an element of support for the '
                'listed classes. More on ICAs '
                '<a href="https://docs-research-it.berkeley.edu/services/high'
                '-performance-computing/getting-account/instructional-computing-allowance/"'
                'target="_blank" rel="noopener noreferrer">here</a>. '
                'Please write \'N/A\' if this does not apply.',
                required=True,
                widget=forms.Textarea(attrs={'rows': 3}))

        self.fields['brc_recommendation_rating'] = forms.ChoiceField(
                choices=(
                    ('1', (
                        '1 - Not at all likely')),
                    ('2', (
                        '2')),
                    ('3', (
                        '3')),
                    ('4', (
                        '4')),
                    ('5', (
                        '5')),
                    ('6', (
                        '6')),
                    ('7', (
                        '7')),
                    ('8', (
                        '8')),
                    ('9', (
                        '9')),
                    ('10', (
                        '10 - Very likely')),
                ),
                label=(
                    '6. Based upon your overall experience using BRC services, '
                    'how likely are you to recommend Berkeley Research '
                    'Computing to others?'),
                required=True,
                widget=forms.RadioSelect())
            
        self.fields['brc_recommendation_rating_reason'] = forms.CharField(
                label='6a. What is the reason for your rating above?',
                required=False,
                widget=forms.Textarea(attrs={'rows': 2}))
            
        self.fields['how_brc_helped_bootstrap_computational_methods'] = forms.CharField(
                label='7. If you are new to computational methods '
                '(broadly, or in a specific application), please '
                'let us know how BRC services and/or resources have '
                'helped you bootstrap the application of computational '
                'methods to your research. Please write \'N/A\' if this does not apply.',
                required=True,
                widget=forms.Textarea(attrs={'rows': 3}))
            
        self.fields['how_important_to_research_is_brc'] = forms.ChoiceField(
                choices=(
                    ('1', (
                        'Not at all important')),
                    ('2', (
                        'Somewhat important')),
                    ('3', (
                        'Important')),
                    ('4', (
                        'Very important')),
                    ('5', (
                        'Essential')),
                    ('6', (
                        'Not applicable')),
                ),
                label=(
                    '8. How important is the Berkeley Research Computing '
                    'Program to your research?'),
                required=True,
                widget=forms.RadioSelect())
            
        self.fields['do_you_use_mybrc'] = forms.ChoiceField(
                choices=(
                    ('yes', (
                        'Yes')),
                    ('no', (
                        'No')),
                ),
                label=(
                    '9. Do you use the Savio Account Management portal '
                    'MyBRC?'),
                required=True,
                widget=forms.RadioSelect())
            
        self.fields['mybrc_comments'] = forms.CharField(
                label=('9a.If yes, what feedback do you have for MyBRC?'),
                required=False,
                widget=forms.Textarea(attrs={'rows': 2}))
            
        self.fields['which_open_ondemand_apps_used'] = forms.MultipleChoiceField(
                choices=(
                    ('desktop', (
                        'Desktop')),
                    ('matlab', (
                        'MatLab')),
                    ('jupyter_notebook', (
                        'Jupyter Notebook/Lab')),
                    ('vscode_server', (
                        'VS Code Server')),
                    ('none', (
                        'None of the above')),
                    ('other', (
                        'Other')),
                ),
                label=(
                    '10. Do you use Open Ondemand? Which '
                    'application(s) do you use? (Check all that apply.)'),
                required=True,
                widget=forms.CheckboxSelectMultiple())
            
        self.fields['brc_feedback'] = forms.CharField(
                label=(
                    '11. How could the Berkeley Research Computing '
                    'Program be more useful to your research or teaching?'),
                required=False,
                widget=forms.Textarea(attrs={'rows': 2}))
            
        self.fields['colleague_suggestions'] = forms.CharField(
                label=(
                    '12. Please suggest colleagues who might benefit from the '
                    'Berkeley Research Computing Program, with whom we '
                    'should follow up. Names, e-mail addresses, and roles '
                    '(faculty, postdoc, graduate student, etc.) would be '
                    'most helpful.'),
                required=False,
                widget=forms.Textarea(attrs={'rows': 3}))
            
        self.fields['indicate_topic_interests'] = forms.MultipleChoiceField(
                choices=(
                    ('have_visited_rdmp_website', (
                        'I have visited the Research Data Management '
                        'Program web site.')),
                    ('have_had_rdmp_event_or_consultation', (
                        mark_safe('I have participated in a '
                        '<a href="http://researchdata.berkeley.edu/">'
                        'Research Data Management Program</a>'
                        ' event or consultation.'
                        ))),
                    ('want_to_learn_more_and_have_rdm_consult', (
                        'I am interested in the Research Data Management Program; '
                        'please have an RDM consultant follow up with me.')),
                    ('want_to_learn_security_and_have_rdm_consult', (
                        'I am interested in learning more about securing research '
                        'data and/or secure computation; please have an RDM consultant '
                        'follow up with me.')),
                    ('interested_in_visualization_services', (
                        'I am interested in resources or services that support '
                        'visualization of research data.')),
                    ('none_of_the_above', (
                        'None of the above.'
                    ))
                ),
                label=(
                    '13. Please indicate your engagement with or '
                    'interest in the following topics. (Check all that apply.)'),
                required=True,
                widget=forms.CheckboxSelectMultiple())

        self.fields['training_session_usefulness_of_computational_platforms_training'] = forms.ChoiceField(
                choices=(
                    ('1', (
                        '1 - Not useful')),
                    ('2', (
                        '2')),
                    ('3', (
                        '3')),
                    ('4', (
                        '4')),
                    ('5', (
                        '5 - Very useful')),
                ),
                label=(
                    mark_safe('<h4>BRC is planning an in-person training session within'
                    ' the next 2-3 months and would like input on what topics would be '
                    'most useful to you personally. Please rate the following topics on '
                    ' how useful they would be to you.</h4>'
                    '14a. Selecting computational platforms that fit your research and '
                    'budget (Savio, HPC@UC, XSEDE, commercial cloud providers, AEoD) '
                    'System overview (how to access Savio via condo contribution '
                    'or faculty compute allowance, system capabilities)')),
                required=False,
                widget=forms.RadioSelect())
            
        self.fields['training_session_usefulness_of_basic_savio_cluster'] = forms.ChoiceField(
                choices=(
                    ('1', (
                        '1 - Not useful')),
                    ('2', (
                        '2')),
                    ('3', (
                        '3')),
                    ('4', (
                        '4')),
                    ('5', (
                        '5 - Very useful')),
                ),
                label=(
                    '14b. Basic usage of the Savio cluster (logging on, data transfer, accessing '
                    'software, using the scheduler; limited discussion of access models and '
                    'capabilities)'),
                required=False,
                widget=forms.RadioSelect())
            
        self.fields['training_session_usefulness_of_advanced_savio_cluster'] = forms.ChoiceField(
                choices=(
                    ('1', (
                        '1 - Not useful')),
                    ('2', (
                        '2')),
                    ('3', (
                        '3')),
                    ('4', (
                        '4')),
                    ('5', (
                        '5 - Very useful')),
                ),
                label=(
                    '14c. Advanced usage of the Savio cluster (e.g. installing your own software, '
                    'parallelization strategies, effective use of specific system resources '
                    'such as GPUs and Hadoop/Spark -- please indicate specific interests '
                    'below)'),
                required=False,
                widget=forms.RadioSelect())
            
        self.fields['training_session_usefulness_of_singularity_on_savio'] = forms.ChoiceField(
                choices=(
                    ('1', (
                        '1 - Not useful')),
                    ('2', (
                        '2')),
                    ('3', (
                        '3')),
                    ('4', (
                        '4')),
                    ('5', (
                        '5 - Very useful')),
                ),
                label=(
                    '14d. Use of Singularity on Savio (containerized applications, including Docker '
                    'containers packaged for Savio deployment)'),
                required=False,
                widget=forms.RadioSelect())
            
        self.fields['training_session_usefulness_of_analytic_envs_on_demand'] = forms.ChoiceField(
                choices=(
                    ('1', (
                        '1 - Not useful')),
                    ('2', (
                        '2')),
                    ('3', (
                        '3')),
                    ('4', (
                        '4')),
                    ('5', (
                        '5 - Very useful')),
                ),
                label=(
                    '14e. Use of Analytic Environments on Demand (virtualized, scalable Windows '
                    'environments provisioned with licensed or open-source software '
                    'applications applicable to research projects)'),
                required=False,
                widget=forms.RadioSelect())

        self.fields['training_session_other_topics_of_interest'] = forms.CharField(
                label=('15. Any other or specific topics of interest?'),
                required=False,
                widget=forms.Textarea(attrs={'rows': 2}))
    def _update_lrc_survey_fields(self):
        # TODO: Replace placeholders with LRC Survey Questions
        self.fields['question_1'] = forms.CharField(
                label='Question 1',
                required=True,
                widget=forms.Textarea(attrs={'rows': 3})
                )

        self.fields['question_2'] = forms.CharField(
                label='Question 2',
                required=True,
                widget=forms.Textarea(attrs={'rows': 3}))
        
        self.fields['question_3'] = forms.MultipleChoiceField(
            choices=(
                ('1', (
                    '1')),
                ('2', (
                    '2')),
                ('3', (
                    '3')),
            ),
            label=(
                'LRC Choose an option:'),
            required=False,
            widget=forms.CheckboxSelectMultiple())


class ProjectRenewalReviewAndSubmitForm(forms.Form):

    confirmation = forms.BooleanField(
        label=(
            'I have reviewed my selections and understand the changes '
            'described above. Submit my request.'),
        required=True)
