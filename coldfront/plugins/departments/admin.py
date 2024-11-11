from django.contrib import admin
from coldfront.plugins.departments.models import Department, UserDepartment

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
    ordering = ('department', 'is_authoritative', 'user__username')
    list_filter = ('user__userprofile__is_pi', 'is_authoritative')
    search_fields = ['department__name', 'department__code',
                     'user__username',
                     'user__first_name',
                     'user__last_name',
                     'user__email']
    fields = ('user', 'department', 'is_authoritative')
    readonly_fields = ('user', 'username')

    def username(self, obj):
        return obj.user.username

    def first_name(self, obj):
        return obj.user.first_name

    def last_name(self, obj):
        return obj.user.last_name
