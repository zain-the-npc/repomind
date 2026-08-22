"""
Splits code files into chunks by function/class.
Python -> ast module (existing, unchanged behavior).
JS/TS/Go/Java/C/C++/Rust -> tree-sitter (real AST-based function/class extraction).
Anything else -> whole-file fallback.

Handles named declarations (function foo() {}, class Foo {}) AND common
assignment patterns (const foo = () => {}, module.exports = async () => {}),
which named-declaration-only matching misses in JS/TS codebases.
"""

import ast

from tree_sitter_languages import get_parser

TS_LANGUAGE_MAP = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
}

# named declarations: function/class has its own name built in
CHUNK_NODE_TYPES = {
    "javascript": {"function_declaration", "class_declaration", "method_definition"},
    "typescript": {"function_declaration", "class_declaration", "method_definition",
                   "interface_declaration"},
    "tsx": {"function_declaration", "class_declaration", "method_definition",
            "interface_declaration"},
    "go": {"function_declaration", "method_declaration", "type_declaration"},
    "java": {"method_declaration", "class_declaration", "interface_declaration"},
    "rust": {"function_item", "impl_item", "struct_item", "trait_item"},
    "cpp": {"function_definition", "class_specifier", "struct_specifier"},
    "c": {"function_definition", "struct_specifier"},
}

# function-value node types: a function with no name of its own — name comes
# from whatever it's assigned to (variable_declarator, assignment_expression, etc.)
FUNCTION_VALUE_TYPES = {"arrow_function", "function_expression", "function"}

# wrapper node types that carry the name for an anonymous function value
ASSIGNMENT_WRAPPER_TYPES = {"variable_declarator", "assignment_expression", "pair"}


def _get_source_segment(source_lines: list[str], start: int, end: int) -> str:
    return "\n".join(source_lines[start - 1:end])


def chunk_python_file(path: str, content: str) -> list[dict]:
    """AST-based Python chunker (unchanged from before)."""
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


def _node_name(node, source_bytes: bytes) -> str | None:
    """Best-effort extraction of a name from a tree-sitter node's identifier children."""
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "property_identifier",
                           "member_expression", "shorthand_property_identifier"):
            return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
    return None


def chunk_treesitter_file(path: str, content: str, language: str) -> list[dict]:
    """
    Walks the tree-sitter parse tree. Two chunk sources:
    1. Named declarations (function foo() {}, class Foo {}) — name is intrinsic.
    2. Function values assigned to a name (const foo = () => {}, module.exports = fn,
       obj = { key: () => {} }) — name comes from the enclosing assignment/pair node.
    Falls back to whole-file on parse failure.
    """
    try:
        parser = get_parser(language)
        source_bytes = content.encode("utf-8")
        tree = parser.parse(source_bytes)
    except Exception:
        return _fallback_chunk(path, content)

    named_types = CHUNK_NODE_TYPES.get(language, set())
    source_lines = content.splitlines()
    chunks = []
    covered_lines = set()

    def add_chunk(node, name, chunk_type):
        start = node.start_point[0] + 1
        end = node.end_point[0] + 1
        text = _get_source_segment(source_lines, start, end)
        chunks.append({
            "file_path": path,
            "function_name": name,
            "start_line": start,
            "end_line": end,
            "chunk_type": chunk_type,
            "text": text,
        })
        covered_lines.update(range(start, end + 1))

    def walk(node, parent=None):
        # case 1: named declaration
        if node.type in named_types:
            name = _node_name(node, source_bytes) or "anonymous"
            chunk_type = ("class" if any(k in node.type for k in ("class", "struct", "interface"))
                          else "function")
            add_chunk(node, name, chunk_type)
            return  # don't descend — keep the declaration whole

        # case 2: anonymous function value assigned to a name
        if node.type in FUNCTION_VALUE_TYPES and parent is not None and parent.type in ASSIGNMENT_WRAPPER_TYPES:
            # only function/function_expression can carry their own name; arrow functions never do
            own_name = _node_name(node, source_bytes) if node.type != "arrow_function" else None
            name = own_name or _node_name(parent, source_bytes) or "anonymous"
            add_chunk(parent, name, "function")
            return  # don't descend into the function body

        for child in node.children:
            walk(child, node)

    walk(tree.root_node)

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

    return chunks if chunks else _fallback_chunk(path, content)


def _fallback_chunk(path: str, content: str) -> list[dict]:
    return [{
        "file_path": path,
        "function_name": None,
        "start_line": 1,
        "end_line": len(content.splitlines()),
        "chunk_type": "module",
        "text": content,
    }]


def chunk_code_file(path: str, content: str) -> list[dict]:
    """Entry point. Routes by extension: Python -> ast, known langs -> tree-sitter, else -> fallback."""
    if path.endswith(".py"):
        return chunk_python_file(path, content)

    ext = "." + path.split(".")[-1] if "." in path else ""
    language = TS_LANGUAGE_MAP.get(ext)
    if language:
        return chunk_treesitter_file(path, content, language)

    return _fallback_chunk(path, content)


if __name__ == "__main__":
    js_sample = """function add(a, b) {
  return a + b;
}

class Calculator {
  multiply(a, b) {
    return a * b;
  }
}

const isOnline = async options => {
  return true;
};

module.exports = async function checkStatus() {
  return 200;
};

module.exports.ping = () => {
  return 'pong';
};
"""
    result = chunk_code_file("sample.js", js_sample)
    print(f"Got {len(result)} chunks")
    for c in result:
        print(c["chunk_type"], c["function_name"], c["start_line"], "-", c["end_line"])