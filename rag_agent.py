import os
import glob
import logging

logger = logging.getLogger("rag_agent")

EMB_MODEL = "all-MiniLM-L6-v2"
CORPUS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus_theory")
CHROMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_rag")

# Lazy-loaded singletons (not loaded at import time)
_embedder = None
_collection = None


def get_embedder():
    """Lazily load the SentenceTransformer model (singleton)."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading SentenceTransformer '%s' ...", EMB_MODEL)
        _embedder = SentenceTransformer(EMB_MODEL)
    return _embedder


def get_collection():
    """Lazily init ChromaDB client and collection (singleton)."""
    global _collection
    if _collection is None:
        from chromadb import PersistentClient
        os.makedirs(CHROMA_DIR, exist_ok=True)
        client = PersistentClient(path=CHROMA_DIR)
        _collection = client.get_or_create_collection("finance_corpus")
    return _collection


def chunk_text(text, size=200, overlap=30):
    """Split text into overlapping word chunks."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + size])
        chunks.append(chunk)
        i += size - overlap
    return chunks


def index_corpus():
    """Read all .txt files from CORPUS_DIR, chunk them, and add to ChromaDB."""
    os.makedirs(CORPUS_DIR, exist_ok=True)
    files = glob.glob(os.path.join(CORPUS_DIR, "*.txt"))

    if not files:
        # Seed a sample corpus if none exists
        sample_path = os.path.join(CORPUS_DIR, "sample.txt")
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write(
                "P/E ratio describes valuation. "
                "Cyclical industries include steel, oil, and automotive. "
                "Value investing focuses on intrinsic value vs market price. "
                "Growth investing focuses on future earnings potential. "
                "Diversification reduces portfolio risk. "
                "The Sharpe ratio measures risk-adjusted returns. "
                "Dollar-cost averaging reduces timing risk. "
            )
        files = [sample_path]

    embedder = get_embedder()
    collection = get_collection()

    ids = []
    docs = []
    metas = []

    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            text = fh.read()
        chunks = chunk_text(text)
        for i, ch in enumerate(chunks):
            ids.append(f"{os.path.basename(f)}_{i}")
            docs.append(ch)
            metas.append({"source": os.path.basename(f), "chunk": i})

    embeddings = embedder.encode(docs)

    collection.add(
        ids=ids,
        documents=docs,
        metadatas=metas,
        embeddings=embeddings.tolist(),
    )

    logger.info("Indexed %d chunks from %d files", len(docs), len(files))
    return len(docs)


def retrieve(query, top_k=5):
    """Retrieve top-k relevant chunks for a query."""
    embedder = get_embedder()
    collection = get_collection()

    emb = embedder.encode([query])[0]
    res = collection.query(query_embeddings=[emb], n_results=top_k)

    hits = []
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]

    for doc, meta, dist in zip(docs, metas, dists):
        hits.append({"text": doc, "metadata": meta, "distance": dist})

    return hits


def ensure_indexed():
    """Index corpus if it hasn't been indexed yet (check if collection is empty)."""
    collection = get_collection()
    if collection.count() == 0:
        logger.info("ChromaDB collection empty — indexing corpus ...")
        index_corpus()


if __name__ == "__main__":
    ensure_indexed()
    print(retrieve("steel valuation"))
