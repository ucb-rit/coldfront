import pytest

from datetime import date
from datetime import datetime

from coldfront.plugins.hardware_procurements.utils import HardwareProcurement


@pytest.mark.unit
class TestHardwareProcurement(object):
    """Tests for the HardwareProcurement class."""

    def test_get_data_returns_copy(self):
        """Test that mutating the output of get_data does not mutate
        underlying instance data."""
        pi_emails_str = 'pi1@email.com,pi2@email.com'
        hardware_type_str = 'GPU'
        initial_inquiry_date_str = '01/01/1970'
        copy_number = 0

        data = {
            'initial_inquiry_date': datetime.strptime(
                initial_inquiry_date_str, '%m/%d/%Y'),
            'pi_emails': [
                'pi1@email.com',
                'pi2@email.com',
            ],
        }

        hp = HardwareProcurement(
            pi_emails_str, hardware_type_str, initial_inquiry_date_str,
            copy_number, data)

        output_1 = hp.get_data()
        output_1['initial_inquiry_date'] = date.today()
        output_1['pi_emails'] = ['pi3@email.com']
        output_1['new_key'] = 'new_value'

        # The output of get_data reflects the data passed in at instantiation.
        output_2 = hp.get_data()
        assert output_2['initial_inquiry_date'] == data['initial_inquiry_date']
        assert (
            output_2['initial_inquiry_date'] !=
            output_1['initial_inquiry_date'])
        assert output_2['pi_emails'] == data['pi_emails']
        assert output_2['pi_emails'] != output_1['pi_emails']
        assert 'new_key' not in output_2

    def test_get_renderable_data_output(self):
        """Test that get_renderable_data returns transformed instance
        data as expected."""
        pi_emails_str = 'pi1@email.com,pi2@email.com'
        hardware_type_str = 'GPU'
        initial_inquiry_date_str = '01/01/1970'
        copy_number = 0

        data = {
            'initial_inquiry_date': datetime.strptime(
                initial_inquiry_date_str, '%m/%d/%Y'),
            'installed_date': None,
            'pi_emails': [
                'pi1@email.com',
                'pi2@email.com',
            ],
        }

        hp = HardwareProcurement(
            pi_emails_str, hardware_type_str, initial_inquiry_date_str,
            copy_number, data)

        renderable_data = hp.get_renderable_data()
        # The instance ID should be present.
        assert 'id' in renderable_data and renderable_data['id'] == hp.get_id()
        # Lists values should be transformed to strs, with entries joined by a
        # comma and space.
        assert renderable_data['pi_emails'] == 'pi1@email.com, pi2@email.com'
        # None values should be transformed to the empty str.
        assert renderable_data['installed_date'] == ''

    @pytest.mark.parametrize(
        ['hardware_procurement_args', 'expected_id'],
        [
            # The same arguments with different copy numbers should produce
            # different IDs.
            (
                ('pi1@email.com,pi2@email.com', 'CPU', '01/01/1970', 0, {}),
                '84a3a48d'
            ),
            (
                ('pi1@email.com,pi2@email.com', 'CPU', '01/01/1970', 1, {}),
                '87c7e8f4'
            ),
            (
                ('pi1@email.com,pi2@email.com', 'CPU', '01/01/1970', 2, {}),
                '026115ca'
            ),
        ]
    )
    def test_get_id(self, hardware_procurement_args, expected_id):
        """Test that an instance instantiated with the given arguments
        has the given ID."""
        hp = HardwareProcurement(*hardware_procurement_args)
        assert hp.get_id() == expected_id

    def test_instance_dict_style_access(self):
        """Test that the dict passed via the data parameter may be
        accessed directly via the object, in dict-style access, or via
        the get_data method."""
        pi_emails_str = 'pi1@email.com,pi2@email.com'
        hardware_type_str = 'CPU'
        initial_inquiry_date_str = '01/01/1970'
        copy_number = 0

        data = {
            'initial_inquiry_date': datetime.strptime(
                initial_inquiry_date_str, '%m/%d/%Y'),
            'installed_date': None,
            'pi_emails': [
                'pi1@email.com',
                'pi2@email.com',
            ],
        }

        hp = HardwareProcurement(
            pi_emails_str, hardware_type_str, initial_inquiry_date_str,
            copy_number, data)

        for key, value in data.items():
            assert value == hp[key] == hp.get_data()[key]

    def test_instance_sorting(self):
        """Test that, when an iterable of instances is sorted, they are
        sorted by initial inquiry date, in ascending order."""
        # All instances share other fields in common.
        pi_emails_str = 'pi1@email.com,pi2@email.com'
        hardware_type_str = 'Storage'

        new_date = date(1970, 1, 3)
        mid_date = date(1970, 1, 2)
        old_date = date(1970, 1, 1)

        hardware_procurements = []
        for _date in (new_date, mid_date, old_date):
            initial_inquiry_date_str = _date.strftime('%m/%d/%Y')
            copy_number = 0
            # For the purposes of this test, no other fields need to be given.
            data = {'initial_inquiry_date': _date}
            hp = HardwareProcurement(
                pi_emails_str, hardware_type_str, initial_inquiry_date_str,
                copy_number, data)
            hardware_procurements.append(hp)

        # The list is initially sorted in the exact reverse order expected.
        old_hp = hardware_procurements[2]
        mid_hp = hardware_procurements[1]
        new_hp = hardware_procurements[0]
        assert hardware_procurements == [new_hp, mid_hp, old_hp]

        hardware_procurements.sort()

        # After sorting, the list is sorted as expected.
        assert hardware_procurements == [old_hp, mid_hp, new_hp]

    @pytest.mark.parametrize(
        [
            'pi_emails', 'poc_emails', 'user_data_to_test',
            'expected_is_associated',
        ],
        [
            # The user is one of the PIs of the procurement.
            (
                ['pi1@email.com', 'pi2@email.com'],
                ['poc1@email.com', 'poc2@email.com'],
                {
                    'id': 1,
                    'emails': ['pi1@email.com'],
                    'first_name': 'PI',
                    'last_name': 'One'
                },
                True,
            ),
            # The user is one of the POCs of the procurement.
            (
                ['pi1@email.com', 'pi2@email.com'],
                ['poc1@email.com', 'poc2@email.com'],
                {
                    'id': 2,
                    'emails': ['poc2@email.com', 'poc2@email.gov'],
                    'first_name': 'POC',
                    'last_name': 'Two'
                },
                True,
            ),
            # The user is neither a PI nor a POC of the procurement.
            (
                ['pi1@email.com', 'pi2@email.com'],
                ['poc1@email.com', 'poc2@email.com'],
                {
                    'id': 3,
                    'emails': ['user1@email.com'],
                    'first_name': 'User',
                    'last_name': 'One'
                },
                False,
            ),
        ]
    )
    def test_is_user_associated(self, pi_emails, poc_emails, user_data_to_test,
                                expected_is_associated):
        """Test that is_user_associated correctly returns whether the
        user represented by the given dict is associated with a
        procurement, based on whether any of the user's emails is in the
        list of PI or POC emails associated with the procurement."""
        pi_emails_str = ','.join(pi_emails)
        hardware_type_str = 'CPU'
        initial_inquiry_date_str = '01/01/1970'
        copy_number = 0

        data = {
            'pi_emails': pi_emails,
            'poc_emails': poc_emails,
        }

        hp = HardwareProcurement(
            pi_emails_str, hardware_type_str, initial_inquiry_date_str,
            copy_number, data)

        assert (
            hp.is_user_associated(user_data_to_test) == expected_is_associated)
