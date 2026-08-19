"""Tests for GoogleFormsRenewalSurveyBackend."""

import json
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
class TestLoadSurveyMetadataFromFile:
    """Unit tests for _load_survey_metadata_from_file."""

    @staticmethod
    def _make_survey_entry(allocation_period, sheet_id="sheet_id"):
        return {"allocation_period": allocation_period, "sheet_id": sheet_id}

    def test_returns_matching_metadata(self, tmp_path):
        entries = [
            self._make_survey_entry("AY 2023-24", "sheet_a"),
            self._make_survey_entry("AY 2024-25", "sheet_b"),
        ]
        survey_file = tmp_path / "renewal-survey-data.json"
        survey_file.write_text(json.dumps(entries))
        renewal_survey = {"details": {"survey_data_file_path": str(survey_file)}}
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = renewal_survey
            result = GoogleFormsRenewalSurveyBackend._load_survey_metadata_from_file(
                "AY 2024-25"
            )
        assert result == self._make_survey_entry("AY 2024-25", "sheet_b")

    def test_raises_when_period_not_found(self, tmp_path):
        entries = [self._make_survey_entry("AY 2023-24")]
        survey_file = tmp_path / "renewal-survey-data.json"
        survey_file.write_text(json.dumps(entries))
        renewal_survey = {"details": {"survey_data_file_path": str(survey_file)}}
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = renewal_survey
            with pytest.raises(ValueError, match="AY 2099-00"):
                GoogleFormsRenewalSurveyBackend._load_survey_metadata_from_file(
                    "AY 2099-00"
                )

    def test_raises_when_survey_data_empty(self, tmp_path):
        survey_file = tmp_path / "renewal-survey-data.json"
        survey_file.write_text(json.dumps([]))
        renewal_survey = {"details": {"survey_data_file_path": str(survey_file)}}
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = renewal_survey
            with pytest.raises(ValueError):
                GoogleFormsRenewalSurveyBackend._load_survey_metadata_from_file(
                    "AY 2024-25"
                )

    def test_raises_when_survey_data_file_path_absent(self):
        renewal_survey = {"details": {}}
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = renewal_survey
            with pytest.raises(ValueError, match="survey_data_file_path"):
                GoogleFormsRenewalSurveyBackend._load_survey_metadata_from_file(
                    "AY 2024-25"
                )

    def test_returns_first_match_when_duplicates(self, tmp_path):
        """When multiple entries share the same allocation_period, the first is returned."""
        entries = [
            self._make_survey_entry("AY 2024-25", "sheet_first"),
            self._make_survey_entry("AY 2024-25", "sheet_second"),
        ]
        survey_file = tmp_path / "renewal-survey-data.json"
        survey_file.write_text(json.dumps(entries))
        renewal_survey = {"details": {"survey_data_file_path": str(survey_file)}}
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = renewal_survey
            result = GoogleFormsRenewalSurveyBackend._load_survey_metadata_from_file(
                "AY 2024-25"
            )
        assert result["sheet_id"] == "sheet_first"


@pytest.mark.unit
class TestGetGspreadWks:
    """Unit tests for _get_gspread_wks."""

    _CREDENTIALS_FILE_PATH = "/etc/coldfront/config/renewal-survey.json"

    def _make_renewal_survey(self, credentials_file_path=None):
        path = (
            credentials_file_path
            if credentials_file_path is not None
            else self._CREDENTIALS_FILE_PATH
        )
        return {"details": {"credentials_file_path": path}}

    def test_raises_when_credentials_file_path_absent(self):
        """No 'credentials_file_path' key at all → ValueError."""
        renewal_survey = {"details": {}}
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = renewal_survey
            with pytest.raises(ValueError, match="No credentials_file_path found"):
                GoogleFormsRenewalSurveyBackend._get_gspread_wks("sheet_id_abc")

    def test_raises_when_credentials_file_path_empty(self):
        """Empty credentials_file_path is falsy → ValueError."""
        renewal_survey = self._make_renewal_survey(credentials_file_path="")
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = renewal_survey
            with pytest.raises(ValueError, match="No credentials_file_path found"):
                GoogleFormsRenewalSurveyBackend._get_gspread_wks("sheet_id_abc")

    def test_returns_worksheet_and_calls_gspread(self):
        mock_wks = MagicMock()
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = self._make_renewal_survey()
            with patch(f"{_BACKEND}.gspread.service_account") as mock_sa:
                mock_gc = mock_sa.return_value
                mock_sh = mock_gc.open_by_key.return_value
                mock_sh.get_worksheet.return_value = mock_wks

                result = GoogleFormsRenewalSurveyBackend._get_gspread_wks(
                    "sheet_id_abc"
                )

        assert result is mock_wks
        mock_sa.assert_called_once_with(filename=self._CREDENTIALS_FILE_PATH)
        mock_gc.open_by_key.assert_called_once_with("sheet_id_abc")
        mock_sh.get_worksheet.assert_called_once_with(0)

    def test_passes_custom_wks_id(self):
        with patch(f"{_BACKEND}.settings") as mock_settings:
            mock_settings.RENEWAL_SURVEY = self._make_renewal_survey()
            with patch(f"{_BACKEND}.gspread.service_account") as mock_sa:
                mock_sh = mock_sa.return_value.open_by_key.return_value
                GoogleFormsRenewalSurveyBackend._get_gspread_wks(
                    "sheet_id_abc", wks_id=2
                )
                mock_sh.get_worksheet.assert_called_once_with(2)
