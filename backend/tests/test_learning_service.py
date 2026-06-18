from types import SimpleNamespace

from app.services.learning_service import LearningService, _score_quiz


class RecordingDB:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.committed = True


def test_score_quiz_normalizes_string_answers():
    questions = [{"answer": "A"}, {"answer": "B"}]

    assert _score_quiz(questions, {"0": " A ", "1": "C"}) == 0.5


def test_score_quiz_accepts_list_answers():
    questions = [{"answer": "A"}, {"answer": "B"}]

    assert _score_quiz(questions, ["A", "B"]) == 1.0


async def test_save_flashcards_preserves_allowed_multi_doc_source():
    db = RecordingDB()
    svc = LearningService(db)

    cards = await svc.save_flashcards(
        "user-1",
        ["doc-1", "doc-2"],
        """
        {
          "cards": [
            {"front": "A", "back": "B", "doc_id": "doc-2"},
            {"front": "C", "back": "D", "doc_id": "other-doc"}
          ]
        }
        """,
    )

    assert db.committed
    assert cards == db.added
    assert [card.doc_id for card in cards] == ["doc-2", None]


async def test_save_flashcards_defaults_single_doc_source():
    svc = LearningService(RecordingDB())

    cards = await svc.save_flashcards(
        "user-1",
        ["doc-1"],
        '{"cards": [{"front": "A", "back": "B"}]}',
    )

    assert cards[0].doc_id == "doc-1"


def test_attempt_summary_includes_answers_count_and_hidden_diagnostics():
    svc = LearningService(RecordingDB())
    attempt = SimpleNamespace(
        id="attempt-1",
        quiz_id="quiz-1",
        answers='{"0": "A", "1": "C"}',
        total_score=0.5,
        duration_sec=42,
        completed_at="2026-06-18T00:00:00+00:00",
    )

    result = svc._attempt_summary_out(
        attempt,
        questions=[
            {"question": "Q1", "answer": "A", "explanation": "E1"},
            {"question": "Q2", "answer": "B", "explanation": "E2"},
        ],
        include_answers=False,
        attempt_count=1,
    )

    assert result["answers"] == {"0": "A", "1": "C"}
    assert result["attempt_count"] == 1
    assert result["diagnostics"][0]["is_correct"] is True
    assert result["diagnostics"][0]["answer"] is None
    assert result["diagnostics"][1]["submitted_answer"] == "C"
