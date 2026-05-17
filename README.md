# RAG VSNT — Plataforma Offline de Consulta Técnica

Sistema RAG multi-usuário com interface web para organizações que precisam consultar documentação técnica sigilosa **100% offline**. Nenhum dado sai da máquina em nenhum momento.

---

## Visão geral

```
┌──────────────────────────────────────────────────────────────┐
│                        SUA MÁQUINA                           │
│                                                              │
│  Navegador → http://127.0.0.1:8000                           │
│       │                                                      │
│   FastAPI (app.py)                                           │
│       ├── Autenticação (sessão assinada, httponly)           │
│       ├── Chat RAG → LlamaIndex + BGE + BM25 + Reranker      │
│       ├── Admin: usuários, documentos, configurações         │
│       └── Audit log (SQLite + arquivo local)                 │
│                                                              │
│  docs/  →  .rag_index/  →  Ollama (porta 11434)             │
│       ← zero tráfego externo em operação →                   │
└──────────────────────────────────────────────────────────────┘
```

---

## Funcionalidades

- **Interface web** acessível no navegador, sem necessidade de terminal
- **Autenticação** com usuário e senha; sessão com timeout configurável (padrão 8 h)
- **Papéis**: Operador (apenas consulta) e Admin (consulta + gerenciamento)
- **Wizard de primeiro acesso** — cria o admin pelo navegador, sem comandos
- **Upload de documentos** via painel admin (PDF, DOCX, Markdown, TXT) ou pasta `docs/`
- **Indexação automática** ao detectar novos arquivos em `docs/`
- **Troca de modelo Ollama** em tempo real pelo painel admin, sem reiniciar
- **Audit log** de todas as consultas e eventos de autenticação
- **Modo terminal preservado** — `rag_vsnt_offline.py` continua funcionando

---

## Instalação

### Pré-requisitos

