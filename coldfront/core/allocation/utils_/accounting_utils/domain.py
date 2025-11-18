"""Domain models for allocation accounting.

Domain models contain pure business logic and have no dependencies on
Django or infrastructure concerns.
"""

from decimal import Decimal


class AllowanceUsage:
    """Domain model representing computing allowance usage."""

    def __init__(self, allowance: Decimal, usage: Decimal):
        self.allowance = allowance
        self.usage = usage

    def calculate_percentage(self) -> Decimal:
        """Calculate usage percentage."""
        return (Decimal(100.00) * self.usage / self.allowance).quantize(
            Decimal('0.00'))

    def format_display(self) -> str:
        """Format the usage for display."""
        percentage = self.calculate_percentage()
        return f'{self.usage}/{self.allowance} ({percentage} %)'
