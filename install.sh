#!/usr/bin/env bash
# VSNT RAG — instalador Linux/macOS
set -e

echo "🔒 VSNT RAG — Instalação"
echo ""

# Python 3.11+
PYTHON=$(command -v python3 || command -v python || true)
if [ -z "$PYTHON" ]; then
  echo "❌ Python não encontrado. Instale o Python 3.11+ e tente novamente."
  exit 1
fi

PY_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
  echo "❌ Python $PY_VER encontrado. Necessário Python 3.11 ou superior."
  exit 1
fi
echo "✅ Python $PY_VER"

# Virtual environment
if [ ! -d ".venv" ]; then
  echo "📦 Criando ambiente virtual..."
  "$PYTHON" -m venv .venv
fi
source .venv/bin/activate
echo "✅ Ambiente virtual ativo"

# Dependencies
echo "📥 Instalando dependências (pode levar alguns minutos)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements_offline.txt
echo "✅ Dependências instaladas"

# Directories
mkdir -p data docs
echo "✅ Diretórios criados"

# Ollama check (warning only)
if command -v ollama &>/dev/null; then
  echo "✅ Ollama encontrado"
else
  echo "⚠️  Ollama não encontrado."
  echo "   Instale em: https://ollama.com/download"
  echo "   Depois execute: ollama pull llama3"
fi

echo ""
echo "✅ Instalação concluída!"
echo ""
echo "Próximos passos:"
echo "  1. Inicie o Ollama:        ollama serve"
echo "  2. Inicie o servidor:      source .venv/bin/activate && python app.py"
echo "  3. Abra no navegador:      http://127.0.0.1:8000"
