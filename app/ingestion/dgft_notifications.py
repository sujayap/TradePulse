import hashlib
from io import BytesIO

import requests
import pypdfium2 as pdfium

from docx import Document as WordDocument
from pypdf import PdfReader
from rapidocr import RapidOCR

HEADERS = {"User-Agent": "TradePulse/1.0 (regulatory monitoring project)"}


def download_document(url):
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()

    content = response.content

    if content.startswith(b"%PDF"):
        document_type = "pdf"

    elif content.startswith(b"PK"):
        document_type = "docx"

    else:
        raise ValueError(
            f"Unsupported document format: {response.headers.get('Content-Type')}"
        )

    return content, document_type


def calculate_sha256(content):
    return hashlib.sha256(content).hexdigest()


def extract_pdf_text(content):
    reader = PdfReader(BytesIO(content))

    pages = [page.extract_text() or "" for page in reader.pages]

    native_text = "\n".join(pages).strip()

    if native_text:
        return native_text, "native_pdf"

    print("No selectable text found. Starting OCR...")

    engine = RapidOCR()
    pdf = pdfium.PdfDocument(content)

    ocr_pages = []

    for page_number in range(len(pdf)):
        page = pdf[page_number]
        image = page.render(scale=2).to_pil()

        result = engine(image)

        page_text = "\n".join(result.txts) if result.txts else ""
        ocr_pages.append(page_text)

        print(f"OCR completed: page {page_number + 1}/{len(pdf)}")

    return "\n".join(ocr_pages).strip(), "rapidocr"


def extract_docx_text(content):
    document = WordDocument(BytesIO(content))

    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    # Also extract text from tables.
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]

            paragraphs.append(" | ".join(cells))

    return "\n".join(paragraphs), "python_docx"


def extract_text(content, document_type):
    if document_type == "pdf":
        return extract_pdf_text(content)

    if document_type == "docx":
        return extract_docx_text(content)

    raise ValueError(f"Unsupported document type: {document_type}")


if __name__ == "__main__":
    test_urls = [
        (
            "https://apeda.gov.in/sites/default/files/dgft_notifications/Notification_48_2026_27.pdf",
            "PDF test",
        ),
        (
            "https://apeda.gov.in/sites/default/files/dgft_notifications/TO%20BE%20PUBLISHED%20IN%20THE%20GAZETTE%2010_2_0.docx",
            "DOCX test",
        ),
    ]

    for url, label in test_urls:
        print(f"\n========== {label} ==========")

        try:
            content, document_type = download_document(url)

            print("Format:", document_type)
            print("Size:", len(content), "bytes")
            print("SHA-256:", calculate_sha256(content))

            text, method = extract_text(content, document_type)

            print("Extraction method:", method)
            print("Extracted characters:", len(text))
            print("\nPreview:\n")
            print(text[:1000])

        except Exception as error:
            print("Processing failed:", type(error).__name__, error)
