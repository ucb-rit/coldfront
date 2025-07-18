from flags.state import flag_enabled

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.html import mark_safe
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _

from allauth.account.models import EmailAddress

from coldfront.core.user.utils import send_account_activation_email
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.mail import dummy_email_address


class UserSearchForm(forms.Form):
    CHOICES = [('username_only', 'Exact Username Only'),
               # ('all_fields', mark_safe('All Fields <a href="#" data-toggle="popover" data-trigger="focus" data-content="This option will be ignored if multiple usernames are specified."><i class="fas fa-info-circle"></i></a>')),
               ('all_fields', mark_safe('All Fields <span class="text-secondary">This option will be ignored if multiple usernames are entered in the search user text area.</span>')),
               ]
    q = forms.CharField(label='Search String', min_length=2, widget=forms.Textarea(attrs={'rows': 4}),
                        help_text='Copy paste usernames separated by space or newline for multiple username searches!')
    search_by = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect(), initial='username_only')

    search_by.widget.attrs.update({'rows': 4})


class UserSearchListForm(forms.Form):
    FIRST_NAME = 'First Name'
    MIDDLE_NAME = 'Middle Name'
    LAST_NAME = 'Last Name'
    USERNAME = 'Cluster Username'
    EMAIL = 'Email'

    first_name = forms.CharField(label=FIRST_NAME, max_length=100, required=False)
    middle_name = forms.CharField(label=MIDDLE_NAME, max_length=100, required=False)
    last_name = forms.CharField(label=LAST_NAME, max_length=100, required=False)
    username = forms.CharField(label=USERNAME, max_length=100, required=False)
    email = forms.EmailField(label=EMAIL, max_length=100, required=False,
            help_text=('You may use this field to find the user that an email address belongs to, even if it is not a primary address.'))


class UserRegistrationForm(UserCreationForm):

    email = forms.EmailField(
        label='Email Address', widget=forms.EmailInput(),
        help_text=(
            'If you have an @berkeley.edu email address, please provide it to '
            'avoid delays in processing. All communication is sent to this '
            'email. Please provide a valid address. If this communication '
            'address changes, it is your responsibility to update it in this '
            'portal.'))

    first_name = forms.CharField(
        label='First Name',
        help_text=(
            'Please specify actual, official names and avoid giving the short '
            'forms or casual names. For example, do NOT give \'Chris\' for '
            '\'Christopher\'.'))
    middle_name = forms.CharField(label='Middle Name', required=False)
    last_name = forms.CharField(label='Last Name')
    password1 = forms.CharField(
        help_text=(
            'This password is unique to this portal, and is separate from the '
            'PIN and OTP used to access the cluster.'),
        label='Enter Password', widget=forms.PasswordInput())
    password2 = forms.CharField(
        label='Confirm Password', widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        self.middle_name = ''
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if (User.objects.filter(username=email).exists() or
                User.objects.filter(email=email).exists() or
                EmailAddress.objects.filter(email=email).exists()):
            login_url = reverse('login')
            password_reset_url = reverse('password-reset')
            message = (
                f'A user with that email address already exists. If this is '
                f'you, please <a href="{login_url}">login</a> or <a href="'
                f'{password_reset_url}">set your password</a> to gain access. '
                f'You may then associate additional email addresses with your '
                f'account.')
            raise forms.ValidationError(mark_safe(message))
        return email

    def clean_first_name(self):
        self.first_name = self.cleaned_data['first_name'].title()
        return self.first_name

    def clean_middle_name(self):
        self.middle_name = self.cleaned_data['middle_name'].title()
        return self.middle_name

    def clean_last_name(self):
        self.last_name = self.cleaned_data['last_name'].title()
        return self.last_name

    def save(self, commit=True):
        model = super().save(commit=False)
        model.username = model.email
        model.is_active = False
        if commit:
            model.save()
        model.refresh_from_db()
        model.userprofile.middle_name = self.middle_name
        model.userprofile.save()
        return model

    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'middle_name', 'last_name', 'password1',
            'password2')


