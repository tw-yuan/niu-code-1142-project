from app.schemas import CourseDocumentRequest
from app.services.courses_service import _course_document_ids


def test_course_document_ids_accepts_legacy_single_doc_id():
    body = CourseDocumentRequest(doc_id="doc-1")

    assert _course_document_ids(body) == ["doc-1"]


def test_course_document_ids_combines_and_deduplicates_bulk_doc_ids():
    body = CourseDocumentRequest(doc_id="doc-1", doc_ids=["doc-2", "doc-1", "doc-3"])

    assert _course_document_ids(body) == ["doc-1", "doc-2", "doc-3"]
