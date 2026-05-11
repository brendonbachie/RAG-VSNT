"""
Gerenciamento de índice VSNT RAG
Uso:
  python manage_index.py add    docs/novo_doc.md
  python manage_index.py update docs/doc_atualizado.md
  python manage_index.py delete docs/doc_antigo.md
  python manage_index.py list
  python manage_index.py rebuild
"""

import os
import sys
import argparse
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
    Settings,
    Document,
)
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

DOCS_DIR    = Path("docs")
PERSIST_DIR = Path(".rag_index")
EMBED_MODEL = "BAAI/bge-base-en-v1.5"


OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")


def build_settings():
    Settings.llm = Ollama(model=OLLAMA_MODEL, request_timeout=120.0)
    Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)
    Settings.node_parser = MarkdownNodeParser()


def load_index() -> VectorStoreIndex:
    if not PERSIST_DIR.exists():
        print("❌ Índice não encontrado. Execute rag_vsnt.py primeiro.")
        sys.exit(1)
    storage_ctx = StorageContext.from_defaults(persist_dir=str(PERSIST_DIR))
    return load_index_from_storage(storage_ctx)


def cmd_list(_args):
    """Lista todos os documentos no índice."""
    index = load_index()
    docstore = index.storage_context.docstore
    docs = docstore.docs
    if not docs:
        print("📭 Nenhum documento indexado.")
        return
    print(f"\n📚 {len(docs)} documento(s) no índice:\n")
    for doc_id, doc in docs.items():
        fname = doc.metadata.get("file_name", doc_id)
        tokens = len(doc.text.split())
        print(f"  • {fname:50s}  (~{tokens} tokens)")


def cmd_add(args):
    """Adiciona um novo arquivo ao índice sem reindexar tudo."""
    path = Path(args.file)
    if not path.exists():
        print(f"❌ Arquivo não encontrado: {path}")
        sys.exit(1)

    index = load_index()
    docs = SimpleDirectoryReader(input_files=[str(path)]).load_data()
    for doc in docs:
        index.insert(doc)
    index.storage_context.persist(persist_dir=str(PERSIST_DIR))
    print(f"✅ '{path.name}' adicionado ao índice.")


def cmd_update(args):
    """Atualiza um documento existente (remove + re-insere)."""
    path = Path(args.file)
    if not path.exists():
        print(f"❌ Arquivo não encontrado: {path}")
        sys.exit(1)

    index = load_index()
    # Remove versão antiga pelo file_name nos metadados
    docstore = index.storage_context.docstore
    to_delete = [
        doc_id for doc_id, doc in docstore.docs.items()
        if doc.metadata.get("file_name") == path.name
    ]
    for doc_id in to_delete:
        index.delete_ref_doc(doc_id, delete_from_docstore=True)

    docs = SimpleDirectoryReader(input_files=[str(path)]).load_data()
    for doc in docs:
        index.insert(doc)
    index.storage_context.persist(persist_dir=str(PERSIST_DIR))
    print(f"✅ '{path.name}' atualizado ({len(to_delete)} versão(ões) anterior(es) removida(s)).")


def cmd_delete(args):
    """Remove um documento do índice."""
    path = Path(args.file)
    index = load_index()
    docstore = index.storage_context.docstore
    to_delete = [
        doc_id for doc_id, doc in docstore.docs.items()
        if doc.metadata.get("file_name") == path.name
    ]
    if not to_delete:
        print(f"⚠️  '{path.name}' não encontrado no índice.")
        return
    for doc_id in to_delete:
        index.delete_ref_doc(doc_id, delete_from_docstore=True)
    index.storage_context.persist(persist_dir=str(PERSIST_DIR))
    print(f"🗑️  '{path.name}' removido do índice.")


def cmd_rebuild(_args):
    """Reconstrói o índice do zero a partir de docs/."""
    import shutil
    if PERSIST_DIR.exists():
        shutil.rmtree(PERSIST_DIR)
        print("🗑️  Índice antigo removido.")
    documents = SimpleDirectoryReader(
        input_dir=str(DOCS_DIR),
        required_exts=[".md", ".txt"],
        recursive=True,
        filename_as_id=True,
    ).load_data()
    print(f"📄 {len(documents)} arquivo(s) encontrado(s). Reindexando...")
    index = VectorStoreIndex.from_documents(documents, show_progress=True)
    index.storage_context.persist(persist_dir=str(PERSIST_DIR))
    print(f"✅ Índice reconstruído com {len(documents)} documento(s).")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    build_settings()

    parser = argparse.ArgumentParser(description="Gerencia o índice RAG do VSNT")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list",    help="Lista documentos indexados")
    sub.add_parser("rebuild", help="Reconstrói índice do zero")

    p_add = sub.add_parser("add",    help="Adiciona arquivo ao índice")
    p_add.add_argument("file")

    p_upd = sub.add_parser("update", help="Atualiza arquivo no índice")
    p_upd.add_argument("file")

    p_del = sub.add_parser("delete", help="Remove arquivo do índice")
    p_del.add_argument("file")

    args = parser.parse_args()
    dispatch = {
        "list":    cmd_list,
        "add":     cmd_add,
        "update":  cmd_update,
        "delete":  cmd_delete,
        "rebuild": cmd_rebuild,
    }
    if args.cmd in dispatch:
        dispatch[args.cmd](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
