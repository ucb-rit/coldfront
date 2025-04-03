import hashlib

from allauth.account.models import EmailAddress


__all__ = [
    'HardwareProcurement',
    'UserInfoDict',
]


class HardwareProcurement(object):
    """An object representing a hardware procurement."""

    # Note: This object is intended to be stored in a cache, so it must
    # be serializable.

    def __init__(self, pi_email, hardware_type, initial_inquiry_date,
                 copy_number, data):
        self._pi_email = pi_email
        self._hardware_type = hardware_type
        self._initial_inquiry_date = initial_inquiry_date
        self._copy_number = copy_number
        self._data = data
        self._id = self._compute_id()

    def __getitem__(self, key):
        """Enable data fields to be accessed directly via the
        instance. E.g.,:

            hardware_procurement['hardware_type']

        """
        return self._data[key]

    def get_data(self):
        """Return the underlying dict of procurement data."""
        return self._data

    def get_id(self):
        """Return a unique ID (str) for the procurement, based on
        identifying fields. Compute and store the ID if not already
        done."""
        if self._id is None:
            self._id = self._compute_id()
        return self._id

    def is_user_associated(self, user_data):
        """Given a UserInfoDict representing a user, return whether the
        user is associated with the procurement."""
        user_emails = set(user_data['emails'])
        pi_email = self['pi_email']
        poc_email = self['poc_email']
        return pi_email in user_emails or poc_email in user_emails

    def _compute_id(self):
        """Compute a unique ID (str), based on identifying fields."""
        object_bytes = str(self._get_identifying_fields()).encode('utf-8')
        return hashlib.sha256(object_bytes).hexdigest()[:8]

    def _get_identifying_fields(self):
        """Return a tuple of values that identify the procurement.

        A procurement can generally be identified by the PI's email, the
        hardware type, and initial inquiry date. The assumption is that
        a single PI would not make more than one procurement request for
        the same hardware type on the same date.

        To handle the rare case in which multiple procurements have
        these fields in common, a "copy number" is used to ensure
        uniqueness. The first procurement would have copy number 0, the
        second 1, and so on. It is the responsibility of the caller to
        provide the copy number at initialization."""
        return (
            self._pi_email,
            self._hardware_type,
            self._initial_inquiry_date,
            self._copy_number)


class UserInfoDict(dict):
    """A dict of identifying information about a user, for the purpose
    of fetching hardware procurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

        assert 'id' in self
        assert 'emails' in self
        assert 'first_name' in self
        assert 'last_name' in self

    @classmethod
    def from_user(cls, user):
        """Instantiate from the given User."""
        user_data = {
            'id': user.id,
            'emails': list(
                EmailAddress.objects.filter(user=user).values_list(
                    'email', flat=True)),
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        return cls(**user_data)
