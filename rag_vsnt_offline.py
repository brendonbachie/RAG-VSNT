"""
RAG - Projeto VSNT (Veículo Subaquático Não Tripulado)
Marinha do Brasil
Sistema 100% OFFLINE — LlamaIndex + Ollama (LLM local) + BGE (embeddings locais)

Melhorias v2:
  1. Hybrid search  — busca semântica (BGE) + BM25 via QueryFusionRetriever (RRF)
  2. Reranking      — cross-encoder offline (ms-marco-MiniLM-L-6-v2)
  3. Memória conv.  — ChatMemoryBuffer + CondensePlusContextChatEngine

NENHUM dado sai da máquina. Zero chamadas externas em operação.
"""

import sys
import json
import urllib.request
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
    Settings,
)
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# ─── Configurações ────────────────────────────────────────────────────────────

DOCS_DIR    = Path("docs")        # pasta com os .md / .txt do projeto
PERSIST_DIR = Path(".rag_index")  # índice vetorial persistido em disco

# Modelo LLM local via Ollama.
# Troque pelo modelo que você baixou:
#   ollama pull llama3          (recomendado, ~4,7 GB)
#   ollama pull mistral         (alternativa leve, ~4,1 GB)
#   ollama pull command-r       (bom para RAG em português, ~8 GB)
#   ollama pull gemma3          (muito bom, ~5 GB)
OLLAMA_MODEL = "llama3"
OLLAMA_URL   = "http://localhost:11434"   # Ollama roda localmente nesta porta

# Embeddings locais — baixados uma vez pelo HuggingFace, depois ficam em cache
# Opções por tamanho de máquina:
#   Máquina leve  → "BAAI/bge-small-en-v1.5"   (~130 MB)
#   Máquina média → "BAAI/bge-base-en-v1.5"    (~440 MB)  ← mais preciso
#   Máquina forte → "BAAI/bge-large-en-v1.5"   (~1,3 GB)  ← melhor qualidade
EMBED_MODEL = "BAAI/bge-base-en-v1.5"

# Cross-encoder para reranking — ~80 MB, baixado uma vez e fica em cache local
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_TOP_N = 3    # chunks finais enviados ao LLM após reranking

SYSTEM_PROMPT = (
    "Você é um assistente técnico especializado no projeto VSNT "
    "(Veículo Subaquático Não Tripulado) da Marinha do Brasil. "
    "Responda sempre em português brasileiro, com precisão técnica, "
    "citando o documento e a seção quando possível. "
    "Se a informação não estiver na base de conhecimento, diga claramente "
    "que não encontrou na documentação e não invente dados."
)

# ─── Verificações de pré-requisito ───────────────────────────────────────────

def _check_ollama():
    """Verifica se o Ollama está rodando e se o modelo está disponível."""
    try:
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3)
    except Exception:
        print("❌ Ollama não está rodando.")
        print("   Inicie com:  ollama serve")
        print(f"   E baixe o modelo (uma vez):  ollama pull {OLLAMA_MODEL}")
        sys.exit(1)

    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags") as r:
            data = json.loads(r.read())
        models = [m["name"].split(":")[0] for m in data.get("models", [])]
        if OLLAMA_MODEL not in models:
            print(f"⚠️  Modelo '{OLLAMA_MODEL}' não encontrado localmente.")
            print(f"   Baixe com:  ollama pull {OLLAMA_MODEL}")
            print(f"   Modelos disponíveis: {', '.join(models) or 'nenhum'}")
            sys.exit(1)
    except Exception:
        pass   # se não conseguir verificar, tenta continuar


# ─── Inicialização ────────────────────────────────────────────────────────────

def build_settings():
    """Configura LLM local (Ollama) e embeddings locais (HuggingFace)."""
    print(f"🦙 LLM:        Ollama / {OLLAMA_MODEL}  (local)")
    print(f"🔢 Embeddings: {EMBED_MODEL}  (local)")
    print(f"🔁 Reranker:   {RERANK_MODEL}  (local)")

    Settings.llm = Ollama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_URL,
        request_timeout=120.0,   # modelos locais podem ser mais lentos
        temperature=0.1,         # respostas mais determinísticas/técnicas
        context_window=8192,
    )
    Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)
    Settings.node_parser = MarkdownNodeParser()  # respeita headings Markdown


