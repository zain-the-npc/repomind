"""
Qdrant client wrapper. Collection has two vectors per point:
- "dense": OpenAI embedding (semantic)
- "sparse": BM25 sparse vector via fastembed (lexical)
Query API fuses both with RRF natively — no manual fusion logic.
"""

from qdrant_client import QdrantClient, models
from fastembed import SparseTextEmbedding

from config import QDRANT_URL, QDRANT_API_KEY, EMBEDDING_DIM, HYBRID_TOP_K

COLLECTION = "codebase_rag"

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)
_sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")


def ensure_collection():
    """Creates the collection if it doesn't exist. Call once before upserting."""
    if client.collection_exists(COLLECTION):
        return
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={
            "dense": models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(),
        },
    )
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="repo_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )


def upsert(repo_id: str, chunks: list[dict], embeddings: list[list[float]]):
    """
    chunks: list of dicts from code_chunker/doc_chunker (file_path, function_name,
            start_line, end_line, chunk_type, text)
    embeddings: dense vectors, same order/length as chunks
    """
    ensure_collection()
    sparse_vecs = list(_sparse_model.embed([c["text"] for c in chunks]))

    points = []
    for i, (chunk, dense_vec, sparse_vec) in enumerate(zip(chunks, embeddings, sparse_vecs)):
        point_id_seed = f"{repo_id}:{chunk['file_path']}:{chunk['start_line']}:{i}"
        points.append(models.PointStruct(
            id=abs(hash(point_id_seed)) % (10 ** 12),
            vector={
                "dense": dense_vec,
                "sparse": models.SparseVector(
                    indices=sparse_vec.indices.tolist(),
                    values=sparse_vec.values.tolist(),
                ),
            },
            payload={
                "repo_id": repo_id,
                "file_path": chunk["file_path"],
                "function_name": chunk["function_name"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "chunk_type": chunk["chunk_type"],
                "text": chunk["text"],
            },
        ))

    for i in range(0, len(points), 100):
        client.upsert(collection_name=COLLECTION, points=points[i:i + 100])


def hybrid_search(repo_id: str, question_text: str, question_embedding: list[float],
                   top_k: int = HYBRID_TOP_K) -> list[dict]:
    """
    Runs BM25 (sparse) + dense search in parallel, fused with RRF, filtered to repo_id.
    Returns list of payload dicts (file_path, function_name, start_line, end_line, text, ...).
    """
    sparse_vec = list(_sparse_model.embed([question_text]))[0]
    repo_filter = models.Filter(
        must=[models.FieldCondition(key="repo_id", match=models.MatchValue(value=repo_id))]
    )

    result = client.query_points(
        collection_name=COLLECTION,
        prefetch=[
            models.Prefetch(
                query=question_embedding,
                using="dense",
                filter=repo_filter,
                limit=top_k,
            ),
            models.Prefetch(
                query=models.SparseVector(
                    indices=sparse_vec.indices.tolist(),
                    values=sparse_vec.values.tolist(),
                ),
                using="sparse",
                filter=repo_filter,
                limit=top_k,
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=top_k,
    )

    return [point.payload for point in result.points]


if __name__ == "__main__":
    ensure_collection()
    print(f"Collection '{COLLECTION}' ready.")