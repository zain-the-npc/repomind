from openai import OpenAI
from config import OPENAI_API_KEY, EMBEDDING_MODEL
 
client = OpenAI(api_key=OPENAI_API_KEY)
 
 
def embed(text: str) -> list[float]:
    """Returns embedding vector for a single text string."""
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return resp.data[0].embedding
 
MAX_CHARS = 24000  # ~6000-8000 tokens, safe under the 8192 limit


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Returns embedding vectors for a list of texts in one API call (cheaper, faster)."""
    safe_texts = [t[:MAX_CHARS] for t in texts]
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=safe_texts)
    return [d.embedding for d in resp.data]
 
if __name__ == "__main__":
    vec = embed("hello world")
    print(f"Single embed dim: {len(vec)}")
 
    vecs = embed_batch(["hello", "world", "test"])
    print(f"Batch embed count: {len(vecs)}, dim: {len(vecs[0])}")
 