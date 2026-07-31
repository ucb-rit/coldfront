"""Tests for GoogleFormsRenewalSurveyBackend."""

from unittest.mock import MagicMock, patch

import pytest

from coldfront.core.project.utils_.renewal_survey.backends.google_forms import (
    GoogleFormsRenewalSurveyBackend,
)

_BACKEND = "coldfront.core.project.utils_.renewal_survey.backends.google_forms"


@pytest.mark.unit
class TestGsheetColumnToIndex:
    """Unit tests for _gsheet_column_to_index.

    The method uses 1-based indexing (gspread col_values convention):
    'A' → 1, 'Z' → 26, 'AA' → 27.
    """

    @pytest.mark.parametrize(
        ["column_str", "expected_index"],
        [
            ("A", 1),
            ("B", 2),
            ("Z", 26),
            ("AA", 27),
            ("AB", 28),
            ("AZ", 52),
            ("BA", 53),
            # Case-insensitive.
            ("a", 1),
            ("aa", 27),
        ],
    )
    def test_column_to_index(self, column_str, expected_index):
        index = GoogleFormsRenewalSurveyBackend._gsheet_column_to_index(column_str)
        assert index == expected_index


@pytest.mark.unit
class TestLoadSurveyMetadataFromSettings:
    """Unit tests for _load_survey_metadata_from_settings."""

    @staticmethod
    def _make_renewal_survey(survey_data):
        return {"details": {"survey_data": survey_data}}

    @staticmethod
    def _make_survey_entry(allocation_period, sheet_id="sheet_id"):
        return {"allocation_period": allocation_period, "sheet_id": sheet_id}

    def test_returns_matching_metadata(self):
        entries = [
            self._make_survey_entry("AY 2023-24", "sheet_a"),
            self._make_survey_entry("AY 2024-25", "sheet_b"),
        ]
        renewal_survey = self._make_renewal_survey(entries)
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = renewal_survey
            result = (
                GoogleFormsRenewalSurveyBackend._load_survey_metadata_from_settings(
                    "AY 2024-25"
                )
            )
        assert result == self._make_survey_entry("AY 2024-25", "sheet_b")

    def test_raises_when_period_not_found(self):
        entries = [self._make_survey_entry("AY 2023-24")]
        renewal_survey = self._make_renewal_survey(entries)
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = renewal_survey
            with pytest.raises(ValueError, match="AY 2099-00"):
                GoogleFormsRenewalSurveyBackend._load_survey_metadata_from_settings(
                    "AY 2099-00"
                )

    def test_raises_when_survey_data_empty(self):
        renewal_survey = self._make_renewal_survey([])
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = renewal_survey
            with pytest.raises(ValueError):
                GoogleFormsRenewalSurveyBackend._load_survey_metadata_from_settings(
                    "AY 2024-25"
                )

    def test_returns_first_match_when_duplicates(self):
        """When multiple entries share the same allocation_period, the first is returned."""
        entries = [
            self._make_survey_entry("AY 2024-25", "sheet_first"),
            self._make_survey_entry("AY 2024-25", "sheet_second"),
        ]
        renewal_survey = self._make_renewal_survey(entries)
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = renewal_survey
            result = (
                GoogleFormsRenewalSurveyBackend._load_survey_metadata_from_settings(
                    "AY 2024-25"
                )
            )
        assert result["sheet_id"] == "sheet_first"


@pytest.mark.unit
class TestGetGspreadWks:
    """Unit tests for _get_gspread_wks."""

    _CREDENTIALS = {"type": "service_account", "project_id": "my-project"}

    def _make_renewal_survey(self, credentials=None):
        creds = credentials if credentials is not None else self._CREDENTIALS
        return {"details": {"credentials": creds}}

    def test_raises_when_credentials_key_absent(self):
        """No 'credentials' key at all → ValueError."""
        renewal_survey = {"details": {}}
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = renewal_survey
            with pytest.raises(ValueError, match="No credentials found"):
                GoogleFormsRenewalSurveyBackend._get_gspread_wks("sheet_id_abc")

    def test_raises_when_credentials_empty_dict(self):
        """Empty credentials dict is falsy → ValueError."""
        renewal_survey = self._make_renewal_survey(credentials={})
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = renewal_survey
            with pytest.raises(ValueError, match="No credentials found"):
                GoogleFormsRenewalSurveyBackend._get_gspread_wks("sheet_id_abc")

    def test_returns_worksheet_and_calls_gspread(self):
        mock_wks = MagicMock()
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = self._make_renewal_survey()
            with patch(f"{_BACKEND}.gspread.service_account_from_dict") as mock_saf:
                mock_gc = mock_saf.return_value
                mock_sh = mock_gc.open_by_key.return_value
                mock_sh.get_worksheet.return_value = mock_wks

                result = GoogleFormsRenewalSurveyBackend._get_gspread_wks(
                    "sheet_id_abc"
                )

        assert result is mock_wks
        mock_saf.assert_called_once_with(self._CREDENTIALS)
        mock_gc.open_by_key.assert_called_once_with("sheet_id_abc")
        mock_sh.get_worksheet.assert_called_once_with(0)

    def test_passes_custom_wks_id(self):
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = self._make_renewal_survey()
            with patch(f"{_BACKEND}.gspread.service_account_from_dict") as mock_saf:
                mock_sh = mock_saf.return_value.open_by_key.return_value
                GoogleFormsRenewalSurveyBackend._get_gspread_wks(
                    "sheet_id_abc", wks_id=2
                )
                mock_sh.get_worksheet.assert_called_once_with(2)
