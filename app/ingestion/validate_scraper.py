from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

from app.ingestion.scrape_dgft import scrape_notifications


def parse_date(value):
    cleaned = " ".join(value.split())

    # Older source records may not contain dates.
    if not cleaned:
        return None

    parsed = datetime.strptime(cleaned, "%d %B, %Y")

    return parsed.replace(tzinfo=ZoneInfo("Asia/Kolkata"))


def main():
    notifications = scrape_notifications()

    valid_records = 0
    incomplete_records = []
    invalid_records = []

    for item in notifications:
        try:
            publish_date = parse_date(item["publish_date"])
            uploaded_date = parse_date(item["uploaded_date"])

            if not item["notice_number"] or not item["title"]:
                raise ValueError("Missing notification number or title")

            if not item["document_url"].lower().endswith(".pdf"):
                raise ValueError("Unexpected document URL")

            valid_records += 1

            if publish_date is None or uploaded_date is None:
                incomplete_records.append(
                    {
                        "notice": item["notice_number"],
                        "publish_date_missing": publish_date is None,
                        "uploaded_date_missing": uploaded_date is None,
                    }
                )

        except Exception as error:
            invalid_records.append(
                {"notice": item.get("notice_number"), "error": str(error)}
            )

    notice_counts = Counter(item["notice_number"] for item in notifications)

    duplicate_numbers = {
        number: count for number, count in notice_counts.items() if count > 1
    }

    unique_urls = len({item["document_url"] for item in notifications})

    print("\n========== TRADEPULSE VALIDATION ==========")
    print("Total records:", len(notifications))
    print("Valid records:", valid_records)
    print("Records with missing dates:", len(incomplete_records))
    print("Invalid records:", len(invalid_records))
    print("Unique PDF URLs:", unique_urls)
    print("Duplicate notification numbers:", len(duplicate_numbers))

    print("\nIncomplete record examples:")
    for item in incomplete_records[:10]:
        print(item)

    print("\nInvalid record examples:")
    for item in invalid_records[:10]:
        print(item)

    print("\nDate parsing example:")
    if notifications:
        first = notifications[0]
        print("Published:", parse_date(first["publish_date"]))
        print("Uploaded:", parse_date(first["uploaded_date"]))


if __name__ == "__main__":
    main()
