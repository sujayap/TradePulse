from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

from app.database import engine
from app.models import (
    Document,
    DocumentVersion,
    ChangeEvent,
    MonitoringRun,
)

from app.ingestion.dgft_notifications import (
    download_document,
    calculate_sha256,
    extract_text,
)

BATCH_SIZE = 3

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def utc_now():
    return datetime.now(timezone.utc)


def detect_changes():
    session = SessionLocal()

    processed = 0
    changed = 0
    unchanged = 0
    failed = 0

    run_id = None

    try:
        # Select documents with the oldest monitoring timestamps.
        # Documents never checked are prioritized first.
        document_ids = [
            row[0]
            for row in (
                session.query(Document.id)
                .join(DocumentVersion)
                .group_by(Document.id)
                .order_by(
                    Document.last_monitored_at.asc().nullsfirst(),
                    Document.id.asc(),
                )
                .limit(BATCH_SIZE)
                .all()
            )
        ]

        print(f"Documents selected: {len(document_ids)}")

        if not document_ids:
            print("No previously captured documents found.")
            return

        first_document = session.get(Document, document_ids[0])

        run = MonitoringRun(
            source_id=first_document.source_id,
            started_at=utc_now(),
            status="running",
            records_found=len(document_ids),
            new_documents=0,
            changed_documents=0,
        )

        session.add(run)
        session.commit()
        run_id = run.id

        for document_id in document_ids:
            try:
                document = session.get(Document, document_id)

                print("\n--------------------------------")
                print(f"Notification: {document.notice_number}")
                print(f"Title: {document.title}")

                latest_version = (
                    session.query(DocumentVersion)
                    .filter_by(document_id=document_id)
                    .order_by(DocumentVersion.version_number.desc())
                    .first()
                )

                if latest_version is None:
                    raise ValueError("No previous document version found.")

                # Download the current source document.
                content, document_type = download_document(document.document_url)

                new_hash = calculate_sha256(content)

                print("Downloaded successfully.")
                print("SHA-256:", new_hash)

                # Compare with the latest stored fingerprint.
                if new_hash == latest_version.sha256:
                    print("Result: No changes detected.")
                    unchanged += 1

                else:
                    extracted_text, extraction_method = extract_text(
                        content,
                        document_type,
                    )

                    if not extracted_text.strip():
                        raise ValueError("Extracted document text is empty.")

                    new_version_number = latest_version.version_number + 1

                    new_version = DocumentVersion(
                        document_id=document_id,
                        version_number=new_version_number,
                        sha256=new_hash,
                        extracted_text=extracted_text,
                        downloaded_at=utc_now(),
                    )

                    event = ChangeEvent(
                        document_id=document_id,
                        event_type="document_updated",
                        old_sha256=latest_version.sha256,
                        new_sha256=new_hash,
                        description=(
                            f"Document changed. Version "
                            f"{latest_version.version_number} -> "
                            f"{new_version_number}. "
                            f"Extraction method: {extraction_method}."
                        ),
                        detected_at=utc_now(),
                    )

                    session.add(new_version)
                    session.add(event)

                    print("DOCUMENT CHANGE DETECTED!")
                    print("New version:", new_version_number)

                    changed += 1

                # Record the monitoring attempt.
                document.last_monitored_at = utc_now()

                session.commit()
                processed += 1

            except Exception as error:
                session.rollback()
                failed += 1

                print(
                    "Processing failed:",
                    type(error).__name__,
                    error,
                )

                # Record failed attempts too, so a broken source
                # does not monopolize every monitoring batch.
                document = session.get(Document, document_id)

                if document is not None:
                    document.last_monitored_at = utc_now()
                    session.commit()

        # Update the monitoring run.
        run = session.get(MonitoringRun, run_id)

        run.finished_at = utc_now()
        run.changed_documents = changed

        if failed == 0:
            run.status = "success"
        elif processed > 0:
            run.status = "partial_success"
        else:
            run.status = "failed"

        if failed:
            run.error_message = f"{failed} document(s) failed."

        session.commit()

        print("\n========== MONITORING SUMMARY ==========")
        print("Selected:", len(document_ids))
        print("Processed:", processed)
        print("Unchanged:", unchanged)
        print("Changed:", changed)
        print("Failed:", failed)

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    detect_changes()
