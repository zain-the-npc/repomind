
from fastembed.rerank.cross_encoder import TextCrossEncoder
from config import RERANK_TOP_K
 
_model = TextCrossEncoder(model_name="BAAI/bge-reranker-base")
 
 
def rerank(question: str, results: list[dict], top_k: int = RERANK_TOP_K) -> list[dict]:
    """
    results: list of payload dicts from vector_store.hybrid_search
             (must have a "text" key)
    Returns top_k results, sorted by cross-encoder relevance score (best first).
    """
    if not results:
        return []
 
    texts = [r["text"] for r in results]
    scores = list(_model.rerank(question, texts))
 
    scored = list(zip(results, scores))
    scored.sort(key=lambda pair: pair[1], reverse=True)
 
    return [r for r, _ in scored[:top_k]]
 
 
if __name__ == "__main__":
    fake_results = [
        {"text": "def add(a, b): return a + b", "file_path": "math_utils.py"},
        {"text": "class UserModel: pass", "file_path": "models.py"},
        {"text": "def subtract(a, b): return a - b", "file_path": "math_utils.py"},
    ]
    top = rerank("how do I add two numbers", fake_results, top_k=2)
    print(f"Top {len(top)} results:")
    for r in top:
        print(r["file_path"], "-", r["text"])