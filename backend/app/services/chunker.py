import re


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[dict]:
    pages = _split_pages(text)
    chunks: list[dict] = []
    chunk_index = 0
    for page_num, page_text in pages:
        sentences = _split_sentences(page_text)
        current = ""
        for sentence in sentences:
            if not sentence:
                continue
            if current and len(current) + len(sentence) > chunk_size:
                chunks.append(
                    {"text": current.strip(), "page_num": page_num, "chunk_index": chunk_index}
                )
                chunk_index += 1
                current = current[-overlap:] + sentence
            else:
                current += sentence
        if current.strip():
            chunks.append({"text": current.strip(), "page_num": page_num, "chunk_index": chunk_index})
            chunk_index += 1
    return chunks


def _split_pages(text: str) -> list[tuple[int, str]]:
    pattern = re.compile(r"===\s*第\s*(\d+)\s*頁\s*===\s*")
    matches = list(pattern.finditer(text))
    if not matches:
        return [(1, text)]
    pages: list[tuple[int, str]] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        pages.append((int(match.group(1)), text[start:end]))
    return pages


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?；;.\n])", text)
    return [part for part in parts if part.strip()]

