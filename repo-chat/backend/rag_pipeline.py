"""
Core RAG pipeline. Two functions:
  index_repo(repo_url) -> repo_id
  query(repo_id, question) -> {answer, sources}
No API/routing logic here — that's main.py's job.
"""

import hashlib

import github_fetch
import vector_store
import rerank as reranker
import query_rewrite
from embeddings import embed, embed_batch, client
from chunking.code_chunker import chunk_code_file
from chunking.doc_chunker import chunk_doc_file
from config import LLM_MODEL, RERANK_TOP_K


def _repo_id_from_url(repo_url: str) -> str:
    return hashlib.sha256(repo_url.encode()).hexdigest()[:16]


def index_repo(repo_url: str) -> str:
    """Fetches, chunks, embeds, and upserts a repo. Returns repo_id."""
    repo_id = _repo_id_from_url(repo_url)
    files = github_fetch.get_files(repo_url)

    all_chunks = []
    for f in files:
        if f["type"] == "code":
            chunks = chunk_code_file(f["path"], f["content"])
        else:
            chunks = chunk_doc_file(f["path"], f["content"])
        all_chunks.extend(chunks)

    if not all_chunks:
        return repo_id

    texts = [c["text"] for c in all_chunks]
    vectors = embed_batch(texts)

    vector_store.upsert(repo_id, all_chunks, vectors)
    return repo_id


def _build_prompt(question: str, chunks: list[dict]) -> str:
    context_blocks = []
    for c in chunks:
        loc = f"{c['file_path']}"
        if c.get("function_name"):
            loc += f" :: {c['function_name']}"
        loc += f" (lines {c['start_line']}-{c['end_line']})"
        context_blocks.append(f"[{loc}]\n{c['text']}")

    context = "\n\n---\n\n".join(context_blocks)

    return (
        "Answer only using the context below. Cite file path and function name "
        "for every claim. If the context doesn't contain the answer, say so.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}"
    )


def query(repo_id: str, question: str) -> dict:
    """Embeds question, hybrid searches, reranks, generates answer with citations."""
    search_query = query_rewrite.rewrite_query(question)
    question_embedding = embed(search_query)

    candidates = vector_store.hybrid_search(repo_id, search_query, question_embedding)
    top_chunks = reranker.rerank(question, candidates, top_k=RERANK_TOP_K)

    if not top_chunks:
        return {
            "answer": "No relevant context found in this repo for that question.",
            "sources": [],
        }

    prompt = _build_prompt(question, top_chunks)

    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = resp.choices[0].message.content

    sources = [
        {
            "file": c["file_path"],
            "function": c.get("function_name"),
            "lines": f"{c['start_line']}-{c['end_line']}",
        }
        for c in top_chunks
    ]

    return {"answer": answer, "sources": sources}


if __name__ == "__main__":
    # quick manual test — small repo, real API calls (costs a few cents)
    test_url = "https://github.com/psf/requests"
    print("Indexing...")
    rid = index_repo(test_url)
    print(f"repo_id: {rid}")

    print("Querying...")
    result = query(rid, "How does this library send an HTTP GET request?")
    print("\nANSWER:\n", result["answer"])
    print("\nSOURCES:")
    for s in result["sources"]:
        print(" -", s)