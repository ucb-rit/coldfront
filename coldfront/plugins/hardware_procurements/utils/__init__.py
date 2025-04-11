import hashlib

from copy import deepcopy

from allauth.account.models import EmailAddress


__all__ = [
    'HardwareProcurement',
    'UserInfoDict',
]


class HardwareProcurement(object):
    """An object representing a hardware procurement."""

    # Note: This object is intended to be stored in a cache, so it must
    # be serializable.

    def __init__(self, pi_emails_str, hardware_type, initial_inquiry_date,
                 copy_number, data):
        # A procurement could have multiple PIs, and thus multiple PI emails,
        # but for identification purposes, the given pi_emails_str should be a
        # str (e.g., one email, or a comma-separated list of emails).
        assert isinstance(pi_emails_str, str)
        self._pi_emails_str = pi_emails_str
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
        return deepcopy(self._data)

    def get_id(self):
        """Return a unique ID (str) for the procurement, based on
        identifying fields. Compute and store the ID if not already
        done."""
        if self._id is None:
            self._id = self._compute_id()
        return self._id

    # TODO: Consider whether this logic should be moved outside the class.
    def get_renderable_data(self):
        """Return the underlying dict of procurement data, with an
        additional `id` field set to the ID, and lists converted into
        comma-separated strs."""
        data = self.get_data()
        data['id'] = self.get_id()
        for key, value in data.items():
            if isinstance(value, list):
                data[key] = ', '.join(value)
        return data

    def is_user_associated(self, user_data):
        """Given a UserInfoDict representing a user, return whether the
        user is associated with the procurement."""
        user_emails = set(user_data['emails'])
        pi_emails = set(self['pi_emails'])
        poc_emails = set(self['poc_emails'])
        return (
            set.intersection(user_emails, pi_emails) or
            set.intersection(user_emails, poc_emails))

    def _compute_id(self):
        """Compute a unique ID (str), based on identifying fields."""
        object_bytes = str(self._get_identifying_fields()).encode('utf-8')
        return hashlib.sha256(object_bytes).hexdigest()[:8]

    def _get_identifying_fields(self):
        """Return a tuple of values that identify the procurement.

        A procurement can generally be identified by the string of PI
        emails, the hardware type, and initial inquiry date. The
        assumption is that a PI (or group of PIs) would not make more
        than one procurement request for the same hardware type on the
        same date.

        To handle the rare case in which multiple procurements have
        these fields in common, a "copy number" is used to ensure
        uniqueness. The first procurement would have copy number 0, the
        second 1, and so on. It is the responsibility of the caller to
        provide the copy number at initialization."""
        return (
            self._pi_emails_str,
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
