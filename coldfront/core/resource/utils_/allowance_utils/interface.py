from base64 import b64decode
from base64 import b64encode

from django.core.cache import cache

from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceType

import pickle


class ComputingAllowanceInterface(object):
    """A singleton that fetches computing allowances from the database
    and provides methods for retrieving associated data."""

    def __init__(self):
        """Retrieve database objects and instantiate data structures."""
        resource_type = ResourceType.objects.get(name='Computing Allowance')
        allowances = Resource.objects.prefetch_related(
            'resourceattribute_set').filter(resource_type=resource_type)

        # A mapping from code values to allowance Resource objects.
        self._code_to_object = {}
        # A mapping from allowance names to allowance Resource objects.
        self._name_to_object = {}
        # A mapping from name_short values to allowance Resource objects.
        self._name_short_to_object = {}
        # A mapping from allowance Resource objects to code values.
        self._object_to_code = {}
        # A mapping from allowance Resource objects to name_long values.
        self._object_to_name_long = {}
        # A mapping from allowance Resource objects to name_short values.
        self._object_to_name_short = {}
        # A mapping from allowance Resource objects to Service Units values.
        self._object_to_service_units = {}
        self._set_up_data_structures(allowances)

    def _set_up_data_structures(self, allowances):
        """Fill in data structures."""
        for allowance in allowances:
            self._name_to_object[allowance.name] = allowance
            self._object_to_service_units[allowance] = {
                'constant': None,
                'timed': {},
            }
            for attribute in allowance.resourceattribute_set.all():
                attribute_type_name = attribute.resource_attribute_type.name
                if attribute_type_name == 'code':
                    self._code_to_object[attribute.value] = allowance
                    self._object_to_code[allowance] = attribute.value
                elif attribute_type_name == 'name_long':
                    self._object_to_name_long[allowance] = attribute.value
                elif attribute_type_name == 'name_short':
                    self._name_short_to_object[attribute.value] = allowance
                    self._object_to_name_short[allowance] = attribute.value
                elif attribute_type_name == 'Service Units':
                    self._object_to_service_units[allowance]['constant'] = \
                        attribute.value
            for timed_attribute in allowance.timedresourceattribute_set.all():
                attribute_type_name = \
                    timed_attribute.resource_attribute_type.name
                key = (timed_attribute.start_date, timed_attribute.end_date)
                if attribute_type_name == 'Service Units':
                    self._object_to_service_units[allowance]['timed'][key] = \
                        timed_attribute.value

    def allowance_from_code(self, code):
        """Given a code, return the corresponding allowance (Resource
        object)."""
        try:
            return self._code_to_object[code]
        except KeyError as e:
            raise ComputingAllowanceInterfaceError(e)

    def allowance_from_name_short(self, name_short):
        """Given a name_short, return the corresponding allowance
        (Resource object)."""
        try:
            return self._name_short_to_object[name_short]
        except KeyError as e:
            raise ComputingAllowanceInterfaceError(e)

    def allowance_from_project(self, project):
        """Given a Project, return the corresponding allowance (Resource
        object)."""
        try:
            code = project.name[:3]
            return self.allowance_from_code(code)
        except Exception as e:
            raise ComputingAllowanceInterfaceError(e)

    def allowances(self):
        """Return a list of allowances (Resource objects)."""
        return list(self._name_to_object.values())

    def code_from_name(self, name):
        """Given a name, return the corresponding allowance's code."""
        try:
            return self._object_to_code[self._name_to_object[name]]
        except KeyError as e:
            raise ComputingAllowanceInterfaceError(e)

    def name_long_from_name(self, name):
        """Given a name, return the corresponding allowance's
        name_long."""
        try:
            return self._object_to_name_long[self._name_to_object[name]]
        except KeyError as e:
            raise ComputingAllowanceInterfaceError(e)

    def name_short_from_name(self, name):
        """Given a name, return the corresponding allowance's
        name_short."""
        try:
            return self._object_to_name_short[self._name_to_object[name]]
        except KeyError as e:
            raise ComputingAllowanceInterfaceError(e)

    def service_units_from_name(self, name, is_timed=False,
                                allocation_period=None):
        """Given a name, return the corresponding allowance's service
        units value. If is_timed is True (i.e., the value varies over
        time), return the value associated with the given
        AllocationPeriod. Otherwise, return the constant value.

        The AllocationPeriod is only considered if is_timed is True.
        """
        try:
            service_units_data = self._object_to_service_units[
                self._name_to_object[name]]
            if is_timed:
                assert isinstance(allocation_period, AllocationPeriod)
                key = (allocation_period.start_date, allocation_period.end_date)
                return service_units_data['timed'][key]
            else:
                return service_units_data['constant']
        except KeyError as e:
            raise ComputingAllowanceInterfaceError(e)


class ComputingAllowanceInterfaceError(Exception):
    """An exception to be raised by the ComputingAllowanceInterface."""
    pass


def cached_computing_allowance_interface():
    """Return an instance of ComputingAllowanceInterface. If one is
    already in the cache, return it. Otherwise, create one, store it in
    the cache, and return it."""
    cache_key = 'computing_allowance_interface'
    if cache_key in cache:
        cache_value = cache.get(cache_key)
        computing_allowance_interface = pickle.loads(
            b64decode(cache_value.encode('utf-8')))
    else:
        computing_allowance_interface = ComputingAllowanceInterface()
        cache_value = b64encode(
            pickle.dumps(computing_allowance_interface)).decode('utf-8')
        cache.set(cache_key, cache_value)
    return computing_allowance_interface
