import os
import json
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import streamlit as st
import threading
import time

# ✅ Ensure Playwright Chromium is installed (for Streamlit Cloud)
os.system("playwright install chromium > /dev/null 2>&1")

# === CONFIGURATION ===
SPREADSHEET_ID = "1CW62XUrBmI7O6LZ-2EUyw6oVKfx871oE2ZD_KF02fxg"
INPUT_SHEET_NAME = "Input"
OUTPUT_SHEET_NAME = "Output"

TRACKERS = [
    "scorecard",
    "adform.ne",
    "adventity",
    "flashtalking",
    "doubleverify",
    "moat",
    "gampad",
    "chartbeat",
    "collect?v=2",
    "trackimp"
]

# Samsung S24 device emulation
samsung_s24 = {
    "name": "Samsung Galaxy S24",
    "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.133 Mobile Safari/537.36",
    "viewport": {"width": 1080, "height": 2340},
    "device_scale_factor": 3,
    "is_mobile": True,
    "has_touch": True,
}

# === TIMEZONE ===
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_time():
    """Return current IST time string."""
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

# === GOOGLE SHEETS AUTH ===
def authorize_gsheets():
    try:
        creds_dict = st.secrets["google_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Google Sheets authorization failed: {e}")
        st.stop()

# === READ URLS ===
def read_urls_from_sheet(client):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(INPUT_SHEET_NAME)
    urls = sheet.col_values(1)[1:]  # Skip header
    return [url.strip() for url in urls if url.strip()]

# === WRITE RESULTS ===
def append_result_to_sheet(client, result):
    """Append a single result row as soon as it finishes."""
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(OUTPUT_SHEET_NAME)
    header = ["url", "error", "checked_at"] + TRACKERS

    # If sheet is empty, add header
    if not sheet.get_all_values():
        sheet.append_row(header, value_input_option="RAW")

    row = [result.get(col, "") for col in header]
    sheet.append_row(row, value_input_option="RAW")

# === TRACKER CHECK ===
def check_url(url):
    tracker_status = {tracker: False for tracker in TRACKERS}
    error_msg = ""
    checked_at = get_ist_time()

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
            page.wait_for_timeout(5000)
            context.close()
            browser.close()

    except Exception as e:
        error_msg = str(e)

    result = {"url": url, "error": error_msg, "checked_at": checked_at}
    result.update(tracker_status)

    print(f"[{checked_at}] ✅ Checked: {url}")
    return result

# === BACKGROUND PROCESS RUNNER ===
def run_tracker_in_background():
    """Run tracker even if Streamlit UI is closed."""
    client = authorize_gsheets()
    urls = read_urls_from_sheet(client)

    print(f"🕒 Started tracking at {get_ist_time()} with {len(urls)} URLs")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(check_url, url): url for url in urls}

        for future in as_completed(futures):
            result = future.result()
            append_result_to_sheet(client, result)

    print(f"✅ All tasks done at {get_ist_time()}")

# === STREAMLIT UI ===
def main():
    st.set_page_config(page_title="Google Sheet Tracker", page_icon="🔍", layout="wide")
    st.title("🔍 Google Sheets Tracker Tool (Auto-Resilient Mode)")
    st.write("This tool runs in background — even if you close the tab or your system sleeps.")
    st.write(f"🕒 Current Time (IST): **{get_ist_time()}**")

    if st.button("🚀 Start Background Tracker"):
        st.success("Tracking started in background — you can close this tab safely.")
        thread = threading.Thread(target=run_tracker_in_background, daemon=True)
        thread.start()
        st.stop()  # End Streamlit request so background continues

if __name__ == "__main__":
    main()
