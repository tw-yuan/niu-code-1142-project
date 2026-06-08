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


def _collection_name(doc_id: int) -> str:
    return f"doc_{doc_id}"


async def index_document(doc_id: int, text: str) -> None:
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
    col.upsert(ids=ids, embeddings=embeddings, documents=chunks)


async def search_document(doc_id: int, query: str) -> list[str]:
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
    )
    return results["documents"][0] if results["documents"] else []


def delete_document_index(doc_id: int) -> None:
    client = get_chroma_client()
    try:
        client.delete_collection(_collection_name(doc_id))
    except Exception:
        pass


async def get_context(doc_id: int, token_count: int, full_text: str, query: str) -> str:
    if token_count < settings.rag_token_threshold:
        return full_text
    chunks = await search_document(doc_id, query)
    if not chunks:
        return full_text[:8000]
    return "\n\n---\n\n".join(chunks)
