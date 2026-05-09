@echo off
cd /d "%~dp0\.."
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-cpu.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-ui.txt
echo CPU setup complete. Run: .\.venv\Scripts\python.exe app.py
