from django.contrib import admin

from coldfront.core.billing.models import BillingActivity, BillingProject


@admin.register(BillingActivity)
class BillingActivityAdmin(admin.ModelAdmin):
    list_display = ("id", "get_project_identifier", "identifier")

    @staticmethod
    @admin.display(
        description="Project Identifier", ordering="billing_project__identifier"
    )
    def get_project_identifier(obj):
        return obj.billing_project.identifier


@admin.register(BillingProject)
class BillingProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "identifier")
