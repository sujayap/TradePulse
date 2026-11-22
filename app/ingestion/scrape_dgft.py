import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SOURCE_URL = "https://apeda.gov.in/dgft-notifications"

HEADERS = {"User-Agent": "TradePulse/1.0 (regulatory monitoring project)"}


def scrape_notifications():
    print("Connecting to DGFT Notifications page...")

    response = requests.get(SOURCE_URL, headers=HEADERS, timeout=60)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Find the notification table
    table = None

    for candidate in soup.find_all("table"):
        headers = [
            cell.get_text(" ", strip=True).lower() for cell in candidate.find_all("th")
        ]

        if any("notification no" in h for h in headers):
            table = candidate
            break

    if table is None:
        raise ValueError("Could not find the DGFT notifications table.")

    rows = table.find_all("tr")
    notifications = []

    for row in rows:
        cells = row.find_all("td")

        if len(cells) < 5:
            continue

        notification_number = cells[0].get_text(" ", strip=True)
        publish_date = cells[1].get_text(" ", strip=True)
        uploaded_date = cells[2].get_text(" ", strip=True)
        title = cells[3].get_text(" ", strip=True)

        # Find the PDF link in the File column
        link = cells[4].find("a", href=True)

        if not link:
            continue

        document_url = urljoin(SOURCE_URL, link["href"])

        notifications.append(
            {
                "notice_number": notification_number,
                "publish_date": publish_date,
                "uploaded_date": uploaded_date,
                "title": title,
                "document_url": document_url,
                "source_page_url": SOURCE_URL,
            }
        )

    return notifications


if __name__ == "__main__":
    try:
        notifications = scrape_notifications()

        print(f"\nNotifications discovered: {len(notifications)}")

        for index, item in enumerate(notifications[:10], start=1):
            print(f"\n--- Notification {index} ---")
            print("Number:", item["notice_number"])
            print("Published:", item["publish_date"])
            print("Uploaded:", item["uploaded_date"])
            print("Title:", item["title"])
            print("PDF:", item["document_url"])

    except Exception as error:
        print("\nScraping failed:")
        print(type(error).__name__, error)
