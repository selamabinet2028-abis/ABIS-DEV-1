"""ABIS-AI ingest: chunk repo files + .ai docs -> embeddings -> ChromaDB.

Usage (Windows PowerShell):
  python ingest.py --repo ..\\ --collection abis
Requires Ollama running locally with: `ollama pull nomic-embed-text`
"""
import argparse, hashlib, pathlib
import chromadb, ollama

INCLUDE = {".py", ".ts", ".tsx", ".md", ".yml", ".yaml", ".json", ".toml", ".ps1"}
EXCLUDE_DIRS = {"node_modules", "venv", ".git", "dist", "build", "__pycache__", "media"}
CHUNK, OVERLAP = 1500, 200

def chunks(text: str):
    i = 0
    while i < len(text):
        yield text[i:i + CHUNK]
        i += CHUNK - OVERLAP

def embed(text: str):
    return ollama.embeddings(model="nomic-embed-text", prompt=text)["embedding"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="..")
    ap.add_argument("--collection", default="abis")
    args = ap.parse_args()
    client = chromadb.PersistentClient(path="./chroma")
    col = client.get_or_create_collection(args.collection)
    root = pathlib.Path(args.repo).resolve()
    n = 0
    for p in root.rglob("*"):
        if p.is_dir() or p.suffix.lower() not in INCLUDE:
            continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(p.relative_to(root))
        for j, ch in enumerate(chunks(text)):
            cid = hashlib.sha1(f"{rel}:{j}".encode()).hexdigest()
            col.upsert(ids=[cid], embeddings=[embed(ch)],
                       documents=[ch], metadatas=[{"path": rel, "chunk": j}])
            n += 1
    print(f"Ingested {n} chunks from {root} into '{args.collection}'.")

if __name__ == "__main__":
    main()
