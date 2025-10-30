import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import streamlit as st

# === CONFIGURATION ===
SPREADSHEET_ID = "1CW62XUrBmI7O6LZ-2EUyw6oVKfx871oE2ZD_KF02fxg"   # ✅ your sheet ID
INPUT_SHEET_NAME = "Input"
OUTPUT_SHEET_NAME = "Output"

TRACKERS = ["scorecard", "adform.ne", "adventity", "flashtalking", "doubleverify", "moat", "gampad", "chartbeat", "collect?v=2", "trackimp"]

samsung_s24 = {
    "name": "Samsung Galaxy S24",
    "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.133 Mobile Safari/537.36",
    "viewport": {"width": 1080, "height": 2340},
    "device_scale_factor": 3,
    "is_mobile": True,
    "has_touch": True,
}

# === FUNCTIONS ===

def authorize_gsheets():
    # ✅ Load credentials from Streamlit secrets
    creds_dict = st.secrets["google_service_account"]
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def read_urls_from_sheet(client):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(INPUT_SHEET_NAME)
    urls = sheet.col_values(1)[1:]  # skip header
    return urls

def write_results_to_sheet(client, results):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(OUTPUT_SHEET_NAME)
    header = ['url', 'error', 'checked_at'] + TRACKERS
    rows = [header]
    for res in results:
        row = [res.get(col, '') for col in header]
        rows.append(row)
    sheet.clear()
    sheet.update('A1', rows, value_input_option="RAW")

def check_url(url):
    tracker_status = {tracker: False for tracker in TRACKERS}
    error_msg = ""
    checked_at = datetime.now().isoformat(sep=' ', timespec='seconds')

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=samsung_s24["user_agent"],
                viewport=samsung_s24["viewport"],
                device_scale_factor=samsung_s24["device_scale_factor"],
                is_mobile=samsung_s24["is_mobile"],
                has_touch=samsung_s24["has_touch"],
            )
            page = context.new_page()

            def handle_request(request):
                req_url = request.url.lower()
                for tracker in TRACKERS:
                    if tracker in req_url:
                        tracker_status[tracker] = True

            page.on("request", handle_request)
            page.goto(url, timeout=180000, wait_until="networkidle")
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(50000)

            context.close()
            browser.close()

    except Exception as e:
        error_msg = str(e)

    result = {"url": url, "error": error_msg, "checked_at": checked_at}
    result.update(tracker_status)
    print(f"Checked: {url} -> {tracker_status} at {checked_at}")
    return result

def main():
    st.title("🔍 Google Sheets Tracker Tool")
    st.write("This tool checks trackers from your Google Sheet using Playwright.")

    if st.button("🚀 Run Tracker"):
        st.info("Running tracker... please wait.")
        client = authorize_gsheets()
        urls = read_urls_from_sheet(client)
        st.write(f"Found {len(urls)} URLs to check.")

        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(check_url, urls))

        write_results_to_sheet(client, results)
        st.success(f"✅ Results written to Google Sheet '{OUTPUT_SHEET_NAME}' tab!")

if __name__ == "__main__":
    main()
