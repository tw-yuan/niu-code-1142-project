from app.services.learning_service import _score_quiz


def test_score_quiz_normalizes_string_answers():
    questions = [{"answer": "A"}, {"answer": "B"}]

    assert _score_quiz(questions, {"0": " A ", "1": "C"}) == 0.5


def test_score_quiz_accepts_list_answers():
    questions = [{"answer": "A"}, {"answer": "B"}]

    assert _score_quiz(questions, ["A", "B"]) == 1.0
