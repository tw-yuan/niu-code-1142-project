from app.services.chat_service import _demo_response, _quiz_metadata
from app.services.direction_service import fallback_dynamic_directions
from app.services.rag_service import _source_label


def test_fallback_dynamic_directions_returns_two_to_three_items():
    directions = fallback_dynamic_directions("資料結構 stack queue tree algorithm", "資料結構")

    assert 2 <= len(directions) <= 3
    assert all(item["is_dynamic"] for item in directions)
    assert {item["key"] for item in directions}


def test_demo_quiz_response_can_be_stored_as_quiz_metadata():
    response = _demo_response("quiz", "自我測驗", "請出題", "## Stack\n先進後出資料結構")
    metadata = _quiz_metadata("quiz", "請出題", response)

    assert metadata is not None
    assert metadata["kind"] == "quiz"
    assert metadata["status"] == "generated"
    assert metadata["question_count"] == 3


def test_quiz_metadata_extracts_score_when_available():
    metadata = _quiz_metadata("quiz", "我的答案", "批改結果：80 分。觀念大致正確。")

    assert metadata is not None
    assert metadata["status"] == "graded"
    assert metadata["score"] == 80


def test_source_label_uses_first_meaningful_line():
    assert _source_label("\n# 第三章 樹狀結構\n內容", 0) == "第三章 樹狀結構"


def test_source_label_falls_back_to_chunk_number():
    assert _source_label("\n\n", 2) == "片段 3"
