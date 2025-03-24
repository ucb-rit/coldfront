from allauth.account.models import EmailAddress


__all__ = [
    'UserInfoDict',
]


class UserInfoDict(dict):
    """A dict of identifying information about a user, for the purpose
    of fetching hardware procurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

        assert 'emails' in self
        assert 'first_name' in self
        assert 'last_name' in self

    @classmethod
    def from_user(cls, user):
        """Instantiate from the given User."""
        user_data = {
            'emails': list(
                EmailAddress.objects.filter(user=user).values_list(
                    'email', flat=True)),
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        return cls(**user_data)
