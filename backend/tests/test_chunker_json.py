from app.services.chunker import chunk_text
from app.services.json_utils import parse_json_llm


def test_chunk_text_tracks_page_numbers():
    text = "=== 第 1 頁 ===\n第一頁第一句。第一頁第二句。\n\n=== 第 2 頁 ===\n第二頁內容。"

    chunks = chunk_text(text, chunk_size=20, overlap=0)

    assert chunks
    assert {chunk["page_num"] for chunk in chunks} == {1, 2}
    assert chunks[0]["chunk_index"] == 0


def test_parse_json_llm_strips_markdown_fence():
    parsed = parse_json_llm('```json\n{"questions": []}\n```')

    assert parsed == {"questions": []}

