from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, sessionmaker

from app.database import engine
from app.models import (
    Source,
    Document,
    DocumentVersion,
    ChangeEvent,
    MonitoringRun,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

app = FastAPI(
    title="TradePulse Intelligence API",
    description="Automated regulatory document monitoring and change detection.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "message": "TradePulse Intelligence API is running",
        "docs": "/docs",
    }


@app.get("/health")
def health(db: Session = Depends(get_db)):
    from sqlalchemy import text

    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    return {
        "total_documents": db.query(Document).count(),
        "total_sources": db.query(Source).count(),
        "total_versions": db.query(DocumentVersion).count(),
        "total_changes": db.query(ChangeEvent)
        .filter(ChangeEvent.event_type == "document_updated")
        .count(),
        "total_runs": db.query(MonitoringRun).count(),
    }


@app.get("/api/documents")
def documents(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 200))

    records = (
        db.query(Document)
        .order_by(Document.publish_date.desc().nullslast(), Document.id.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": item.id,
            "notice_number": item.notice_number,
            "title": item.title,
            "publish_date": (
                item.publish_date.isoformat() if item.publish_date else None
            ),
            "uploaded_date": (
                item.uploaded_date.isoformat() if item.uploaded_date else None
            ),
            "document_url": item.document_url,
            "source_page_url": item.source_page_url,
            "first_seen_at": (
                item.first_seen_at.isoformat() if item.first_seen_at else None
            ),
            "last_monitored_at": (
                item.last_monitored_at.isoformat() if item.last_monitored_at else None
            ),
        }
        for item in records
    ]


@app.get("/api/changes")
def changes(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 200))

    records = (
        db.query(ChangeEvent, Document)
        .join(Document, ChangeEvent.document_id == Document.id)
        .order_by(ChangeEvent.detected_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": event.id,
            "notice_number": document.notice_number,
            "title": document.title,
            "event_type": event.event_type,
            "description": event.description,
            "old_sha256": event.old_sha256,
            "new_sha256": event.new_sha256,
            "detected_at": (
                event.detected_at.isoformat() if event.detected_at else None
            ),
        }
        for event, document in records
    ]


@app.get("/api/runs")
def runs(
    limit: int = 20,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 100))

    records = (
        db.query(MonitoringRun)
        .order_by(MonitoringRun.started_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": run.id,
            "status": run.status,
            "records_found": run.records_found,
            "new_documents": run.new_documents,
            "changed_documents": run.changed_documents,
            "error_message": run.error_message,
            "started_at": (run.started_at.isoformat() if run.started_at else None),
            "finished_at": (run.finished_at.isoformat() if run.finished_at else None),
        }
        for run in records
    ]
