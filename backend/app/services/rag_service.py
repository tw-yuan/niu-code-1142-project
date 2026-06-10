import tiktoken
import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import AsyncOpenAI

from app.config import settings

_chroma_client = None
_openai_client: AsyncOpenAI | None = None


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        settings.chromadb_dir.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=str(settings.chromadb_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(
            base_url=settings.openai_compatible_base_url,
            api_key=settings.openai_compatible_api_key or "none",
        )
    return _openai_client


def _split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))
        if end == len(tokens):
            break
        start += chunk_size - overlap
    return chunks


def _source_label(chunk: str, index: int) -> str:
    for line in chunk.splitlines():
        clean = line.strip(" #\t")
        if clean:
            return clean[:80]
    return f"片段 {index + 1}"


def _collection_name(doc_id: int) -> str:
    return f"doc_{doc_id}"


async def index_document(doc_id: int, user_id: int, text: str) -> None:
    client = get_chroma_client()
    col = client.get_or_create_collection(name=_collection_name(doc_id))

    chunks = _split_into_chunks(text, settings.rag_chunk_size, settings.rag_chunk_overlap)
    if not chunks:
        return

    oai = get_openai_client()
    response = await oai.embeddings.create(
        model=settings.embedding_model,
        input=chunks,
    )
    embeddings = [item.embedding for item in response.data]

    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "user_id": user_id,
            "doc_id": doc_id,
            "chunk_index": i,
            "source_label": _source_label(chunks[i], i),
        }
        for i in range(len(chunks))
    ]
    col.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)


async def search_document(doc_id: int, user_id: int, query: str) -> list[dict]:
    client = get_chroma_client()
    try:
        col = client.get_collection(name=_collection_name(doc_id))
    except Exception:
        return []

    oai = get_openai_client()
    response = await oai.embeddings.create(
        model=settings.embedding_model,
        input=[query],
    )
    query_embedding = response.data[0].embedding

    results = col.query(
        query_embeddings=[query_embedding],
        n_results=min(settings.rag_top_k, col.count()),
        where={"user_id": user_id},
    )
    docs = results["documents"][0] if results["documents"] else []
    metas = results["metadatas"][0] if results.get("metadatas") else []
    out = []
    for i, text in enumerate(docs):
        metadata = metas[i] if i < len(metas) and metas[i] else {}
        out.append(
            {
                "chunk_index": metadata.get("chunk_index", i),
                "source_label": metadata.get("source_label") or _source_label(text, i),
                "text": text,
                "snippet": text[:500],
            }
        )
    return out


def delete_document_index(doc_id: int) -> None:
    client = get_chroma_client()
    try:
        client.delete_collection(_collection_name(doc_id))
    except Exception:
        pass


async def get_context_with_sources(
    doc_id: int,
    user_id: int,
    token_count: int,
    full_text: str,
    query: str,
) -> tuple[str, list[dict]]:
    if token_count < settings.rag_token_threshold:
        source = {
            "chunk_index": 0,
            "source_label": "全文模式",
            "snippet": full_text[:500],
            "text": full_text[:2000],
        }
        return full_text, [source]
    if settings.demo_mode or not settings.openai_compatible_api_key:
        source = {
            "chunk_index": 0,
            "source_label": "示範模式全文節錄",
            "snippet": full_text[:500],
            "text": full_text[:2000],
        }
        return full_text[:8000], [source]
    chunks = await search_document(doc_id, user_id, query)
    if not chunks:
        source = {
            "chunk_index": 0,
            "source_label": "全文備援",
            "snippet": full_text[:500],
            "text": full_text[:2000],
        }
        return full_text[:8000], [source]
    return "\n\n---\n\n".join(c["text"] for c in chunks), chunks


async def get_context(doc_id: int, user_id: int, token_count: int, full_text: str, query: str) -> str:
    context, _ = await get_context_with_sources(doc_id, user_id, token_count, full_text, query)
    return context
