"""
Splits code files into chunks by function/class using Python's ast module.
Python only for now. Non-Python code files fall back to whole-file chunk
(extend with tree-sitter later for multi-language support).
"""

import ast


def _get_source_segment(source_lines: list[str], start: int, end: int) -> str:
    # ast line numbers are 1-indexed
    return "\n".join(source_lines[start - 1:end])


def chunk_python_file(path: str, content: str) -> list[dict]:
    """
    Returns list of dicts: {file_path, function_name, start_line, end_line,
    chunk_type, text}
    chunk_type: "function" | "class" | "module" (leftover top-level code)
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return _fallback_chunk(path, content)

    source_lines = content.splitlines()
    chunks = []
    covered_lines = set()

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", start)
            text = _get_source_segment(source_lines, start, end)
            chunk_type = "class" if isinstance(node, ast.ClassDef) else "function"

            chunks.append({
                "file_path": path,
                "function_name": node.name,
                "start_line": start,
                "end_line": end,
                "chunk_type": chunk_type,
                "text": text,
            })
            covered_lines.update(range(start, end + 1))

    # leftover top-level code (imports, constants, script logic) as one module chunk
    leftover_lines = [
        line for i, line in enumerate(source_lines, start=1)
        if i not in covered_lines and line.strip()
    ]
    if leftover_lines:
        chunks.append({
            "file_path": path,
            "function_name": None,
            "start_line": 1,
            "end_line": len(source_lines),
            "chunk_type": "module",
            "text": "\n".join(leftover_lines),
        })

    return chunks


def _fallback_chunk(path: str, content: str) -> list[dict]:
    # used for syntax errors or non-Python code files
    return [{
        "file_path": path,
        "function_name": None,
        "start_line": 1,
        "end_line": len(content.splitlines()),
        "chunk_type": "module",
        "text": content,
    }]


def chunk_code_file(path: str, content: str) -> list[dict]:
    """Entry point. Routes by extension. Python -> AST. Others -> fallback."""
    if path.endswith(".py"):
        return chunk_python_file(path, content)
    return _fallback_chunk(path, content)


if __name__ == "__main__":
    # quick manual test on this file itself
    with open(__file__, "r") as f:
        src = f.read()
    result = chunk_code_file(__file__, src)
    print(f"Got {len(result)} chunks")
    for c in result:
        print(c["chunk_type"], c["function_name"], c["start_line"], "-", c["end_line"])