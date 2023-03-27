from django.contrib import admin
from coldfront.core.department.models import Department, UserDepartment

# Register your models here.

class DepartmentHasUsersFilter(admin.SimpleListFilter):
    title = 'Has Users'
    parameter_name = 'has_users'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value() == 'yes':
            return queryset.exclude(userdepartment__isnull=True)
        if self.value() == 'no':
            return queryset.filter(userdepartment__isnull=True)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    ordering = ('name', 'code')
    search_fields = ['name', 'code']
    list_filter = (DepartmentHasUsersFilter,)

@admin.register(UserDepartment)
class UserDepartmentAdmin(admin.ModelAdmin):
    list_display = ('department', 'username', 'first_name', 'last_name', 'is_authoritative')
    ordering = ('department', 'is_authoritative', 'userprofile__user__username')
    list_filter = ('userprofile__is_pi', 'is_authoritative')
    search_fields = ['department__name', 'department__code',
                     'userprofile__user__username',
                     'userprofile__user__first_name',
                     'userprofile__user__last_name',
                     'userprofile__user__email']
    fields = ('userprofile', 'department', 'is_authoritative')
    readonly_fields = ('userprofile', 'username' )

    def username(self, obj):
        return obj.userprofile.user.username

    def first_name(self, obj):
        return obj.userprofile.user.first_name

    def last_name(self, obj):
        return obj.userprofile.user.last_name