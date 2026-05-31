import os
import uuid
import shutil

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.config import settings
from backend.embeddings import get_embeddings_model


class VectorStore:
    def __init__(self, persist_directory: str = None):
        if persist_directory is None:
            persist_directory = settings.chroma_db_path
        self.persist_directory = persist_directory
        self._embeddings = get_embeddings_model()
        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )

    def index_documents(self, chunks: list[dict]):
        if not chunks:
            return

        if self._collection.count() > 0:
            self._client.delete_collection("documents")
            self._collection = self._client.create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"},
            )

        texts = [c["content"] for c in chunks]
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [
            {"document": c["document"], "chunk_index": c["chunk_index"]}
            for c in chunks
        ]

        embeddings = self._embeddings.encode(texts)

        batch_size = 100
        for i in range(0, len(texts), batch_size):
            end = i + batch_size
            self._collection.add(
                ids=ids[i:end],
                documents=texts[i:end],
                embeddings=embeddings[i:end],
                metadatas=metadatas[i:end],
            )

    def search(self, query: str, k: int = None) -> list[dict]:
        if k is None:
            k = settings.top_k
        query_embedding = self._embeddings.encode_query(query)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
        )

        documents = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                score = 1 - results["distances"][0][i]
                if score < settings.similarity_threshold:
                    continue
                documents.append(
                    {
                        "document": results["metadatas"][0][i]["document"],
                        "content": results["documents"][0][i],
                        "score": score,
                    }
                )
        return documents

    def count(self) -> int:
        return self._collection.count()

    def clear(self):
        self._client.delete_collection("documents")
        self._collection = self._client.create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )
