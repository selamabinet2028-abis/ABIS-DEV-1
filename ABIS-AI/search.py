"""ABIS-AI search: semantic retrieval over the ingested codebase/docs.
Usage: python search.py "how does dedup work" -k 5
"""
import argparse
import chromadb, ollama

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--collection", default="abis")
    args = ap.parse_args()
    col = chromadb.PersistentClient(path="./chroma").get_or_create_collection(args.collection)
    emb = ollama.embeddings(model="nomic-embed-text", prompt=args.query)["embedding"]
    res = col.query(query_embeddings=[emb], n_results=args.k)
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        print(f"\n=== {meta['path']} (chunk {meta['chunk']}, dist {dist:.3f}) ===")
        print(doc[:600])

if __name__ == "__main__":
    main()
