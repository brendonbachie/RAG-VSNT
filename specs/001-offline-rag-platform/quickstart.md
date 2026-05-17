# Quickstart: Offline RAG Commercial Platform

Installation guide for Windows 10/11 and Ubuntu/Debian Linux.
**Total time**: ~25–30 minutes on a machine with internet access (for first-time setup).
After setup, the machine may be fully air-gapped.

---

## Prerequisites

| Requirement | Minimum | Recommended |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Disk space | 10 GB free | 20 GB free |
| GPU (optional) | — | 6 GB VRAM (speeds up LLM inference) |
| Python | 3.11+ | 3.11+ |
| Ollama | Latest | Latest |

---

## Step 1 — Install Ollama and download a model

### Linux / macOS
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3
```

### Windows
Download and run the installer from https://ollama.com/download, then open a terminal:
```bat
ollama pull llama3
```

> **Air-gap transfer**: use `ollama save <model> > model.tar` on a connected machine,
> transfer the file, then `ollama load < model.tar` on the target machine.

---

## Step 2 — Install the application

### Linux / macOS
```bash
git clone <repo-url> vsnt-rag
cd vsnt-rag
bash install.sh
```

### Windows
```bat
git clone <repo-url> vsnt-rag
cd vsnt-rag
install.bat
```

The installer script does the following:
1. Creates a Python virtual environment (`.venv/`)
2. Installs all dependencies from `requirements_offline.txt`
3. Creates the `data/` directory for the SQLite database
4. Verifies Ollama is reachable and the configured model is available

> **Air-gap pip install**: on a connected machine run
> `pip download -r requirements_offline.txt -d ./pip-packages`, transfer the folder,
> then on the target machine run `pip install --no-index --find-links=./pip-packages -r requirements_offline.txt`.

---

## Step 3 — Add your documents

Copy your PDF, DOCX, or Markdown files into the `docs/` folder:
```
docs/
├── manual_operacao.pdf
├── especificacoes_tecnicas.docx
└── protocolo_comunicacao.md
```

---

## Step 4 — Start the server

### Linux / macOS
```bash
source .venv/bin/activate
python app.py
```

### Windows
```bat
.venv\Scripts\activate
python app.py
```

You will see:
```
🔒 VSNT RAG — Web Platform  (v1.0)
   Server  : http://127.0.0.1:8000
   Database: data/vsnt_rag.db
   Docs    : docs/  (N files)
   LLM     : llama3 via Ollama
✅ Ollama OK
📂 Starting server...
```

---

## Step 5 — Create the first admin account

1. Open your browser and go to: **http://127.0.0.1:8000**
2. The setup wizard appears automatically on first access.
3. Enter an admin username and password, then click **Create Account**.
4. You are redirected to the login page.

---

## Step 6 — Log in and index your documents

1. Log in with the admin credentials you just created.
2. Click **Admin → Documents** in the navigation.
3. Click **Index Now** to index all files in `docs/`.
4. Wait for indexing to complete (progress is shown on the page).
5. Once complete, click **Chat** in the navigation and ask your first question.

---

## Auto-start on boot (optional)

### Linux (systemd)
```ini
# /etc/systemd/system/vsnt-rag.service
[Unit]
Description=VSNT RAG Web Platform
After=network.target

[Service]
User=vsnt
WorkingDirectory=/opt/vsnt-rag
ExecStart=/opt/vsnt-rag/.venv/bin/python app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now vsnt-rag
```

### Windows (Task Scheduler)
Create a basic task that runs `pythonw.exe app.py` from the project directory at logon.
A helper script `scripts/register-task.bat` is provided.

---

## Switching the LLM model

1. Install a different model: `ollama pull mistral`
2. In the web app, go to **Admin → Settings**.
3. Select `mistral` from the model dropdown and click **Save**.
4. The next query will use the new model — no restart needed.

---

## Terminal mode (existing CLI)

The original terminal interface is still available:
```bash
python rag_vsnt_offline.py
```
Both modes share the same `docs/` and `.rag_index/` directories.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Ollama não está rodando" on startup | Run `ollama serve` in a separate terminal |
| Blank page or 500 error | Check terminal output for the Python traceback |
| Documents not appearing after upload | Click "Index Now" in Admin → Documents |
| Login rejected immediately after setup | Ensure Caps Lock is off; passwords are case-sensitive |
| Slow queries | Use a smaller model (`mistral`) or add a GPU |
