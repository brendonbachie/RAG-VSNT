# 🔒 RAG VSNT — Modo 100% Offline

Guia de instalação e operação **sem nenhuma conexão com a internet**.
Ideal para ambientes classificados e redes isoladas (air-gap).

---

## Fluxo de dados (tudo local)

```
┌─────────────────────────────────────────────────────┐
│                    SUA MÁQUINA                      │
│                                                     │
│  docs/*.md  →  LlamaIndex  →  BGE Embeddings        │
│                    │               (cache local)    │
│              .rag_index/                            │
│              (índice vetorial                       │
│               em disco)                            │
│                    │                                │
│              Ollama (porta 11434)                   │
│              └── llama3 / mistral / gemma3          │
│                    │                                │
│              Resposta no terminal                   │
└─────────────────────────────────────────────────────┘
          ← zero tráfego externo em operação →
```

---

## Instalação (faça uma vez, pode ser com internet)

### 1. Instale o Ollama

```bash
# Linux / macOS
curl -fsSL https://ollama.com/install.sh | sh

# Windows: baixe o instalador em https://ollama.com/download
```

> Em ambiente totalmente air-gap, baixe o instalador e o modelo
> em uma máquina com internet e transfira via mídia física.

### 2. Baixe o modelo LLM (escolha um)

```bash
ollama pull llama3       # recomendado — bom português, ~4,7 GB
ollama pull mistral      # alternativa leve, ~4,1 GB
ollama pull gemma3       # excelente qualidade, ~5 GB
ollama pull command-r    # otimizado para RAG, ~8 GB
```

> **Transferência air-gap:** use `ollama save` / `ollama load` para
> exportar e importar modelos via arquivo.

### 3. Instale as dependências Python

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

pip install -r requirements_offline.txt
```

> Na primeira execução, o modelo de embeddings BGE (~440 MB) é baixado
> automaticamente. Para air-gap total, pré-baixe com:
> ```python
> from sentence_transformers import SentenceTransformer
> SentenceTransformer("BAAI/bge-base-en-v1.5")
> ```
> e copie o cache (~/.cache/huggingface/) para a máquina destino.

---

## Uso

### 1. Inicie o Ollama (deixe rodando em background)

```bash
ollama serve
```

### 2. Coloque a documentação em `docs/`

```
docs/
├── arquitetura_sistema.md
├── protocolo_comunicacao.md
├── manual_operacao.md
└── subsistemas/
    ├── propulsao.md
    └── navegacao.md
```

### 3. Execute o sistema RAG

```bash
python rag_vsnt_offline.py
```

```
🔒 VSNT RAG — Sistema 100% Offline
   LLM local : llama3 via Ollama
   Embeddings: BAAI/bge-base-en-v1.5 (cache local)

✅ Ollama OK — modelo llama3 disponível
📂 Carregando índice existente...

═══════════════════════════════════════════════════════════════
  🤿  VSNT RAG — Consulta Técnica Interna  [MODO OFFLINE]
  Projeto VSNT | Marinha do Brasil
═══════════════════════════════════════════════════════════════
  Nenhum dado trafega pela internet.
  Digite sua pergunta ou 'sair' para encerrar.

❓ Pergunta: Qual é o sistema de navegação do VSNT?
```

---

## Trocar o modelo LLM

Edite a linha no `rag_vsnt_offline.py`:

```python
OLLAMA_MODEL = "llama3"   # troque para "mistral", "gemma3", etc.
```

E apague o índice para reindexar com o novo modelo:

```bash
rm -rf .rag_index/
python rag_vsnt_offline.py
```

---

## Requisitos de hardware

| Configuração | RAM   | GPU        | Modelo sugerido  |
|--------------|-------|------------|------------------|
| Mínima       | 8 GB  | Sem GPU    | mistral (4-bit)  |
| Recomendada  | 16 GB | 6 GB VRAM  | llama3           |
| Ideal        | 32 GB | 12 GB VRAM | command-r        |

---

## Segurança

| Componente         | Trafega internet? | Observação                        |
|--------------------|-------------------|-----------------------------------|
| LlamaIndex         | ❌ Não            | Biblioteca local                  |
| Ollama (LLM)       | ❌ Não            | Roda na porta 11434, localhost    |
| BGE Embeddings     | ❌ Não            | Cache local após 1ª instalação    |
| Índice vetorial    | ❌ Não            | Arquivo em `.rag_index/` no disco |
| Documentos `docs/` | ❌ Não            | Nunca saem da máquina             |

**Recomendações adicionais para ambientes classificados:**
- Execute em máquina com firewall ativo bloqueando saída
- Use disco criptografado (LUKS / BitLocker) para proteger `docs/` e `.rag_index/`
- Controle acesso físico à máquina
- Registre log de consultas para auditoria (ver `manage_index.py`)
