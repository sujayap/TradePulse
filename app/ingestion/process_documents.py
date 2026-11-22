from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import engine
from app.models import Document, DocumentVersion, ChangeEvent, MonitoringRun

from app.ingestion.dgft_notifications import (
    download_document,
    calculate_sha256,
    extract_text,
)

BATCH_SIZE = 3
STORAGE_DIR = Path("data/documents")


def process_documents():

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    with Session(engine) as session:

        # Find documents that have not been downloaded and versioned.
        documents = session.scalars(
            select(Document)
            .outerjoin(DocumentVersion, Document.id == DocumentVersion.document_id)
            # .where(Document.document_url.ilike("%.docx"))
            .order_by(Document.id)
            .limit(BATCH_SIZE)
        ).all()

        if not documents:
            print("No unprocessed documents found.")
            return

        source_id = documents[0].source_id

        run = MonitoringRun(
            source_id=source_id, started_at=datetime.now(timezone.utc), status="running"
        )

        session.add(run)
        session.commit()

        processed = 0
        failed = 0

        print(f"Documents selected: {len(documents)}")

        for document in documents:

            print("\n--------------------------------")
            print("Notification:", document.notice_number)
            print("Title:", document.title)
            print("URL:", document.document_url)

            try:
                # Download the original document.
                content, document_type = download_document(document.document_url)

                # Calculate fingerprint from original bytes.
                fingerprint = calculate_sha256(content)

                # Extract document text.
                extracted_text, extraction_method = extract_text(content, document_type)

                if not extracted_text.strip():
                    raise ValueError("No text could be extracted.")

                # Store original file using its fingerprint.
                extension = document_type
                file_path = STORAGE_DIR / f"{fingerprint}.{extension}"

                if not file_path.exists():
                    file_path.write_bytes(content)

                # Determine next version number.
                latest_version = session.scalar(
                    select(func.max(DocumentVersion.version_number)).where(
                        DocumentVersion.document_id == document.id
                    )
                )

                version_number = (latest_version or 0) + 1

                version = DocumentVersion(
                    document_id=document.id,
                    version_number=version_number,
                    sha256=fingerprint,
                    extracted_text=extracted_text,
                    downloaded_at=datetime.now(timezone.utc),
                )

                session.add(version)
                session.flush()

                # Initial capture: no earlier version was stored.
                event = ChangeEvent(
                    document_id=document.id,
                    event_type="initial_capture",
                    old_sha256=None,
                    new_sha256=fingerprint,
                    description=(
                        f"Initial document captured. "
                        f"Format: {document_type}. "
                        f"Extraction: {extraction_method}."
                    ),
                    detected_at=datetime.now(timezone.utc),
                )

                session.add(event)
                session.commit()

                processed += 1

                print("Format:", document_type)
                print("Extraction:", extraction_method)
                print("Characters:", len(extracted_text))
                print("SHA-256:", fingerprint)
                print("Version:", version_number)
                print("Saved successfully.")

            except Exception as error:
                session.rollback()
                failed += 1

                print("Processing failed:", type(error).__name__, error)

        # Update monitoring run.
        run = session.get(MonitoringRun, run.id)

        run.records_found = len(documents)
        run.new_documents = 0
        run.changed_documents = 0
        run.status = "success" if failed == 0 else "partial_success"
        run.error_message = f"{failed} document(s) failed." if failed else None
        run.finished_at = datetime.now(timezone.utc)

        session.commit()

        print("\n========== PROCESSING SUMMARY ==========")
        print("Selected:", len(documents))
        print("Processed:", processed)
        print("Failed:", failed)


if __name__ == "__main__":
    process_documents()