def _embedding_dims_match(index: VectorStoreIndex) -> bool:
    """Returns False if any stored embedding is wrong-sized or 2-D (inhomogeneous)."""
    try:
        embs = index._vector_store._data.embedding_dict
        if not embs:
            return True
        expected = len(Settings.embed_model.get_text_embedding("test"))
        for v in embs.values():
            if not hasattr(v, "__len__") or len(v) != expected:
                return False
            # 2-D embedding causes the inhomogeneous-array error at query time
            if hasattr(v[0], "__len__"):
                return False
        return True
    except Exception:
        return True  # can't inspect — assume OK


def load_or_build_index() -> VectorStoreIndex:
    """Carrega índice existente ou cria um novo a partir dos documentos."""
    if PERSIST_DIR.exists():
        print("📂 Carregando índice existente...")
        storage_ctx = StorageContext.from_defaults(persist_dir=str(PERSIST_DIR))
        index = load_index_from_storage(storage_ctx)
        if _embedding_dims_match(index):
            return index
        print(
            f"⚠️  Embeddings no índice têm dimensão incompatível com '{EMBED_MODEL}'. "
            "Reconstruindo índice automaticamente..."
        )
        import shutil
        shutil.rmtree(PERSIST_DIR)

    print(f"📄 Indexando documentos em '{DOCS_DIR}'...")
    if not DOCS_DIR.exists():
        DOCS_DIR.mkdir(parents=True)
        _create_sample_doc()

    documents = SimpleDirectoryReader(
        input_dir=str(DOCS_DIR),
        required_exts=[".md", ".txt"],
        recursive=True,
        filename_as_id=True,
    ).load_data()

    if not documents:
        print(f"⚠️  Nenhum arquivo .md ou .txt encontrado em '{DOCS_DIR}'.")
        print("   Adicione a documentação do VSNT e execute novamente.")
        sys.exit(1)

    print(f"   {len(documents)} arquivo(s) carregado(s). Gerando embeddings...")
    index = VectorStoreIndex.from_documents(documents, show_progress=True)
    index.storage_context.persist(persist_dir=str(PERSIST_DIR))
    print(f"✅ Índice salvo em '{PERSIST_DIR}'")
    return index


def _create_sample_doc():
    """Cria documento de exemplo para demonstração."""
    sample = DOCS_DIR / "overview_vsnt.md"
    sample.write_text(
        "# VSNT – Visão Geral\n\n"
        "O VSNT é um drone aquático desenvolvido pela Marinha do Brasil "
        "para missões de reconhecimento, monitoramento e inspeção subaquática.\n\n"
        "## Subsistemas Principais\n"
        "- **Propulsão**: motores brushless waterproof com hélices de 3 pás\n"
        "- **Navegação**: INS + DVL + GPS de superfície\n"
        "- **Comunicação**: acústico subaquático / RF em superfície\n"
        "- **Payload**: câmera estereoscópica 4K + sonar de varredura lateral\n\n"
        "## Especificações Gerais\n"
        "| Parâmetro          | Valor  |\n"
        "|--------------------|--------|\n"
        "| Comprimento        | 1,8 m  |\n"
        "| Peso em ar         | 42 kg  |\n"
        "| Profundidade máx.  | 150 m  |\n"
        "| Autonomia          | 6 h    |\n",
        encoding="utf-8",
    )
    print("   📝 Documento de exemplo criado: docs/overview_vsnt.md")


# ─── Pipeline de recuperação ──────────────────────────────────────────────────

