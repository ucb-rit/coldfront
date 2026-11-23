from allauth.account.urls import urlpatterns as all_patterns
from django.urls import path
from django.views.generic import TemplateView
from flags.urls import flagged_paths

"""Include a subset of patterns from allauth.account."""


urlpatterns = []


names_to_include = {
    "account_email_verification_sent",
    "account_confirm_email",
}
for pattern in all_patterns:
    if pattern.name in names_to_include:
        urlpatterns.append(pattern)


# Serve the inactive account page with a plain TemplateView. Since 65.16,
# allauth's view reverses "account_login" (and optionally "account_signup") to
# build context the template does not use, and this project does not include
# those patterns.
for pattern in all_patterns:
    if pattern.name == "account_inactive":
        urlpatterns.append(
            path(
                str(pattern.pattern),
                TemplateView.as_view(template_name="account/account_inactive.html"),
                name=pattern.name,
            )
        )


# Only include the view for managing emails if users are allowed to have
# multiple emails.
names_to_include_if_multiple_emails_allowed = {
    "account_email",
}
with flagged_paths("MULTIPLE_EMAIL_ADDRESSES_ALLOWED") as f_path:
    for pattern in all_patterns:
        if pattern.name in names_to_include_if_multiple_emails_allowed:
            urlpatterns.append(
                f_path(
                    str(pattern.pattern),
                    pattern.callback,
                    pattern.default_args,
                    pattern.name,
                )
            )
