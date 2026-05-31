#!/usr/bin/env python3
"""
Script para poblar la base de datos vectorial desde los documentos
en la carpeta docs/.

Uso:
    python scripts/ingest_docs.py

Requiere tener configurado .env con las variables necesarias.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ingestion import process_documents
from backend.vector_store import VectorStore


def main():
    print("Reading documents from docs/ ...")
    chunks = process_documents()
    print(f"  → {len(chunks)} chunks generated")

    print("Indexing into ChromaDB ...")
    store = VectorStore()
    store.index_documents(chunks)
    print(f"  → {store.count()} chunks indexed successfully")


if __name__ == "__main__":
    main()
