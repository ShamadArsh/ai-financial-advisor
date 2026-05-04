import os, glob
from sentence_transformers import SentenceTransformer
from chromadb import PersistentClient

EMB_MODEL = "all-MiniLM-L6-v2"
CORPUS_DIR = "./corpus_theory"
CHROMA_DIR = "./chroma_rag"

os.makedirs(CORPUS_DIR, exist_ok=True)

embedder = SentenceTransformer(EMB_MODEL)

# NEW Chroma client API
client = PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection("finance_corpus")

def chunk_text(text, size=200, overlap=30):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+size])
        chunks.append(chunk)
        i += size - overlap
    return chunks

def index_corpus():
    files = glob.glob(os.path.join(CORPUS_DIR, "*.txt"))
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
        embeddings=embeddings.tolist()
    )

    print("Indexed:", len(docs))


def retrieve(query, top_k=5):
    emb = embedder.encode([query])[0]
    res = collection.query(query_embeddings=[emb], n_results=top_k)

    hits = []
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]

    for doc, meta, dist in zip(docs, metas, dists):
        hits.append({
            "text": doc,
            "metadata": meta,
            "distance": dist
        })
    return hits


if __name__ == "__main__":
    # sample corpus if empty
    if not any(os.scandir(CORPUS_DIR)):
        with open(os.path.join(CORPUS_DIR, "sample.txt"), "w") as f:
            f.write("P/E ratio describes valuation. Cyclical industries include steel.")
    index_corpus()
    print(retrieve("steel valuation"))
