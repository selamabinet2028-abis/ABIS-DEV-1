# ABIS-AI — Local RAG Knowledge Assistant

Local "company knowledge base" over the ABIS repo + .ai/ docs + session history.

Stack: Ollama (`nomic-embed-text` embeddings + a local coder model) + ChromaDB.

```powershell
cd ABIS-AI
python -m venv venv; .\venv\Scripts\activate
pip install -r requirements.txt
ollama pull nomic-embed-text; ollama pull qwen2.5-coder
python ingest.py --repo ..     # (re)index the repository
python search.py "where is the matching engine interface" 
python chatbot.py              # interactive RAG chat
```
Re-run `ingest.py` after significant code changes (or wire watchdog later).
