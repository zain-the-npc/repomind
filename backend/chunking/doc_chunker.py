"""
Splits doc files (.md, .rst, .txt) into chunks by heading.
Falls back to paragraph splitting if no headings, or size-based split
if a section is too big (>500 tokens, approx by word count).
"""

import re

MAX_WORDS = 500  # rough proxy for ~500 tokens
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)", re.MULTILINE)


def _split_by_heading(content: str) -> list[dict]:
    """Returns list of {heading, text} using markdown '#' headings."""
    matches = list(HEADING_RE.finditer(content))
    if not matches:
        return [{"heading": None, "text": content}]

    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        heading = m.group(2).strip()
        text = content[start:end].strip()
        sections.append({"heading": heading, "text": text})
    return sections


def _split_oversized(text: str, max_words: int = MAX_WORDS) -> list[str]:
    """If a section is too long, split by paragraph, greedily packing."""
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = []
    current_words = 0

    for p in paragraphs:
        p_words = len(p.split())
        if current_words + p_words > max_words and current:
            chunks.append("\n\n".join(current))
            current = []
            current_words = 0
        current.append(p)
        current_words += p_words

    if current:
        chunks.append("\n\n".join(current))

    return chunks if chunks else [text]


def chunk_doc_file(path: str, content: str) -> list[dict]:
    """
    Returns list of dicts: {file_path, function_name, start_line, end_line,
    chunk_type, text}
    function_name is reused as "heading" for doc chunks (keeps schema uniform
    with code_chunker output).
    Line numbers are approximate (based on char offset -> line count).
    """
    sections = _split_by_heading(content)
    chunks = []

    for section in sections:
        pieces = _split_oversized(section["text"])
        for piece in pieces:
            start_line = content[:content.find(piece)].count("\n") + 1 if piece in content else 1
            end_line = start_line + piece.count("\n")
            chunks.append({
                "file_path": path,
                "function_name": section["heading"],
                "start_line": start_line,
                "end_line": end_line,
                "chunk_type": "doc",
                "text": piece,
            })

    return chunks


if __name__ == "__main__":
    sample = """# Title

Intro paragraph here.

## Section One

Some content in section one.

## Section Two

More content here.
"""
    result = chunk_doc_file("sample.md", sample)
    print(f"Got {len(result)} chunks")
    for c in result:
        print(c["chunk_type"], c["function_name"], c["start_line"], "-", c["end_line"])