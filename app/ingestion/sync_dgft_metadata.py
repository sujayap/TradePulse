from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.models import Source, Document, MonitoringRun
from app.ingestion.scrape_dgft import scrape_notifications

SOURCE_NAME = "DGFT Notifications"
SOURCE_URL = "https://apeda.gov.in/dgft-notifications"


def parse_date(value):
    cleaned = " ".join(value.split())

    if not cleaned:
        return None

    parsed = datetime.strptime(cleaned, "%d %B, %Y")

    return parsed.replace(tzinfo=ZoneInfo("Asia/Kolkata"))


def sync_metadata():
    print("Discovering DGFT notifications...")

    notifications = scrape_notifications()

    now = datetime.now(timezone.utc)

    new_documents = 0
    updated_documents = 0

    with Session(engine) as session:

        # Find or create the source.
        source = session.scalar(select(Source).where(Source.name == SOURCE_NAME))

        if source is None:
            source = Source(
                name=SOURCE_NAME,
                authority="Directorate General of Foreign Trade",
                source_type="notifications",
                listing_url=SOURCE_URL,
                is_active=True,
            )

            session.add(source)
            session.flush()

            print("Created DGFT source.")

        # Start a monitoring run.
        run = MonitoringRun(source_id=source.id, started_at=now, status="running")

        session.add(run)
        session.flush()

        try:
            for item in notifications:

                document_url = item["document_url"]

                document = session.scalar(
                    select(Document).where(
                        Document.source_id == source.id,
                        Document.document_url == document_url,
                    )
                )

                if document is None:
                    document = Document(
                        source_id=source.id,
                        notice_number=item["notice_number"],
                        title=item["title"],
                        publish_date=parse_date(item["publish_date"]),
                        uploaded_date=parse_date(item["uploaded_date"]),
                        document_url=document_url,
                        source_page_url=item["source_page_url"],
                        first_seen_at=now,
                        last_seen_at=now,
                    )

                    session.add(document)
                    new_documents += 1

                else:
                    document.notice_number = item["notice_number"]
                    document.title = item["title"]
                    document.publish_date = parse_date(item["publish_date"])
                    document.uploaded_date = parse_date(item["uploaded_date"])
                    document.source_page_url = item["source_page_url"]
                    document.last_seen_at = now

                    updated_documents += 1

            run.records_found = len(notifications)
            run.new_documents = new_documents
            run.changed_documents = 0
            run.status = "success"
            run.finished_at = datetime.now(timezone.utc)

            source.last_checked_at = now
            source.last_success_at = now

            session.commit()

        except Exception:
            session.rollback()
            raise

    print("\n========== METADATA SYNC COMPLETE ==========")
    print("Records discovered:", len(notifications))
    print("New documents saved:", new_documents)
    print("Existing documents refreshed:", updated_documents)
    print("Missing dates preserved as NULL.")
    print("Monitoring run: success")


if __name__ == "__main__":
    try:
        sync_metadata()

    except Exception as error:
        print("\nMetadata sync failed:")
        print(type(error).__name__, error)
        raise
