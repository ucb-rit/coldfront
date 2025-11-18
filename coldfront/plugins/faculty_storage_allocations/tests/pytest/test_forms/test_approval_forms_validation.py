"""Unit tests for approval form validation."""

import pytest

from coldfront.plugins.faculty_storage_allocations.forms.form_utils import (
    ReviewStatusForm,
    ReviewDenyForm,
)
from coldfront.plugins.faculty_storage_allocations.forms.approval_forms import (
    FSARequestEditForm,
)


@pytest.mark.unit
class TestReviewStatusFormValidation:
    """Unit tests for ReviewStatusForm validation logic."""

    def test_form_requires_status_field(self):
        """Test form requires status field."""
        # Empty data
        form = ReviewStatusForm(data={})

        assert not form.is_valid()
        assert 'status' in form.errors

    def test_form_accepts_pending_status(self):
        """Test form accepts 'Pending' status."""
        data = {'status': 'Pending', 'justification': ''}
        form = ReviewStatusForm(data=data)

        assert form.is_valid()
        assert form.cleaned_data['status'] == 'Pending'

    def test_form_accepts_approved_status(self):
        """Test form accepts 'Approved' status."""
        data = {'status': 'Approved', 'justification': ''}
        form = ReviewStatusForm(data=data)

        assert form.is_valid()
        assert form.cleaned_data['status'] == 'Approved'

    def test_form_accepts_denied_status(self):
        """Test form accepts 'Denied' status."""
        data = {
            'status': 'Denied',
            'justification': 'PI not eligible for this allocation'
        }
        form = ReviewStatusForm(data=data)

        assert form.is_valid()
        assert form.cleaned_data['status'] == 'Denied'

    def test_form_requires_justification_for_denial(self):
        """Test form requires justification when denying."""
        # Denied without justification
        data = {'status': 'Denied', 'justification': ''}
        form = ReviewStatusForm(data=data)

        assert not form.is_valid()
        assert 'justification' in str(form.non_field_errors()).lower()

    def test_form_requires_justification_for_denial_whitespace_only(self):
        """Test form rejects whitespace-only justification for denials."""
        # Denied with only whitespace
        data = {'status': 'Denied', 'justification': '   '}
        form = ReviewStatusForm(data=data)

        assert not form.is_valid()
        assert 'justification' in str(form.non_field_errors()).lower()

    def test_form_does_not_require_justification_for_approval(self):
        """Test justification is optional when approving."""
        data = {'status': 'Approved', 'justification': ''}
        form = ReviewStatusForm(data=data)

        assert form.is_valid()

    def test_form_does_not_require_justification_for_pending(self):
        """Test justification is optional when setting to pending."""
        data = {'status': 'Pending', 'justification': ''}
        form = ReviewStatusForm(data=data)

        assert form.is_valid()

    def test_form_accepts_optional_justification_for_approval(self):
        """Test form accepts optional justification for approval."""
        data = {
            'status': 'Approved',
            'justification': 'PI meets all criteria'
        }
        form = ReviewStatusForm(data=data)

        assert form.is_valid()
        assert form.cleaned_data['justification'] == 'PI meets all criteria'

    def test_form_validates_justification_minimum_length(self):
        """Test justification must be at least 10 characters when provided."""
        # Short justification for denial
        data = {'status': 'Denied', 'justification': 'Too short'}
        form = ReviewStatusForm(data=data)

        assert not form.is_valid()
        assert 'justification' in form.errors

    def test_form_accepts_valid_justification_length(self):
        """Test form accepts justification >= 10 characters."""
        data = {
            'status': 'Denied',
            'justification': 'This is a valid justification reason'
        }
        form = ReviewStatusForm(data=data)

        assert form.is_valid()

    def test_form_rejects_invalid_status_value(self):
        """Test form rejects invalid status values."""
        data = {'status': 'InvalidStatus', 'justification': ''}
        form = ReviewStatusForm(data=data)

        assert not form.is_valid()
        assert 'status' in form.errors

    def test_form_requires_non_empty_status(self):
        """Test form requires non-empty status selection."""
        data = {'status': '', 'justification': ''}
        form = ReviewStatusForm(data=data)

        assert not form.is_valid()
        assert 'status' in form.errors


@pytest.mark.unit
class TestReviewDenyFormValidation:
    """Unit tests for ReviewDenyForm validation logic."""

    def test_form_requires_justification(self):
        """Test form requires justification field."""
        form = ReviewDenyForm(data={})

        assert not form.is_valid()
        assert 'justification' in form.errors

    def test_form_validates_justification_minimum_length(self):
        """Test justification must be at least 10 characters."""
        # Too short
        data = {'justification': 'Too short'}
        form = ReviewDenyForm(data=data)

        assert not form.is_valid()
        assert 'justification' in form.errors

    def test_form_accepts_valid_justification(self):
        """Test form accepts justification >= 10 characters."""
        data = {'justification': 'This is a valid denial reason'}
        form = ReviewDenyForm(data=data)

        assert form.is_valid()
        assert form.cleaned_data['justification'] == \
            'This is a valid denial reason'

    def test_form_rejects_empty_justification(self):
        """Test form rejects empty justification."""
        data = {'justification': ''}
        form = ReviewDenyForm(data=data)

        assert not form.is_valid()
        assert 'justification' in form.errors

    def test_form_accepts_long_justification(self):
        """Test form accepts long justifications."""
        long_text = 'A' * 500  # 500 character justification
        data = {'justification': long_text}
        form = ReviewDenyForm(data=data)

        assert form.is_valid()


@pytest.mark.unit
class TestFSARequestEditFormValidation:
    """Unit tests for FSARequestEditForm validation logic."""

    def test_form_requires_storage_amount(self):
        """Test form requires storage_amount field."""
        form = FSARequestEditForm(data={})

        assert not form.is_valid()
        assert 'storage_amount' in form.errors

    def test_form_accepts_valid_storage_amounts(self):
        """Test form accepts valid storage amount choices (1-5 TB)."""
        for amount in [1, 2, 3, 4, 5]:
            data = {'storage_amount': amount}
            form = FSARequestEditForm(data=data)

            assert form.is_valid(), \
                f"Form should accept {amount} TB"
            assert int(form.cleaned_data['storage_amount']) == amount

    def test_form_rejects_zero_storage_amount(self):
        """Test form rejects 0 TB storage amount."""
        data = {'storage_amount': 0}
        form = FSARequestEditForm(data=data)

        assert not form.is_valid()
        assert 'storage_amount' in form.errors

    def test_form_rejects_negative_storage_amount(self):
        """Test form rejects negative storage amount."""
        data = {'storage_amount': -1}
        form = FSARequestEditForm(data=data)

        assert not form.is_valid()
        assert 'storage_amount' in form.errors

    def test_form_rejects_invalid_storage_amount(self):
        """Test form rejects storage amounts not in choices (e.g., 10 TB)."""
        data = {'storage_amount': 10}
        form = FSARequestEditForm(data=data)

        assert not form.is_valid()
        assert 'storage_amount' in form.errors

    def test_form_has_correct_field_labels(self):
        """Test form has expected field labels."""
        form = FSARequestEditForm()

        assert 'Updated Storage Amount' in \
            form.fields['storage_amount'].label

    def test_form_has_help_text(self):
        """Test form includes helpful guidance text."""
        form = FSARequestEditForm()

        assert form.fields['storage_amount'].help_text
        assert 'storage' in form.fields['storage_amount'].help_text.lower()
