@echo off
REM VSNT RAG — registrar como tarefa agendada no Windows (logon do usuario atual)
setlocal

set TASK_NAME=VSNT-RAG
set PROJECT_DIR=%~dp0..
set PYTHON=%PROJECT_DIR%\.venv\Scripts\pythonw.exe
set SCRIPT=%PROJECT_DIR%\app.py

echo [VSNT RAG] Registrando tarefa agendada...

schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%PYTHON%\" \"%SCRIPT%\"" ^
  /sc onlogon ^
  /ru "%USERNAME%" ^
  /f

if errorlevel 1 (
    echo [ERRO] Falha ao registrar a tarefa. Execute como Administrador.
    pause & exit /b 1
)

echo [OK] Tarefa "%TASK_NAME%" registrada com sucesso.
echo      O servidor iniciara automaticamente no proximo logon.
echo      Para iniciar agora: schtasks /run /tn "%TASK_NAME%"
pause
