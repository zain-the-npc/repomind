"""
Rewrites vague user questions into retrieval-friendly queries before search.
Original question is still used for the final answer prompt (keeps citations honest);
only the REWRITTEN version is used for embedding + hybrid search.
"""

from embeddings import client
from config import LLM_MODEL

REWRITE_PROMPT = """Rewrite this question into a short, specific search query for finding
relevant code/docs in a repository. Expand vague questions ("what is this repo about")
into concrete terms (architecture, main entry point, core modules, README purpose).
Keep it to one line, no explanation, just the rewritten query.

Question: {question}
Rewritten query:"""


def rewrite_query(question: str) -> str:
    """Returns a retrieval-optimized version of the question. Falls back to original on error."""
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": REWRITE_PROMPT.format(question=question)}],
            max_tokens=60,
            temperature=0.3,
        )
        rewritten = resp.choices[0].message.content.strip()
        return rewritten if rewritten else question
    except Exception:
        return question  # never block the pipeline on rewrite failure


if __name__ == "__main__":
    tests = [
        "what is this repo about",
        "how does auth work",
        "raise_for_status",
    ]
    for q in tests:
        print(f"{q!r} -> {rewrite_query(q)!r}")