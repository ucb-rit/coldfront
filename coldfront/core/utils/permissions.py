from functools import wraps
from django.contrib import messages

def permission_required(permission_check):
    """
    Decorator to check if a user has a certain permission before allowing them to access a view.
    The decorater is used to wrap a test_func from UserPassesTestMixin, which allows gradular refactoring of
    the permission check logic on test_func without having to change the permission logic.

    :param permission_check: function that returns True if the user has the permission, False otherwise
    :return:
    """
    def decorator(test_func):
        @wraps(test_func)
        def wrapper(view_instance, *args, **kwargs):
            if not permission_check(view_instance.request):
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
        messages.error(request, 'You must set your first and last name on your account before you can make requests.')
        return False
    return True