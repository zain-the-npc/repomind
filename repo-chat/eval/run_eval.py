"""
Compares hybrid search (BM25 + dense + RRF) vs vector-only (dense) search.
Scores: does the expected file appear in top-k results for each test query?
Run after indexing a repo. Set REPO_ID below or pass as arg.

Usage: py run_eval.py <repo_id>
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from embeddings import embed
from vector_store import client, COLLECTION, HYBRID_TOP_K
from qdrant_client import models

TEST_QUERIES_PATH = os.path.join(os.path.dirname(__file__), "test_queries.json")


def vector_only_search(repo_id: str, question_embedding: list[float], top_k: int) -> list[dict]:
    """Dense-only search, no BM25, no fusion — for comparison baseline."""
    repo_filter = models.Filter(
        must=[models.FieldCondition(key="repo_id", match=models.MatchValue(value=repo_id))]
    )
    result = client.query_points(
        collection_name=COLLECTION,
        query=question_embedding,
        using="dense",
        query_filter=repo_filter,
        limit=top_k,
    )
    return [point.payload for point in result.points]


def hybrid_search_eval(repo_id: str, question_text: str, question_embedding: list[float], top_k: int) -> list[dict]:
    from vector_store import hybrid_search
    return hybrid_search(repo_id, question_text, question_embedding, top_k)


def hit(results: list[dict], expected_file: str) -> bool:
    return any(r["file_path"] == expected_file for r in results)


def run(repo_id: str, top_k: int = 5):
    with open(TEST_QUERIES_PATH) as f:
        queries = json.load(f)

    hybrid_hits = 0
    vector_hits = 0

    print(f"Running {len(queries)} queries, top_k={top_k}\n")

    for q in queries:
        question = q["question"]
        expected = q["expected_file"]
        q_embedding = embed(question)

        hybrid_results = hybrid_search_eval(repo_id, question, q_embedding, top_k)
        vector_results = vector_only_search(repo_id, q_embedding, top_k)

        h_hit = hit(hybrid_results, expected)
        v_hit = hit(vector_results, expected)

        hybrid_hits += h_hit
        vector_hits += v_hit

        status = lambda b: "HIT " if b else "MISS"
        print(f"[{status(h_hit)}|{status(v_hit)}] {question[:60]}")
        print(f"         expected: {expected}")

    n = len(queries)
    print(f"\n--- Results (top_{top_k}) ---")
    print(f"Hybrid search:     {hybrid_hits}/{n} ({100*hybrid_hits/n:.0f}%)")
    print(f"Vector-only search: {vector_hits}/{n} ({100*vector_hits/n:.0f}%)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py run_eval.py <repo_id>")
        sys.exit(1)
    run(sys.argv[1])