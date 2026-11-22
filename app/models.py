from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Text,
    DateTime,
    Integer,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    authority: Mapped[str] = mapped_column(String(100))
    source_type: Mapped[str] = mapped_column(String(50))
    listing_url: Mapped[str] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(default=True)

    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    documents: Mapped[list["Document"]] = relationship(back_populates="source")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )

    notice_number: Mapped[str] = mapped_column(String(150))
    title: Mapped[str] = mapped_column(Text)

    publish_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    uploaded_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    document_url: Mapped[str] = mapped_column(Text)
    source_page_url: Mapped[str] = mapped_column(Text)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    # Tracks when TradePulse last checked this document.
    last_monitored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    source: Mapped["Source"] = relationship(back_populates="documents")

    __table_args__ = (
        UniqueConstraint("source_id", "document_url", name="uq_source_document_url"),
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(primary_key=True)

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )

    version_number: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    downloaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    document: Mapped["Document"] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_version"),
        UniqueConstraint("document_id", "sha256", name="uq_document_sha256"),
    )


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id: Mapped[int] = mapped_column(primary_key=True)

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )

    event_type: Mapped[str] = mapped_column(String(50))
    old_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class MonitoringRun(Base):
    __tablename__ = "monitoring_runs"

    id: Mapped[int] = mapped_column(primary_key=True)

    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    status: Mapped[str] = mapped_column(String(30))
    records_found: Mapped[int] = mapped_column(Integer, default=0)
    new_documents: Mapped[int] = mapped_column(Integer, default=0)
    changed_documents: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


Index("ix_documents_publish_date", Document.publish_date)
Index("ix_change_events_detected_at", ChangeEvent.detected_at)
Index("ix_documents_last_monitored_at", Document.last_monitored_at)
