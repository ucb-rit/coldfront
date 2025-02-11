## Google Sheets Integration

This project uses Google Sheets to track acitivites such as:
- HPC hardware procurement and decommission information.
- TBD



### Setup

1. **Service Account & Credentials:**
   - Create a Google Cloud service account with Sheets API (readonly) access.
   - Set the environment variable `GOOGLE_SERVICE_ACCOUNT_JSON_PATH` to the path of your JSON credentials.
   - Set `DECOMISSION_SHEET_ID` to your target spreadsheet's ID.

2. **Django Settings:**
   - **`DECOMMISSION_WARNING_DAYS`**: Days before the decommission date to trigger a warning (default: `30`).
   - **`GSHEETS_CACHE_TIMEOUT`**: Cache duration in seconds (default: `86400` for 24 hours).
   - **`GSHEETS_DISABLE_CACHE`**: Set to `True` during development/testing to disable caching.

3. ** Docker-compose environment:**
   - Add the following to your `docker-compose.yml` file:
     ```yaml
     services:
       web:
         environment:
           - GOOGLE_SERVICE_ACCOUNT_JSON_PATH=/path/to/your/credentials.json
           - DECOMISSION_SHEET_ID=your-spreadsheet-id
           - GSHEETS_DISABLE_CACHE=True
     # ...
     ```

### Google Sheets Format

- **Tabs:** The spreadsheet must include two tabs: **Savio** and **LRC**.
- **Header:** The header is on row 3 and must include at least:
  - `PI Email`
  - `Expected Decomission Date` (in MM/DD/YYYY format)
- **Data Rows:** Data starts from row 4.

### HPCS Hardware Procurement Tracking

Upon user login, the application:
- Checks both the **Savio** and **LRC** tabs for a record where `PI Email` matches the logged-in user's email.
- Parses the `Expected Decomission Date` and, if the current date is within `DECOMMISSION_WARNING_DAYS` of that date, flags the record.
- Displays decommission alerts using a card layout that lists each field vertically for clear, readable details.

---

This summary should help users and developers quickly understand and set up the Google Sheets integration and the HPCS Hardware Procurement Tracking functionality.