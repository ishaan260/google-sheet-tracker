import os
import json
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import streamlit as st

# ✅ Ensure Playwright Chromium is installed (auto on Streamlit Cloud)
os.system("playwright install chromium > /dev/null 2>&1")

# === CONFIGURATION ===
SPREADSHEET_ID = "1CW62XUrBmI7O6LZ-2EUyw6oVKfx871oE2ZD_KF02fxg"  # ✅ Replace with your Sheet ID
INPUT_SHEET_NAME = "Input"
OUTPUT_SHEET_NAME = "Output"

TRACKERS = [
    "scorecard", "adform.ne", "adventity", "flashtalking",
    "doubleverify", "moat", "gampad", "chartbeat", "collect?v=2", "trackimp"
]

# Emulate Samsung Galaxy S24 mobile browser
samsung_s24 = {
    "name": "Samsung Galaxy S24",
    "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-S911B) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/114.0.5735.133 Mobile Safari/537.36",
    "viewport": {"width": 1080, "height": 2340},
    "device_scale_factor": 3,
    "is_mobile": True,
    "has_touch": True,
}


# === GOOGLE SHEETS AUTH ===
def authorize_gsheets():
    """Authorize Google Sheets using Streamlit secrets"""
    try:
        creds_dict = st.secrets["google_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Google Sheets authorization failed: {e}")
        st.stop()


# === READ URLS ===
def read_urls_from_sheet(client):
    """Read URLs from the Input sheet"""
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(INPUT_SHEET_NAME)
    urls = sheet.col_values(1)[1:]  # Skip header
    return [u.strip() for u in urls if u.strip()]


# === WRITE RESULTS ===
def write_results_to_sheet(client, results):
    """Write results to Output sheet"""
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(OUTPUT_SHEET_NAME)
    header = ["url", "error", "checked_at"] + TRACKERS
    rows = [header]

    for res in results:
        row = [res.get(col, "") for col in header]
        rows.append(row)

    sheet.clear()
    sheet.update("A1", rows, value_input_option="RAW")


# === CHECK URL ===
def check_url(url):
    """Check a single URL for trackers"""
    tracker_status = {t: False for t in TRACKERS}
    error_msg = ""

    # ✅ Get current time in IST (UTC+5:30)
    IST = timezone(timedelta(hours=5, minutes=30))
    checked_at = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=samsung_s24["user_agent"],
                viewport=samsung_s24["viewport"],
                device_scale_factor=samsung_s24["device_scale_factor"],
                is_mobile=samsung_s24["is_mobile"],
                has_touch=samsung_s24["has_touch"]
            )
            page = context.new_page()

            def handle_request(request):
                req_url = request.url.lower()
                for t in TRACKERS:
                    if t in req_url:
                        tracker_status[t] = True

            page.on("request", handle_request)
            page.goto(url, timeout=150000, wait_until="networkidle")
            page.mouse.wheel(0, 500)
            page.wait_for_timeout(5000)

            context.close()
            browser.close()
    except Exception as e:
        error_msg = str(e)

    result = {"url": url, "error": error_msg, "checked_at": checked_at}
    result.update(tracker_status)
    print(f"✅ Checked: {url} at {checked_at}")
    return result


# === STREAMLIT UI ===
def main():
    st.set_page_config(page_title="Google Sheet Tracker", page_icon="🔍", layout="wide")
    st.title("🔍 Google Sheets Tracker Tool")
    st.write("Check your Google Sheet URLs for trackers using Playwright automation.")

    if st.button("🚀 Run Tracker"):
        st.info("Running tracker... please wait.")
        client = authorize_gsheets()
        urls = read_urls_from_sheet(client)

        if not urls:
            st.warning("No URLs found in the Input sheet.")
            return

        st.write(f"Found **{len(urls)} URLs** to check...")
        results = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            for r in executor.map(check_url, urls):
                results.append(r)

        try:
            write_results_to_sheet(client, results)
            st.success(f"✅ Results written to Google Sheet '{OUTPUT_SHEET_NAME}' successfully!")
        except Exception as e:
            st.error(f"❌ Error writing results: {e}")


if __name__ == "__main__":
    main()
