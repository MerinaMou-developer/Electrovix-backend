# base/ai/embedding.py

from sentence_transformers import SentenceTransformer

# loads only once
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

def embed_text(text: str):
    return EMBED_MODEL.encode([text], normalize_embeddings=True)[0].tolist()
