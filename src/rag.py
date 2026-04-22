from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss, numpy as np, pickle

MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 80MB, fast, English-friendly
ROOT = Path(__file__).parent.parent
KNOWLEDGE_DIR = ROOT / "knowledge"
INDEX_PATH = KNOWLEDGE_DIR / "faiss.index"
DOCS_PATH = KNOWLEDGE_DIR / "docs.pkl"

def build_index():
    docs = [(p.stem, p.read_text()) for p in KNOWLEDGE_DIR.glob("*.md")]
    # print(f"Found {len(docs)} documents: {[d[0] for d in docs]}") 
    encoder = SentenceTransformer(MODEL)
    embs = encoder.encode([d[1] for d in docs], normalize_embeddings=True)
    index = faiss.IndexFlatIP(embs.shape[1])
    index.add(np.array(embs, dtype="float32"))
    faiss.write_index(index, str(INDEX_PATH))
    with open(DOCS_PATH, "wb") as f:
        pickle.dump(docs, f)

def retrieve(query: str, k: int = 3):
    encoder = SentenceTransformer(MODEL)
    index = faiss.read_index(str(INDEX_PATH))
    with open(DOCS_PATH, "rb") as f:
        docs = pickle.load(f)
    q = encoder.encode([query], normalize_embeddings=True).astype("float32")
    scores, idxs = index.search(q, k)
    return [{"title": docs[i][0], "content": docs[i][1], "score": float(scores[0][j])}
            for j, i in enumerate(idxs[0])]

def main():
    build_index()


if __name__ == "__main__":
    main()
