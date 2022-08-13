from coldfront.core.user.utils import get_compute_resources_for_user


def assert_identity_linking_request_serialization(identity_linking_request,
                                                  result, fields):
    """Assert that IdentityLinkingRequest serialization gives the
    expected result."""
    for field in fields:
        field_value = getattr(identity_linking_request, field)
        if field == 'requester':
            expected = str(field_value.id)
        elif field in ('request_time', 'completion_time'):
            if field_value is None:
                expected = str(field_value)
            else:
                expected = field_value.isoformat().replace('+00:00', 'Z')
        elif field == 'status':
            expected = field_value.name
        else:
            expected = str(field_value)
        actual = str(result[field])
        assert expected == actual


def assert_user_serialization(user, result, fields):
    """Assert that User serialization gives the expected result."""
    for field in fields:
        field_value = getattr(user, field)
        expected = str(field_value)
        actual = str(result[field])
        assert expected == actual


def assert_account_deactivation_request_serialization(
        request, result, fields):
    """Assert that IdentityLinkingRequest serialization gives the
    expected result."""
    for field in fields:
        if field == 'justification':
            continue

        if field == 'user':
            field_value = getattr(request, field)
            expected = field_value.username
        elif field in ['status', 'reason']:
            field_value = getattr(request, field)
            expected = field_value.name
        elif field == 'compute_resources':
            resources = get_compute_resources_for_user(request.user)
            expected = ','.join([resource.name for resource in resources])
        elif field == 'recharge_project':
            expected = str(request.state['recharge_project_pk'])
        else:
            field_value = getattr(request, field)
            expected = str(field_value)

        actual = str(result[field])
        assert expected == actual
