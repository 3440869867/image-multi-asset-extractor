@echo off
cd /d "%~dp0\.."
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-amd-directml.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-ui.txt
.\.venv\Scripts\python.exe extract_assets.py --check-env --allow-cpu
echo AMD DirectML setup complete. Run: .\.venv\Scripts\python.exe app.py and choose amd-directml.
