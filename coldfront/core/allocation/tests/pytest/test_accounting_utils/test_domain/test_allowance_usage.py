"""Unit tests for AllowanceUsage domain model."""

import pytest
from decimal import Decimal

from coldfront.core.allocation.utils_.accounting_utils.domain import (
    AllowanceUsage)


@pytest.mark.unit
class TestAllowanceUsage:
    """Unit tests for AllowanceUsage domain model."""

    def test_calculate_percentage_with_half_usage(self):
        """Test percentage calculation when usage is half of allowance."""
        usage = AllowanceUsage(
            allowance=Decimal('100'),
            usage=Decimal('50')
        )

        percentage = usage.calculate_percentage()

        assert percentage == Decimal('50.00')

    def test_calculate_percentage_with_zero_usage(self):
        """Test percentage calculation when usage is zero."""
        usage = AllowanceUsage(
            allowance=Decimal('100'),
            usage=Decimal('0')
        )

        percentage = usage.calculate_percentage()

        assert percentage == Decimal('0.00')

    def test_calculate_percentage_with_full_usage(self):
        """Test percentage calculation when usage equals allowance."""
        usage = AllowanceUsage(
            allowance=Decimal('100'),
            usage=Decimal('100')
        )

        percentage = usage.calculate_percentage()

        assert percentage == Decimal('100.00')

    def test_calculate_percentage_with_over_usage(self):
        """Test percentage calculation when usage exceeds allowance."""
        usage = AllowanceUsage(
            allowance=Decimal('100'),
            usage=Decimal('150')
        )

        percentage = usage.calculate_percentage()

        assert percentage == Decimal('150.00')

    def test_calculate_percentage_rounds_to_two_decimals(self):
        """Test percentage is rounded to two decimal places."""
        usage = AllowanceUsage(
            allowance=Decimal('100'),
            usage=Decimal('33.333333')
        )

        percentage = usage.calculate_percentage()

        assert percentage == Decimal('33.33')

    def test_calculate_percentage_with_large_numbers(self):
        """Test percentage calculation with large service unit values."""
        usage = AllowanceUsage(
            allowance=Decimal('1000000'),
            usage=Decimal('750000')
        )

        percentage = usage.calculate_percentage()

        assert percentage == Decimal('75.00')

    def test_calculate_percentage_with_fractional_values(self):
        """Test percentage calculation with fractional allowance and usage."""
        usage = AllowanceUsage(
            allowance=Decimal('123.45'),
            usage=Decimal('67.89')
        )

        percentage = usage.calculate_percentage()

        assert percentage == Decimal('54.99')

    def test_format_display_with_typical_values(self):
        """Test display formatting with typical service unit values."""
        usage = AllowanceUsage(
            allowance=Decimal('1000'),
            usage=Decimal('750')
        )

        display = usage.format_display()

        assert display == '750/1000 (75.00 %)'

    def test_format_display_with_zero_usage(self):
        """Test display formatting when no service units have been used."""
        usage = AllowanceUsage(
            allowance=Decimal('500'),
            usage=Decimal('0')
        )

        display = usage.format_display()

        assert display == '0/500 (0.00 %)'

    def test_format_display_with_full_usage(self):
        """Test display formatting when all service units are used."""
        usage = AllowanceUsage(
            allowance=Decimal('200'),
            usage=Decimal('200')
        )

        display = usage.format_display()

        assert display == '200/200 (100.00 %)'

    def test_format_display_with_over_usage(self):
        """Test display formatting when usage exceeds allowance."""
        usage = AllowanceUsage(
            allowance=Decimal('100'),
            usage=Decimal('125')
        )

        display = usage.format_display()

        assert display == '125/100 (125.00 %)'

    def test_format_display_preserves_decimal_places(self):
        """Test display formatting preserves decimal places in values."""
        usage = AllowanceUsage(
            allowance=Decimal('100.50'),
            usage=Decimal('25.75')
        )

        display = usage.format_display()

        assert display == '25.75/100.50 (25.62 %)'

    def test_format_display_with_small_percentage(self):
        """Test display formatting with very small percentage."""
        usage = AllowanceUsage(
            allowance=Decimal('10000'),
            usage=Decimal('1')
        )

        display = usage.format_display()

        assert display == '1/10000 (0.01 %)'

    def test_calculate_percentage_division_by_zero_raises_error(self):
        """Test that division by zero raises appropriate error."""
        usage = AllowanceUsage(
            allowance=Decimal('0'),
            usage=Decimal('50')
        )

        with pytest.raises(Exception):  # ZeroDivisionError or InvalidOperation
            usage.calculate_percentage()
