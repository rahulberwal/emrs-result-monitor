```python
import os
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import firebase_admin
from firebase_admin import messaging


# ============================================================
# CONFIGURATION
# ============================================================

# Target document repository.
# Set this through the MONITOR_BASE_URL environment variable.
BASE_URL = os.getenv(
    "MONITOR_BASE_URL",
    "https://example.com/documents/"
).rstrip("/") + "/"

# Number of timestamps to check when the monitor starts.
LOOK_BEHIND = int(
    os.getenv("LOOK_BEHIND", "1")
)

# Maximum number of concurrent HTTP requests.
MAX_WORKERS = int(
    os.getenv("MAX_WORKERS", "5")
)

# Seconds between scans.
SCAN_INTERVAL = float(
    os.getenv("SCAN_INTERVAL", "1")
)

# HTTP request timeout.
REQUEST_TIMEOUT = float(
    os.getenv("REQUEST_TIMEOUT", "8")
)

# Local storage.
DOWNLOAD_FOLDER = Path(
    os.getenv("DOWNLOAD_FOLDER", "./downloads")
)

STATE_FILE = Path(
    os.getenv("STATE_FILE", "./detected_files.txt")
)

DOWNLOAD_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# FIREBASE
# ============================================================

# Firebase Admin SDK uses Application Default Credentials.
#
# On Google Cloud, credentials are normally supplied by the
# VM's attached service account.
firebase_admin.initialize_app()


FCM_TOPIC = os.getenv(
    "FCM_TOPIC",
    "result_updates"
)


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 "
        "(compatible; PDF-Monitor/1.0)"
    )
})


# ============================================================
# STATE MANAGEMENT
# ============================================================

def load_detected_files():
    """Load filenames that have already been processed."""

    if not STATE_FILE.exists():
        return set()

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return {
                line.strip()
                for line in file
                if line.strip()
            }

    except OSError:
        return set()


def save_detected_file(filename):
    """Persist a processed filename."""

    with open(
        STATE_FILE,
        "a",
        encoding="utf-8"
    ) as file:
        file.write(filename + "\n")


# ============================================================
# PDF DETECTION
# ============================================================

def check_pdf(timestamp):
    """
    Check whether a timestamp-based PDF exists.

    The monitor assumes documents follow the pattern:

        <unix_timestamp>.pdf
    """

    filename = f"{timestamp}.pdf"
    url = BASE_URL + filename

    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        is_pdf = (
            "application/pdf" in content_type
            or response.content[:4] == b"%PDF"
        )

        if response.status_code == 200 and is_pdf:
            return {
                "timestamp": timestamp,
                "filename": filename,
                "url": url,
                "data": response.content
            }

    except requests.RequestException:
        pass

    return None


# ============================================================
# FIREBASE CLOUD MESSAGING
# ============================================================

def send_notification(filename, url):
    """Send a notification to all subscribers of the topic."""

    message = messaging.Message(
        notification=messaging.Notification(
            title="New Result Document",
            body=f"New PDF detected: {filename}"
        ),
        data={
            "title": "New Result Document",
            "body": f"New PDF detected: {filename}",
            "url": url
        },
        topic=FCM_TOPIC
    )

    response = messaging.send(message)

    print()
    print("FCM notification sent successfully.")
    print("FCM response:", response)


# ============================================================
# HANDLE DETECTED PDF
# ============================================================

def handle_pdf(result, detected_files):
    """Process a newly discovered PDF."""

    if result is None:
        return

    filename = result["filename"]

    # Prevent duplicate processing.
    if filename in detected_files:
        return

    timestamp = result["timestamp"]
    url = result["url"]
    pdf_data = result["data"]

    # Mark the document before notification to prevent
    # duplicate alerts if the same timestamp is encountered.
    detected_files.add(filename)
    save_detected_file(filename)

    detected_time = datetime.now()

    file_time = datetime.fromtimestamp(timestamp)

    print()
    print("=" * 65)
    print("                 !!! PDF FOUND !!!")
    print("=" * 65)

    print("Filename       :", filename)
    print("URL            :", url)

    print(
        "Timestamp time :",
        file_time.strftime("%d-%m-%Y %I:%M:%S %p")
    )

    print(
        "Detected at    :",
        detected_time.strftime("%d-%m-%Y %I:%M:%S %p")
    )

    print(
        "Size           :",
        len(pdf_data),
        "bytes"
    )

    # Save the PDF locally.
    output_path = DOWNLOAD_FOLDER / filename

    with open(
        output_path,
        "wb"
    ) as file:
        file.write(pdf_data)

    print()
    print("PDF SAVED TO:")
    print(output_path)

    # Send notification.
    try:
        send_notification(
            filename,
            url
        )

    except Exception as error:
        print()
        print("ERROR sending FCM notification:")
        print(error)

    print("=" * 65)
    print()


# ============================================================
# MAIN MONITOR
# ============================================================

def main():

    print()
    print("=" * 65)
    print("              TIMESTAMP PDF MONITOR")
    print("=" * 65)

    print(
        "Look-behind    :",
        LOOK_BEHIND,
        "second(s)"
    )

    print(
        "Concurrent     :",
        MAX_WORKERS,
        "requests"
    )

    print(
        "Scan interval  :",
        SCAN_INTERVAL,
        "second(s)"
    )

    print(
        "Started        :",
        datetime.now().strftime(
            "%d-%m-%Y %I:%M:%S %p"
        )
    )

    print("=" * 65)
    print()

    detected_files = load_detected_files()

    print(
        "Previously detected files:",
        len(detected_files)
    )

    print()
    print("Monitoring... Press CTRL+C to stop.")
    print()

    last_checked = None

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        next_scan = time.monotonic()

        while True:

            now = time.monotonic()

            if now < next_scan:
                time.sleep(
                    next_scan - now
                )

            next_scan += SCAN_INTERVAL

            current_timestamp = int(
                time.time()
            )

            # ------------------------------------------------
            # Determine which timestamps need checking.
            # ------------------------------------------------

            if last_checked is None:

                # Startup safety window.
                timestamps = [
                    current_timestamp - i
                    for i in range(
                        LOOK_BEHIND,
                        -1,
                        -1
                    )
                ]

            else:

                start = last_checked + 1
                end = current_timestamp

                if start <= end:

                    timestamps = list(
                        range(
                            start,
                            end + 1
                        )
                    )

                else:

                    # Clock did not advance.
                    timestamps = [
                        current_timestamp
                    ]

            last_checked = max(timestamps)

            current_time = datetime.now().strftime(
                "%I:%M:%S %p"
            )

            print(
                f"[{current_time}] "
                f"Checking "
                f"{len(timestamps)} timestamp(s) "
                f"({timestamps[0]} → "
                f"{timestamps[-1]})"
            )

            futures = [
                executor.submit(
                    check_pdf,
                    timestamp
                )
                for timestamp in timestamps
            ]

            for future in as_completed(futures):

                result = future.result()

                handle_pdf(
                    result,
                    detected_files
                )

            # Prevent excessive timing drift.
            if time.monotonic() > (
                next_scan + SCAN_INTERVAL
            ):
                next_scan = time.monotonic()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:

        print()
        print("=" * 65)
        print("Monitor stopped by user.")
        print("=" * 65)
```
