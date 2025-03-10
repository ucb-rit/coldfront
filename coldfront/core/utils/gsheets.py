import os
import json
import datetime
import hashlib
from google.oauth2 import service_account
from googleapiclient.discovery import build
from django.conf import settings
from django.core.cache import cache



import os
from pdb import set_trace
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import datetime
from django.conf import settings
from django.core.cache import cache


DECOMISSION_SHEET_HEADERS = {
    "email": "PI Email",
    "name": "PI Name (first last)",
    "expected_decomission_date": "Expected Decomission Date",
    "hardware_type": "Hardware Type",
    "status": "Status",
    "initial_inquiry_date": "Initial Inquiry Date",
    "department_divison": "Department Division",
    "hardware_specification_details": "Hardware Specification Details",
}


def get_all_condo_allocations(email, sheets=["Savio", "LRC"]):
    """
    Looks in the specified sheets for records matching the user email.

    Each alert includes:
      - "id": a unique hash for the record,
      - "sheet": which sheet/tab the record came from,
      - "record": the record dictionary,
      - "expected_date": the original string,
      - other useful fields.
    """
    alerts = []
    warning_days = getattr(settings, "DECOMMISSION_WARNING_DAYS", 30)
    today = datetime.date.today()

    for sheet in sheets:
        decomissioned_csv_data, headers = get_cached_decomissions_sheet_data(sheet)
        try:
            # Ensure the required columns exist.
            headers.index(DECOMISSION_SHEET_HEADERS["email"])
        except ValueError:
            continue  # skip this sheet if necessary columns are missing

        for key, row in decomissioned_csv_data.items():
            # Normalize to a list of records.
            records = row if isinstance(row, list) else [row]
            for record in records:
                expected_date_str = record.get(DECOMISSION_SHEET_HEADERS["expected_decomission_date"], "").strip()
                if not expected_date_str:
                    continue
                try:
                    expected_date = datetime.datetime.strptime(expected_date_str, "%m/%d/%Y").date()
                except ValueError:
                    continue

                threshold_date = expected_date - datetime.timedelta(days=warning_days)
                if today >= threshold_date:
                    # Compute a unique id using sheet + email + expected_date.
                    unique_id = hashlib.md5(
                        (sheet + record.get(DECOMISSION_SHEET_HEADERS["email"], "") + expected_date_str).encode("utf8")
                    ).hexdigest()
                    alert = {
                        "id": unique_id,
                        "sheet": sheet,
                        "record": record,
                        "expected_date": expected_date_str,
                        "initial_inquiry_date": record.get(DECOMISSION_SHEET_HEADERS["initial_inquiry_date"], "").strip(),
                        "hardware_type": record.get(DECOMISSION_SHEET_HEADERS["hardware_type"], "").strip(),
                        "status": record.get(DECOMISSION_SHEET_HEADERS["status"], "").strip(),
                        "department_division": record.get(DECOMISSION_SHEET_HEADERS["department_divison"], "").strip(),
                        "hardware_specification_details": record.get(
                            DECOMISSION_SHEET_HEADERS["hardware_specification_details"], "").strip(),
                    }
                    alerts.append(alert)
    return alerts


def fetch_sheet_data(sheet_name, spreadsheet_id, header_row=2):
    """
    Returns the rows from your Google Sheet as a list of lists, where each sub-list is a row.
    The first row is expected to be the column headers.
    """
    service_account_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_PATH")
    range_name = f"{sheet_name}!A1:Z"

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)

    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

    # This gives you a list of lists, each sub-list is a row
    csv_data = result.get('values', [])

    # In this data the first two rows are title/empty.
    # We assume that the header is in row index 2.
    header = csv_data[header_row]

    return csv_data, header

def parse_decommission_data(csv_data, headers, data_start=3):
    """
    Parses the decommission data from the Google Sheet and returns a dictionary
    with the PI Email as the key and the record as the value.

    """
    try:
        headers.index(DECOMISSION_SHEET_HEADERS["email"])
    except ValueError:
        raise ValueError(f"Header does not contain a {DECOMISSION_SHEET_HEADERS['email']} field.")

    result = {}
    for row in csv_data[data_start:]:
        # In case the row is shorter than the header, pad with empty strings.
        if len(row) < len(headers):
            for i in range(len(headers) - len(row)):
                row.append("")

        # Create a dictionary mapping header names to row values.
        record = {headers[i]: row[i] for i in range(len(headers))}
        # Get the PI Email value and strip any extra whitespace.

        email = record.get(DECOMISSION_SHEET_HEADERS["email"], "").strip()
        # If there is an email, use it as the key;
        # otherwise, use the PI Name (or some other fallback).
        if email:
            key = email
        else:
            # Get a name string and replace spaces and special chars with underscores and convert to lowercase
            name = record.get(DECOMISSION_SHEET_HEADERS["name"]
                              , "").strip().replace(" ", "_").replace("/", ".").replace("-", "_").lower()
            key = f"unknown_{name}"  # fallback if even PI Name is missing

        # If you expect duplicate keys (say multiple records with the same email)
        # you might want to store a list of records per key. For example:
        if key in result:
            # If the key already exists, ensure the value is a list.
            if isinstance(result[key], list):
                result[key].append(record)
            else:
                result[key] = [result[key], record]
        else:
            result[key] = record

    return result, headers

def get_cached_decomissions_sheet_data(sheet_name, cache_time=24 * 3600):
    sheet_id = os.environ.get("DECOMISSION_SHEET_ID")
    # Optionally disable caching during testing
    if getattr(settings, "GSHEETS_DISABLE_CACHE", False):
        csv_data,headers = fetch_sheet_data(sheet_name, sheet_id)
        return parse_decommission_data(csv_data, headers)

    cache_key = f"gsheet_{sheet_name}"
    csv_data, headers  = cache.get(cache_key)
    if csv_data is None:
        sheet_id = os.environ.get("DECOMISSION_SHEET_ID")
        raw_csv_data,raw_headers = fetch_sheet_data(sheet_name, sheet_id)
        csv_data,headers = parse_decommission_data(raw_csv_data, raw_headers)
        cache.set(cache_key, csv_data, cache_time)
    return csv_data, headers
