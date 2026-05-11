# Offline RAG — Local Document Q&A

A fully offline Retrieval-Augmented Generation (RAG) system for querying technical documentation using local LLMs. No data ever leaves your machine.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      YOUR MACHINE                        │
│                                                          │
│  docs/*.md  ──►  LlamaIndex  ──►  BGE Embeddings         │
│                      │              (local cache)        │
│                 .rag_index/                              │
│              (vector index on disk)                      │
│                      │                                   │
│               Ollama  :11434                             │
│               └── llama3 / mistral / gemma3              │
│                      │                                   │
│               Answer in terminal                         │
└──────────────────────────────────────────────────────────┘
              ← zero external traffic at runtime →
```

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| Ollama | latest |
| RAM | 8 GB minimum |

---

## Installation

### 1. Install Ollama

```bash
# Linux / macOS
curl -fsSL https://ollama.com/install.sh | sh

# Windows: download the installer from https://ollama.com/download
```

> **Air-gap environments:** download the installer and model on a machine with internet access, then transfer via physical media.

### 2. Pull an LLM model

```bash
ollama pull llama3       # recommended — ~4.7 GB
ollama pull mistral      # lighter alternative — ~4.1 GB
ollama pull gemma3       # high quality — ~5 GB
ollama pull command-r    # RAG-optimized — ~8 GB
```

> **Air-gap transfer:** use `ollama save` / `ollama load` to export and import models as files.

### 3. Clone the repository

```bash
git clone <repo-url>
cd <repo-folder>
```

### 4. Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

pip install -r requirements_offline.txt
```

> On the first run, the BGE embedding model (~440 MB) is downloaded automatically.  
> For full air-gap setups, pre-download it:
> ```python
> from sentence_transformers import SentenceTransformer
> SentenceTransformer("BAAI/bge-base-en-v1.5")
> ```
> Then copy `~/.cache/huggingface/` to the target machine.

---

## Adding Documents

Place Markdown files inside `docs/`. Subdirectories are supported.

```
docs/
├── architecture.md
├── api_reference.md
├── deployment.md
└── subsystems/
    ├── networking.md
    └── storage.md
```

The system indexes all `.md` files on startup. Delete `.rag_index/` and restart to force a full reindex after adding or updating documents.

---

## Running

### 1. Start Ollama (keep it running in the background)

```bash
ollama serve
```

### 2. Start the RAG system

```bash
python rag_vsnt_offline.py
```

You will see a prompt where you can type natural language questions about your documents. Type `exit` or `quit` to stop.

### 3. (Optional) Manage the index

```bash
python manage_index.py --help
```

---

## Switching the LLM

Edit the model name in `rag_vsnt_offline.py`:

```python
OLLAMA_MODEL = "llama3"   # change to "mistral", "gemma3", etc.
```

Then delete the index and restart:

```bash
rm -rf .rag_index/
python rag_vsnt_offline.py
```

---

## Stack

| Component | Library / Tool | Purpose |
|-----------|---------------|---------|
| Orchestration | LlamaIndex | Document loading, chunking, retrieval |
| Embeddings | BAAI/bge-base-en-v1.5 | Text vectorization (runs locally) |
| Vector store | LlamaIndex SimpleVectorStore | Persistent index on disk |
| LLM | Ollama | Local inference server |
| Interface | Python CLI | Interactive Q&A loop |

---

## Hardware Requirements

| Profile | RAM | GPU | Suggested model |
|---------|-----|-----|-----------------|
| Minimum | 8 GB | None | mistral (4-bit) |
| Recommended | 16 GB | 6 GB VRAM | llama3 |
| Ideal | 32 GB | 12 GB VRAM | command-r |

---

## Security

Everything runs locally. No API keys, no cloud services, no telemetry.

| Component | Internet traffic | Notes |
|-----------|-----------------|-------|
| LlamaIndex | None | Local library |
| Ollama (LLM) | None | Binds to `localhost:11434` |
| BGE Embeddings | None | Local cache after first download |
| Vector index | None | Stored in `.rag_index/` on disk |
| `docs/` folder | None | Never leaves the machine |

**Additional recommendations for sensitive environments:**

- Run on a machine with an outbound firewall rule blocking all external traffic
- Encrypt the disk (LUKS on Linux, BitLocker on Windows) to protect `docs/` and `.rag_index/`
- Restrict physical access to the machine
- Enable query logging in `manage_index.py` for audit trails
