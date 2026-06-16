import asyncio
from pathlib import Path
from typing import Any

from filelock import FileLock

from app.config import settings
from app.dependencies import get_chroma, get_documents_collection


class ChromaService:
    def __init__(self):
        self.collection = get_documents_collection(get_chroma())
        self.lock_path = str(Path(settings.CHROMA_PATH).parent / "chroma.lock")

    async def upsert_chunks(
        self,
        user_id: str,
        doc_id: str,
        filename: str,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        if not chunks:
            return
        await asyncio.to_thread(
            self._upsert_chunks_sync, user_id, doc_id, filename, chunks, embeddings
        )

    def _upsert_chunks_sync(
        self,
        user_id: str,
        doc_id: str,
        filename: str,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        with FileLock(self.lock_path):
            self.collection.upsert(
                ids=[f"{doc_id}__chunk_{c['chunk_index']}" for c in chunks],
                embeddings=embeddings,
                documents=[c["text"] for c in chunks],
                metadatas=[
                    {
                        "user_id": user_id,
                        "doc_id": doc_id,
                        "filename": filename,
                        "page_num": c["page_num"],
                        "chunk_index": c["chunk_index"],
                    }
                    for c in chunks
                ],
            )

    async def query_chunks(
        self,
        user_id: str,
        query_embedding: list[float],
        doc_ids: list[str] | None = None,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            self._query_chunks_sync, user_id, query_embedding, doc_ids, n_results
        )

    def _query_chunks_sync(
        self,
        user_id: str,
        query_embedding: list[float],
        doc_ids: list[str] | None,
        n_results: int,
    ) -> list[dict[str, Any]]:
        where = _where_for(user_id, doc_ids)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        return [
            {"text": documents[i], "metadata": metadatas[i], "distance": distances[i]}
            for i in range(len(documents))
        ]

    async def get_document_chunks(self, user_id: str, doc_ids: list[str]) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_document_chunks_sync, user_id, doc_ids)

    def _get_document_chunks_sync(self, user_id: str, doc_ids: list[str]) -> list[dict[str, Any]]:
        results = self.collection.get(
            where=_where_for(user_id, doc_ids),
            include=["documents", "metadatas"],
        )
        items = [
            {"text": doc, "metadata": meta}
            for doc, meta in zip(results.get("documents", []), results.get("metadatas", []), strict=False)
        ]
        return sorted(items, key=lambda item: (item["metadata"].get("page_num", 0), item["metadata"].get("chunk_index", 0)))

    async def delete_doc_chunks(self, user_id: str, doc_id: str) -> None:
        await asyncio.to_thread(self._delete_doc_chunks_sync, user_id, doc_id)

    def _delete_doc_chunks_sync(self, user_id: str, doc_id: str) -> None:
        with FileLock(self.lock_path):
            self.collection.delete(
                where={"$and": [{"user_id": {"$eq": user_id}}, {"doc_id": {"$eq": doc_id}}]}
            )


def _where_for(user_id: str, doc_ids: list[str] | None) -> dict[str, Any]:
    where: dict[str, Any] = {"user_id": {"$eq": user_id}}
    if doc_ids:
        if len(doc_ids) == 1:
            where = {"$and": [{"user_id": {"$eq": user_id}}, {"doc_id": {"$eq": doc_ids[0]}}]}
        else:
            where = {"$and": [{"user_id": {"$eq": user_id}}, {"doc_id": {"$in": doc_ids}}]}
    return where

