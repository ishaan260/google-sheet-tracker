import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# === CONFIGURATION ===
SERVICE_ACCOUNT_FILE = r"C:\Users\ishaan jairath\Downloads\theta-reserve-472516-h1-b2f908ac6210.json"  # <-- update this
SPREADSHEET_ID = "1CW62XUrBmI7O6LZ-2EUyw6oVKfx871oE2ZD_KF02fxg"                       # <-- update this
INPUT_SHEET_NAME = "Input"
OUTPUT_SHEET_NAME = "Output"

TRACKERS = ["scorecard", "adform.ne", "adventity", "flashtalking", "doubleverify", "moat", "gampad","chartbeat","collect?v=2","trackimp"]

# Samsung Galaxy S24 device descriptor
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
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def read_urls_from_sheet(client):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(INPUT_SHEET_NAME)
    # Read all values in first column, skip header
    urls = sheet.col_values(1)[1:]
    return urls

def write_results_to_sheet(client, results):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(OUTPUT_SHEET_NAME)
    header = ['url', 'error', 'checked_at'] + TRACKERS
    rows = [header]
    for res in results:
        row = [res.get(col, '') for col in header]
        rows.append(row)
    sheet.clear()
    sheet.update('A1', rows)

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
    client = authorize_gsheets()
    urls = read_urls_from_sheet(client)
    print(f"Read {len(urls)} URLs from Google Sheet.")

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(check_url, urls))

    write_results_to_sheet(client, results)
    print(f"\nResults written to Google Sheet '{OUTPUT_SHEET_NAME}' tab successfully!")

if __name__ == "__main__":
    main()