def _build_hybrid_retriever(index: VectorStoreIndex) -> QueryFusionRetriever:
    """
    Busca híbrida: BGE (semântico) + BM25 (palavras-chave) fundidos por RRF.

    similarity_top_k=10 em cada retriever garante candidatos suficientes
    para o reranker escolher entre eles; o reranker reduz para RERANK_TOP_N.
    num_queries=1 desativa expansão de queries pelo LLM (mantém offline puro).
    """
    nodes = list(index.storage_context.docstore.docs.values())

    vector_retriever = index.as_retriever(similarity_top_k=10)
    bm25_retriever   = BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=10)

    return QueryFusionRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        similarity_top_k=5,
        num_queries=1,              # sem geração de queries extras via LLM
        mode="reciprocal_rerank",   # Reciprocal Rank Fusion (RRF)
        use_async=False,
    )


def build_chat_engine(index: VectorStoreIndex) -> CondensePlusContextChatEngine:
    """
    Motor de chat com:
      - retriever híbrido (BGE + BM25)
      - reranking por cross-encoder
      - memória conversacional (histórico da sessão)

    CondensePlusContextChatEngine condensa o histórico em uma pergunta
    autônoma antes de recuperar contexto, permitindo perguntas de
    acompanhamento como "e sobre a propulsão?" funcionarem corretamente.
    """
    retriever = _build_hybrid_retriever(index)

    reranker = SentenceTransformerRerank(
        model=RERANK_MODEL,
        top_n=RERANK_TOP_N,
    )

    # token_limit controla quanto do histórico de chat é mantido no contexto
    memory = ChatMemoryBuffer.from_defaults(token_limit=2000)

    return CondensePlusContextChatEngine.from_defaults(
        retriever=retriever,
        memory=memory,
        system_prompt=SYSTEM_PROMPT,
        node_postprocessors=[reranker],
        llm=Settings.llm,
        verbose=False,
    )


# ─── Interface de consulta ────────────────────────────────────────────────────

def interactive_query(index: VectorStoreIndex):
    """Loop de chat com memória conversacional no terminal."""
    print("⚙️  Inicializando retriever híbrido e reranker...")
    chat_engine = build_chat_engine(index)

    print("\n" + "═" * 62)
    print("  🤿  VSNT RAG — Consulta Técnica Interna  [MODO OFFLINE]")
    print("  Projeto VSNT | Marinha do Brasil")
    print("═" * 62)
    print("  Nenhum dado trafega pela internet.")
    print("  Busca híbrida (BGE + BM25) + reranking cross-encoder.")
    print("  Histórico da conversa mantido na sessão.")
    print("  'limpar' → reinicia histórico  |  'sair' → encerra\n")

    while True:
        try:
            pergunta = input("❓ Pergunta: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Encerrando.")
            break

        if not pergunta:
            continue
        if pergunta.lower() in ("sair", "exit", "quit"):
            print("👋 Encerrando.")
            break
        if pergunta.lower() in ("limpar", "clear", "reset"):
            chat_engine.reset()
            print("🗑️  Histórico da conversa limpo.\n")
            continue

        print("\n🔍 Consultando base de conhecimento (processamento local)...")
        try:
            response = chat_engine.chat(pergunta)
        except Exception as e:
            print(f"❌ Erro ao consultar: {e}")
            print("   Verifique se o Ollama ainda está rodando.")
            continue

        print(f"\n💬 Resposta:\n{response.response}\n")

        if response.source_nodes:
            print("📎 Fontes consultadas:")
            seen = set()
            for node in response.source_nodes:
                src = node.metadata.get("file_name", "desconhecido")
                score = node.score or 0.0
                if src not in seen:
                    print(f"   • {src}  (relevância: {score:.2f})")
                    seen.add(src)
        print("─" * 62)


# ─── Entrypoint ───────────────────────────────────────────────────────────────

def main():
    print("🔒 VSNT RAG — Sistema 100% Offline  (v2 — hybrid + rerank + memória)")
    print(f"   LLM local : {OLLAMA_MODEL} via Ollama")
    print(f"   Embeddings: {EMBED_MODEL} (cache local)")
    print(f"   Reranker  : {RERANK_MODEL} (cache local)\n")

    _check_ollama()
    build_settings()
    index = load_or_build_index()
    interactive_query(index)


if __name__ == "__main__":
    main()
