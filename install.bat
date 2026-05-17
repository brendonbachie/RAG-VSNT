@echo off
REM VSNT RAG — instalador Windows
setlocal enabledelayedexpansion

echo [VSNT RAG] Instalacao
echo.

REM Python check
where python >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale Python 3.11+ em https://python.org
    pause & exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER%

REM Virtual environment
if not exist ".venv\" (
    echo [INFO] Criando ambiente virtual...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo [OK] Ambiente virtual ativo

REM Dependencies
echo [INFO] Instalando dependencias...
pip install --quiet --upgrade pip
pip install --quiet -r requirements_offline.txt
echo [OK] Dependencias instaladas

REM Directories
if not exist "data\" mkdir data
if not exist "docs\" mkdir docs
echo [OK] Diretorios criados

REM Ollama check
where ollama >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Ollama nao encontrado. Instale em: https://ollama.com/download
    echo         Depois execute: ollama pull llama3
) else (
    echo [OK] Ollama encontrado
)

echo.
echo [OK] Instalacao concluida!
echo.
echo Proximos passos:
echo   1. Inicie o Ollama (em outro terminal):  ollama serve
echo   2. Inicie o servidor:                    .venv\Scripts\activate ^& python app.py
echo   3. Abra no navegador:                    http://127.0.0.1:8000
echo.
pause
