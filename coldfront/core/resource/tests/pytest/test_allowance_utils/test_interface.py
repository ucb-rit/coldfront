"""Tests for ComputingAllowanceInterface and get_computing_allowance_interface."""

import pytest

from coldfront.core.resource.utils_.allowance_utils.interface import (
    ComputingAllowanceInterface,
    ComputingAllowanceInterfaceError,
    get_computing_allowance_interface,
)

# ---------------------------------------------------------------------------
# ComputingAllowanceInterface
# ---------------------------------------------------------------------------


@pytest.mark.component
@pytest.mark.django_db
class TestComputingAllowanceInterface:
    def test_allowances_returns_non_empty_list(self):
        interface = ComputingAllowanceInterface()
        allowances = interface.allowances()
        assert isinstance(allowances, list)
        assert len(allowances) > 0

    def test_allowance_from_code_round_trip(self):
        """code_from_name → allowance_from_code round-trips back to the same object."""
        interface = ComputingAllowanceInterface()
        tested_any = False
        for allowance in interface.allowances():
            try:
                code = interface.code_from_name(allowance.name)
                assert interface.allowance_from_code(code) is allowance
                tested_any = True
            except ComputingAllowanceInterfaceError:
                pass
        if not tested_any:
            pytest.skip("No allowances with codes found in test database")

    def test_name_short_round_trip(self):
        """name_short_from_name → allowance_from_name_short round-trips back."""
        interface = ComputingAllowanceInterface()
        tested_any = False
        for allowance in interface.allowances():
            try:
                name_short = interface.name_short_from_name(allowance.name)
                assert interface.allowance_from_name_short(name_short) is allowance
                tested_any = True
            except ComputingAllowanceInterfaceError:
                pass
        if not tested_any:
            pytest.skip("No allowances with name_short found in test database")

    def test_allowance_from_project_uses_name_prefix(self):
        """allowance_from_project reads the first 3 chars of project.name as a code."""
        interface = ComputingAllowanceInterface()
        for allowance in interface.allowances():
            try:
                code = interface.code_from_name(allowance.name)
            except ComputingAllowanceInterfaceError:
                continue

            class _FakeProject:
                name = f"{code}_testproject"

            assert interface.allowance_from_project(_FakeProject()) is allowance
            return  # one successful case is enough

        pytest.skip("No allowances with codes found in test database")

    def test_allowance_from_code_raises_on_unknown_code(self):
        interface = ComputingAllowanceInterface()
        with pytest.raises(ComputingAllowanceInterfaceError):
            interface.allowance_from_code("__nonexistent_code__")

    def test_allowance_from_name_short_raises_on_unknown(self):
        interface = ComputingAllowanceInterface()
        with pytest.raises(ComputingAllowanceInterfaceError):
            interface.allowance_from_name_short("__nonexistent__")

    def test_code_from_name_raises_on_unknown_name(self):
        interface = ComputingAllowanceInterface()
        with pytest.raises(ComputingAllowanceInterfaceError):
            interface.code_from_name("__nonexistent_allowance_name__")


# ---------------------------------------------------------------------------
# get_computing_allowance_interface
# ---------------------------------------------------------------------------


@pytest.mark.component
@pytest.mark.django_db
class TestGetComputingAllowanceInterface:
    def test_returns_computing_allowance_interface_instance(self):
        result = get_computing_allowance_interface()
        assert isinstance(result, ComputingAllowanceInterface)

    def test_cache_returns_same_instance(self):
        instance1 = get_computing_allowance_interface()
        instance2 = get_computing_allowance_interface()
        assert instance1 is instance2

    def test_cache_clear_creates_new_instance(self):
        instance1 = get_computing_allowance_interface()
        get_computing_allowance_interface.cache_clear()
        instance2 = get_computing_allowance_interface()
        assert instance1 is not instance2
        # instance2 is now cached — leave it in place for subsequent test code.

    def test_cached_instance_has_same_allowances_as_fresh(self):
        """The cached instance returns the same allowance names as a fresh one."""
        cached = get_computing_allowance_interface()
        fresh = ComputingAllowanceInterface()
        assert sorted(a.name for a in cached.allowances()) == sorted(
            a.name for a in fresh.allowances()
        )
