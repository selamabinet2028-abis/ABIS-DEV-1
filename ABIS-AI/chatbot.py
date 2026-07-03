"""ABIS-AI chatbot: RAG chat over the ABIS knowledge base via local Ollama model.
Usage: python chatbot.py            (model default qwen2.5-coder; `ollama pull` it first)
"""
import chromadb, ollama

MODEL = "qwen2.5-coder"
SYSTEM = ("You are the ABIS engineering assistant. Answer using the provided "
          "repository context. If context is insufficient, say so and point to "
          "the relevant .ai/ document.")

col = chromadb.PersistentClient(path="./chroma").get_or_create_collection("abis")

def retrieve(q: str, k: int = 6) -> str:
    emb = ollama.embeddings(model="nomic-embed-text", prompt=q)["embedding"]
    res = col.query(query_embeddings=[emb], n_results=k)
    return "\n\n".join(f"[{m['path']}]\n{d}" for d, m in
                       zip(res["documents"][0], res["metadatas"][0]))

def main():
    history = [{"role": "system", "content": SYSTEM}]
    print("ABIS-AI chat. Ctrl+C to exit.")
    while True:
        q = input("\nyou> ").strip()
        if not q:
            continue
        ctx = retrieve(q)
        history.append({"role": "user", "content": f"Context:\n{ctx}\n\nQuestion: {q}"})
        out = ollama.chat(model=MODEL, messages=history)["message"]["content"]
        history.append({"role": "assistant", "content": out})
        print(f"\nabis-ai> {out}")

if __name__ == "__main__":
    main()
