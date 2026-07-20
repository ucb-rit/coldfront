import re

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Model, QuerySet
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse

from coldfront.core.project.models import Project


class ListFilterMixin:
    """Mixin for list views with server-side sorting, filtering, and pagination.

    Centralizes the three pieces of boilerplate duplicated across every
    request-queue list view: sort-param parsing, filter_parameters string
    building, and manual Paginator application.
    """

    paginate_by = 25

    def get_order_by(self, default="-id"):
        """Return the queryset order_by string derived from GET params."""
        order_by = self.request.GET.get("order_by")
        if order_by:
            direction = "" if self.request.GET.get("direction") == "asc" else "-"
            return direction + order_by
        return default

    def build_filter_parameters(self, data):
        """Build a ``key=value&`` query string from a dict of filter values.

        Empty/falsy values are omitted. Model instances (from
        ``ModelChoiceField``) are serialized as their PK. QuerySets (from
        ``ModelMultipleChoiceField``) emit one ``key=pk`` pair per element.
        """
        result = ""
        for k, v in data.items():
            if not v and v != 0:
                continue
            if isinstance(v, Model):
                result += f"{k}={v.pk}&"
            elif isinstance(v, QuerySet):
                for ele in v:
                    result += f"{k}={ele.pk}&"
            else:
                result += f"{k}={v}&"
        return result

    def paginate(self, queryset, context):
        """Apply pagination to *queryset* and populate *context*.

        Sets ``page_obj`` and ``is_paginated`` on the context dict and
        returns the current ``Page`` object.
        """
        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get("page")
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        context["page_obj"] = page_obj
        context["is_paginated"] = paginator.num_pages > 1
        return page_obj


class SnakeCaseTemplateNameMixin:
    # by default:
    # Django converts the model class name to simply lowercase (i.e. not snake_case)
    # however, we use snake_case filename style throughout coldfront
    #
    # thus, for consistency:
    # override get_template_names() to use snake_case instead of simply lowercase

    def get_template_names(self):
        def to_snake(string):
            # note that this is an oversimplified implementation
            # it should work in the majority of cases, even allowing us to change app/class/etc. names
            # but cases like DOIDisplay (or similar, using multiple caps in a row) would fail

            return string[0].lower() + re.sub("([A-Z])", r"_\1", string[1:]).lower()

        app_label = self.model._meta.app_label
        model_name = self.model.__name__

        return [
            "{}/{}{}.html".format(
                app_label, to_snake(model_name), self.template_name_suffix
            )
        ]


class ProjectInContextMixin:
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["project"] = get_object_or_404(
            Project, pk=self.kwargs.get("project_pk")
        )

        return context


class ChangesOnlyOnActiveProjectMixin:
    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))
        if project_obj.status.name not in [
            "Active",
            "New",
        ]:
            messages.error(request, "You cannot modify an archived project.")
            return HttpResponseRedirect(
                reverse("project-detail", kwargs={"pk": project_obj.pk})
            )
        else:
            return super().dispatch(request, *args, **kwargs)


class UserActiveManagerOrHigherMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        if project_obj.projectuser_set.filter(
            user=self.request.user,
            role__name__in=["Manager", "Principal Investigator"],
            status__name="Active",
        ).exists():
            return True