| Requisito | Versão mínima | Observação |
|-----------|--------------|------------|
| Python    | 3.11+        | [python.org](https://www.python.org/downloads/) |
| Ollama    | qualquer     | [ollama.com/download](https://ollama.com/download) |
| RAM       | 8 GB         | 16 GB recomendado |

### Linux / macOS

```bash
git clone <repositório> && cd RAG-VSNT
bash install.sh
```

### Windows

```bat
git clone <repositório>
cd RAG-VSNT
install.bat
```

Os scripts criam o ambiente virtual, instalam dependências e verificam o Ollama automaticamente.

---

## Inicialização

### 1. Inicie o Ollama (mantenha rodando em background)

```bash
ollama serve
```

Baixe pelo menos um modelo (necessário apenas uma vez):

```bash
ollama pull llama3        # recomendado — bom português, ~4,7 GB
ollama pull mistral       # alternativa leve, ~4,1 GB
ollama pull gemma3        # excelente qualidade, ~5 GB
```

### 2. Inicie o servidor web

```bash
# Linux / macOS
source .venv/bin/activate
python app.py

# Windows
.venv\Scripts\activate
python app.py
```

### 3. Abra o navegador

```
http://127.0.0.1:8000
```

Na primeira visita, o sistema detecta que não há admin cadastrado e exibe o **wizard de configuração** para criar a conta administrador.

---

## Uso

### Consulta de documentos

1. Faça login com suas credenciais
2. Digite sua pergunta em linguagem natural no chat
3. O sistema retorna a resposta com citação da fonte em até 60 s

Se a informação não estiver nos documentos indexados, o sistema responde:
> "Não encontrei essa informação na documentação disponível."

### Adicionar documentos

**Via painel admin** (recomendado): acesse `/admin/documents`, clique em "Upload" e selecione arquivos PDF, DOCX, MD ou TXT.

**Via pasta**: copie os arquivos para `docs/` — a indexação é disparada automaticamente.

Formatos aceitos: `.pdf`, `.docx`, `.doc`, `.md`, `.txt`

### Painel de administração (`/admin`)

| Seção         | Acesso | Função |
|---------------|--------|--------|
| Usuários      | Admin  | Criar, ativar/desativar, excluir contas |
| Documentos    | Admin  | Upload, listar, excluir, re-indexar |
| Configurações | Admin  | Trocar modelo Ollama, ajustar timeout de sessão |
| Auditoria     | Admin  | Ver últimos 100 eventos (consultas e autenticações) |

---

## Estrutura do projeto

```
app.py                     # Entrada FastAPI — monta routers, inicia uvicorn
config.py                  # Configurações centrais (porta, caminhos, modelos)
rag_vsnt_offline.py        # Modo terminal original (preservado)

src/
├── auth/                  # Login, logout, wizard, sessão assinada
├── chat/                  # Engine RAG + rota de consulta
├── admin/                 # Usuários, documentos, configurações, indexador
├── audit/                 # Logger de consultas e eventos
├── db/                    # SQLAlchemy async + SQLite
├── models/                # ORM: User, AuditEvent, SystemSettings
└── templates/             # HTML (Jinja2): login, chat, admin, setup

static/                    # CSS e JS do frontend
docs/                      # Documentos-fonte (PDF, DOCX, MD, TXT)
.rag_index/                # Índice vetorial (LlamaIndex, gerado automaticamente)
data/vsnt_rag.db           # Banco SQLite (usuários, audit, configurações)
```

---

## Configuração via variáveis de ambiente

| Variável                | Padrão                        | Descrição |
|-------------------------|-------------------------------|-----------|
| `OLLAMA_MODEL`          | `llama3`                      | Modelo LLM padrão |
| `OLLAMA_URL`            | `http://localhost:11434`      | Endereço do Ollama |
| `EMBED_MODEL`           | `BAAI/bge-base-en-v1.5`      | Modelo de embeddings |
| `RERANK_MODEL`          | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Modelo de reranking |
| `SERVER_HOST`           | `127.0.0.1`                   | Host do servidor (não alterar) |
| `SERVER_PORT`           | `8000`                        | Porta do servidor |
| `SESSION_TIMEOUT_SECONDS` | `28800`                    | Timeout de sessão (8 h) |

O modelo ativo e o timeout também podem ser alterados pelo painel admin sem reiniciar.

---

## Requisitos de hardware

| Configuração | RAM   | GPU        | Modelo sugerido |
|--------------|-------|------------|-----------------|
| Mínima       | 8 GB  | Sem GPU    | mistral (4-bit) |
| Recomendada  | 16 GB | 6 GB VRAM  | llama3          |
| Ideal        | 32 GB | 12 GB VRAM | command-r       |

---

## Segurança

| Componente          | Trafega internet? | Observação |
|---------------------|-------------------|------------|
| FastAPI / Jinja2    | Não               | Servidor local, apenas 127.0.0.1 |
| Ollama (LLM)        | Não               | Porta 11434, localhost |
| BGE Embeddings      | Não               | Cache local após 1ª instalação |
| Índice vetorial     | Não               | Arquivo em `.rag_index/` no disco |
| Documentos `docs/`  | Não               | Nunca saem da máquina |
| Banco de dados      | Não               | SQLite local em `data/vsnt_rag.db` |
| Sessões             | Não               | Cookie httponly, assinado com chave local |

**Recomendações para ambientes classificados:**
- Execute com firewall ativo bloqueando saída de rede
- Use disco criptografado (LUKS / BitLocker) para `docs/`, `.rag_index/` e `data/`
- Controle acesso físico à máquina
- Revise o audit log periodicamente via painel admin ou diretamente no banco SQLite

---

## Air-gap total (sem internet na máquina de destino)

1. Em uma máquina com internet, baixe o repositório, execute `install.sh` / `install.bat` e pré-baixe os modelos:

```bash
# Modelos de embedding e reranking (cache HuggingFace)
python -c "
from sentence_transformers import SentenceTransformer, CrossEncoder
SentenceTransformer('BAAI/bge-base-en-v1.5')
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
"

# Modelo Ollama
ollama pull llama3
ollama save llama3 llama3.tar
```

2. Transfira a pasta do projeto (incluindo `.venv/` e `~/.cache/huggingface/`) e o arquivo `llama3.tar` para a máquina destino via mídia física.

3. Na máquina destino:

```bash
ollama load llama3.tar
python app.py
```