class UserLoginForm(AuthenticationForm):

    error_messages = {
        'invalid_login': _(
            'Please enter a correct username or verified email address, and '
            'password. Note that both fields may be case-sensitive.'),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = (
            f'This is your {settings.PROGRAM_NAME_SHORT} cluster account '
            f'username if you have one, or any of the verified email '
            f'addresses associated with your portal account, not your CalNet '
            f'username.')
        self.fields['password'].help_text = (
            f'This password is unique to this portal, and is neither your '
            f'CalNet password nor the PIN and OTP used to access the '
            f'{settings.PROGRAM_NAME_SHORT} cluster.')

    def clean_username(self):
        cleaned_data = super().clean()
        return cleaned_data.get('username').lower()
 
    def confirm_login_allowed(self, user):
        if not user.is_active:
            send_account_activation_email(user)
            raise forms.ValidationError(
                'Your account has been created, but is inactive. Please click '
                'the link sent to your email address to activate your '
                'account.', code='inactive')


class UserProfileUpdateForm(forms.Form):
    first_name = forms.CharField(label='First Name')
    middle_name = forms.CharField(label='Middle Name', required=False)
    last_name = forms.CharField(label='Last Name')

    def clean_first_name(self):
        return self.cleaned_data['first_name'].title()

    def clean_middle_name(self):
        return self.cleaned_data['middle_name'].title()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].title()


class UserAccessAgreementForm(forms.Form):

    POP_QUIZ_CHOICES = [
        ('1', '1'),
        ('2', '2'),
        ('24', '24'),
        ('48', '48'),
    ]

    pop_quiz_answer = forms.ChoiceField(
        choices=POP_QUIZ_CHOICES,
        label=(
            'You run a job that uses 2 of the 24 cores of a savio2 node, for '
            '1 hour. How many SUs have you used?'),
        required=True,
        widget=forms.RadioSelect())

    acknowledgement = forms.BooleanField(
        initial=False,
        label='Acknowledge & Sign',
        required=True)

    class Meta:
        model = UserProfile
        fields = ('pop_quiz_answer', 'acknowledgement', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not flag_enabled('BRC_ONLY'):
            self.fields.pop('pop_quiz_answer')
        self.set_acknowledgement_help_text()

    def clean_pop_quiz_answer(self):
        pop_quiz_answer = int(self.cleaned_data['pop_quiz_answer'])
        if pop_quiz_answer != 24:
            raise forms.ValidationError('Incorrect answer.')
        return pop_quiz_answer

    def set_acknowledgement_help_text(self):
        field = self.fields['acknowledgement']
        program_name_short = settings.PROGRAM_NAME_SHORT
        template = (
            f'I have read the {{0}} Policies and Procedures and understand my '
            f'responsibilities in the use of {program_name_short} computing '
            f'resources managed by the {{1}}.')
        if flag_enabled('BRC_ONLY'):
            field.help_text = template.format(
                'UC Berkeley', f'{program_name_short} Program')
        if flag_enabled('LRC_ONLY'):
            field.help_text = template.format('LBNL', 'LBNL IT Division')


class UserReactivateForm(forms.Form):

    email = forms.EmailField(max_length=100, required=True)


class VerifiedEmailAddressPasswordResetForm(PasswordResetForm):
    """A subclass of django.contrib.auth.forms.PasswordResetForm that
    uses EmailAddress."""

    @staticmethod
    def get_email_address(email):
        """Given an email, return a corresponding, verified EmailAddress
        if one exists, else None."""
        try:
            return EmailAddress.objects.select_related('user').get(
                email=email, verified=True, user__is_active=True)
        except EmailAddress.DoesNotExist:
            return None

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        """Generate a one-use only link for resetting password and send
        it to the user with which the provided email is associated."""
        email = self.cleaned_data['email'].lower()
        if not domain_override:
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain
        else:
            site_name = domain = domain_override
        email_address = self.get_email_address(email)
        if email_address is not None:
            user_email = email_address.email
            user = email_address.user
            context = {
                'email': user_email,
                'domain': domain,
                'site_name': site_name,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
                **(extra_email_context or {}),
            }
            self.send_mail(
                subject_template_name, email_template_name, context,
                from_email, user_email,
                html_email_template_name=html_email_template_name)

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email,
                  html_email_template_name=None):
        """Only send an email if email is enabled. Replace the to_email
        with a fake value if DEBUG is True."""
        if not settings.EMAIL_ENABLED:
            return
        if settings.DEBUG:
            to_email = dummy_email_address()
        super().send_mail(
            subject_template_name, email_template_name, context, from_email,
            to_email, html_email_template_name=html_email_template_name)
