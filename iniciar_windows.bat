@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -m venv .venv
  if errorlevel 1 (echo Nao foi possivel criar o ambiente Python.& pause & exit /b 1)
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (echo Falha ao instalar Flask. Confira sua conexao e execute novamente.& pause & exit /b 1)
start "" http://127.0.0.1:5000
".venv\Scripts\python.exe" app.py
pause
