from functools import wraps
from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html



def permissions_required(*permissions):
    """
    Decorator to check if a user has all specified permissions before allowing them to access a view.
    The decorator is used to wrap a test_func from UserPassesTestMixin, which allows granular refactoring of
    the permission check logic on test_func without having to change the permission logic.

    :param permissions: variable number of functions where each returns True if the user has the permission, False otherwise
    :return:
    """
    def decorator(test_func):
        @wraps(test_func)
        def wrapper(view_instance, *args, **kwargs):
            # Check if all provided permissions return True
            if not all(permission(view_instance.request) for permission in permissions):
                return False
            return test_func(view_instance, *args, **kwargs)
        return wrapper
    return decorator


def check_first_last_name(request):
    """
    Check if the user has set their first and last name on their account before allowing them to make requests.
    :param request:
    :return:
    """
    if request.user.first_name == '' or request.user.last_name == '':
        profile_url = request.build_absolute_uri(reverse('user-profile'))
        messages.error(request, format_html(f'You must set your first and last name on your account before you can make requests. Update your profile <a href="{profile_url}">here</a>.'))
        return False
    return True