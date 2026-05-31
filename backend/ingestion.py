import os
import re
import json
from pathlib import Path

from backend.config import settings


def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_json_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return json.dumps(data, ensure_ascii=False, indent=2)


def read_markdown_file(path: str) -> str:
    return read_text_file(path)


def read_pdf_file(path: str) -> str:
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber is required to read PDF files")
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def clean_text(text: str) -> str:
    text = re.sub(r"\ufeff", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[^\S\n]+", " ", text)
    text = text.strip()
    return text


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list[str]:
    if chunk_size is None:
        chunk_size = settings.chunk_size
    if overlap is None:
        overlap = settings.chunk_overlap

    if not text:
        return []

    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    if not paragraphs:
        return []

    chunks = []
    current_chunk = []
    current_length = 0

    for para in paragraphs:
        para_len = len(para)

        if current_length + para_len > chunk_size and current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(chunk_text)

            overlap_texts = []
            overlap_len = 0
            for p in reversed(current_chunk):
                if not overlap_texts or overlap_len + len(p) <= overlap:
                    overlap_texts.insert(0, p)
                    overlap_len += len(p)
                    if overlap_len >= overlap:
                        break
                else:
                    break
            current_chunk = overlap_texts
            current_length = overlap_len

        current_chunk.append(para)
        current_length += para_len

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def read_file(path: str) -> str:
    ext = Path(path).suffix.lower()
    readers = {
        ".txt": read_text_file,
        ".md": read_markdown_file,
        ".json": read_json_file,
        ".pdf": read_pdf_file,
    }
    reader = readers.get(ext)
    if reader is None:
        raise ValueError(f"Unsupported file format: {ext}")
    return reader(path)


def process_documents(docs_dir: str = None) -> list[dict]:
    if docs_dir is None:
        docs_dir = settings.docs_dir
    supported = {".txt", ".md", ".json", ".pdf"}
    docs_dir_path = Path(docs_dir)
    if not docs_dir_path.exists():
        raise FileNotFoundError(f"Documentation directory not found: {docs_dir}")

    all_chunks = []
    for file_path in sorted(docs_dir_path.iterdir()):
        if file_path.suffix.lower() not in supported:
            continue
        try:
            raw_text = read_file(str(file_path))
            cleaned = clean_text(raw_text)
            chunks = chunk_text(cleaned)
            for i, chunk in enumerate(chunks):
                all_chunks.append(
                    {
                        "document": file_path.name,
                        "chunk_index": i,
                        "content": chunk,
                    }
                )
        except Exception as e:
            print(f"Warning: could not process {file_path.name}: {e}")

    return all_chunks
