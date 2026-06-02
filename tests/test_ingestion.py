from backend.ingestion import clean_text, chunk_text


def test_clean_text_removes_bom():
    assert clean_text("\ufeffHola") == "Hola"


def test_clean_text_normalizes_spaces():
    assert clean_text("Hola    mundo") == "Hola mundo"


def test_clean_text_collapses_newlines():
    text = "a\n\n\n\nb"
    assert clean_text(text) == "a\n\nb"


def test_clean_text_strips_whitespace():
    assert clean_text("  hola  ") == "hola"


def test_chunk_text_empty():
    assert chunk_text("") == []


def test_chunk_text_small():
    chunks = chunk_text("Hola mundo", chunk_size=500, overlap=50)
    assert len(chunks) == 1
    assert "Hola mundo" in chunks[0]


def test_chunk_text_splits():
    text = "a" * 300 + "\n\n" + "b" * 300
    chunks = chunk_text(text, chunk_size=200, overlap=50)
    assert len(chunks) >= 2


def test_chunk_text_with_overlap():
    text = ("A" * 100 + "\n\n") * 10
    chunks = chunk_text(text, chunk_size=300, overlap=50)
    assert len(chunks) >= 1
