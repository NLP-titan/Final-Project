from app.rag.chunker import chunk_markdown


SAMPLE = """---
title: Sample
category: coverage
---

# Top

Some intro paragraph.

## Subsection A

Content for A.

## Subsection B

Content for B.
"""


def test_chunk_markdown_preserves_metadata_and_splits_by_heading():
    chunks = chunk_markdown(SAMPLE, base_metadata={"source_file": "sample.md"})

    assert len(chunks) >= 3
    assert all(c.metadata["source_file"] == "sample.md" for c in chunks)
    assert all(c.metadata.get("category") == "coverage" for c in chunks)

    sections = [c.metadata["section"] for c in chunks]
    assert any("Subsection A" in s for s in sections)
    assert any("Subsection B" in s for s in sections)


def test_chunk_markdown_no_headings_falls_back_to_paragraphs():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_markdown(text)
    assert len(chunks) == 1  # all paragraphs fit under SOFT_CHAR_CAP
    assert "First paragraph" in chunks[0].text
    assert "Third paragraph" in chunks[0].text
