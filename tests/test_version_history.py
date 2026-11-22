from datetime import datetime, timezone
from pathlib import Path
import hashlib

from sqlalchemy.orm import sessionmaker

from app.database import engine
from app.models import (
    Source,
    Document,
    DocumentVersion,
    ChangeEvent,
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

TEST_FILE = Path("tests/fixtures/change_test.txt")


def calculate_sha256(content):
    return hashlib.sha256(content).hexdigest()


def main():
    session = SessionLocal()

    try:
        # Create an isolated test source.
        source = Source(
            name="TradePulse Integration Test",
            authority="TradePulse Test",
            source_type="test",
            listing_url="https://example.com/test",
        )
        session.add(source)
        session.flush()

        # Create a test document.
        document = Document(
            source_id=source.id,
            notice_number="TEST-001",
            title="TradePulse Version History Test",
            document_url="https://example.com/test/document.txt",
            source_page_url="https://example.com/test",
        )
        session.add(document)
        session.flush()

        # Save version 1.
        original_content = TEST_FILE.read_bytes()
        original_hash = calculate_sha256(original_content)

        version_1 = DocumentVersion(
            document_id=document.id,
            version_number=1,
            sha256=original_hash,
            extracted_text=original_content.decode("utf-8"),
        )
        session.add(version_1)
        session.flush()

        print("Version 1 saved:", original_hash)

        # Simulate an amended document.
        updated_content = (
            original_content + b"\n\nVersion: 2\n" + b"An amendment has been added."
        )

        updated_hash = calculate_sha256(updated_content)

        # Compare fingerprints.
        if updated_hash == original_hash:
            raise RuntimeError("Change was not detected.")

        # Save version 2.
        version_2 = DocumentVersion(
            document_id=document.id,
            version_number=2,
            sha256=updated_hash,
            extracted_text=updated_content.decode("utf-8"),
        )
        session.add(version_2)

        # Record the change event.
        event = ChangeEvent(
            document_id=document.id,
            event_type="document_updated",
            old_sha256=original_hash,
            new_sha256=updated_hash,
            description="Integration test: simulated document amendment.",
            detected_at=datetime.now(timezone.utc),
        )
        session.add(event)

        session.commit()

        print("\nVersion 2 saved:", updated_hash)
        print("Change event created:", event.event_type)

        # Verify the stored history.
        versions = (
            session.query(DocumentVersion)
            .filter_by(document_id=document.id)
            .order_by(DocumentVersion.version_number)
            .all()
        )

        events = session.query(ChangeEvent).filter_by(document_id=document.id).all()

        assert len(versions) == 2
        assert versions[0].version_number == 1
        assert versions[1].version_number == 2
        assert len(events) == 1
        assert events[0].old_sha256 == original_hash
        assert events[0].new_sha256 == updated_hash

        print("\n========== TEST RESULTS ==========")
        print("Document ID:", document.id)
        print("Versions stored:", len(versions))
        print("Change events:", len(events))
        print("Old and new fingerprints verified.")
        print("SUCCESS: Version history works!")

        # Keep the test source/document for manual inspection.
        print("\nTest records retained in the database.")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()
