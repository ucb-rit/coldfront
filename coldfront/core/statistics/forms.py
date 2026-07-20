from django import forms
from django.contrib.auth.models import User

from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.statistics.models import Job


class JobSearchForm(forms.Form):
    STATUS_CHOICES = [
        ("", "-----"),
        ("COMPLETING", "Completed"),
        ("NODE_FAIL", "Node Fail"),
        ("CANCELLED", "Cancelled"),
        ("FAILED", "Failed"),
        ("OUT_OF_MEMORY", "Out of Memory"),
        ("PREEMPTED", "Preempted"),
        ("REQUEUED", "Requeued"),
        ("RUNNING", "Running"),
        ("TIMEOUT", "Timeout"),
    ]

    status = forms.ChoiceField(
        label="Status", choices=STATUS_CHOICES, required=False, widget=forms.Select()
    )

    jobslurmid = forms.CharField(label="Slurm ID", max_length=150, required=False)

    project_name = forms.CharField(
        label="Project Name", max_length=100, required=False, widget=forms.Select()
    )

    username = forms.CharField(
        label="Username", max_length=150, required=False, widget=forms.Select()
    )

    partition = forms.CharField(
        label="Partition", max_length=100, required=False, widget=forms.Select()
    )

    submitdate_after = forms.DateField(
        label="Submitted After",
        widget=forms.DateInput(
            attrs={"class": "datepicker", "placeholder": "MM/DD/YYYY"}
        ),
        required=False,
    )

    submitdate_before = forms.DateField(
        label="Submitted Before",
        widget=forms.DateInput(
            attrs={"class": "datepicker", "placeholder": "MM/DD/YYYY"}
        ),
        required=False,
    )

    show_all_jobs = forms.BooleanField(
        initial=False, required=False, label="Show All Jobs"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        is_pi = kwargs.pop("is_pi", None)
        super().__init__(*args, **kwargs)

        project_queryset = Project.objects.all()
        user_queryset = User.objects.order_by("username")

        if user:
            if not (user.is_superuser or user.has_perm("statistics.view_job")):
                if not is_pi:
                    self.fields.pop("username")

                self.fields.pop("show_all_jobs")

                active_projects = (
                    ProjectUser.objects.filter(
                        user=user,
                        status__name="Active",
                    )
                    .distinct("project")
                    .values_list("project__name")
                )
                project_queryset = Project.objects.filter(name__in=active_projects)

                if is_pi:
                    managed_projects = ProjectUser.objects.filter(
                        user=user,
                        role__name__in=["Manager", "Principal Investigator"],
                        status__name__in=["Active", "Pending - Remove"],
                    ).values_list("project", flat=True)
                    pi_project_users = ProjectUser.objects.filter(
                        project__in=managed_projects,
                        status__name="Active",
                    ).values_list("user", flat=True)
                    user_queryset = User.objects.filter(
                        pk__in=pi_project_users,
                    ).order_by("username")

        self.fields["project_name"].widget.choices = [("", "-----")] + [
            (p.name, p.name) for p in project_queryset.iterator()
        ]

        if "username" in self.fields:
            self.fields["username"].widget.choices = [("", "-----")] + [
                (u.username, u.username) for u in user_queryset.iterator()
            ]

        partitions = (
            Job.objects.exclude(partition__isnull=True)
            .exclude(partition="")
            .order_by("partition")
            .values_list("partition", flat=True)
            .distinct()
        )
        self.fields["partition"].widget.choices = [("", "-----")] + [
            (p, p) for p in partitions
        ]
