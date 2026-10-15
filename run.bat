@echo off
TITLE ClipAI Generator
color 0A

echo.
echo ===================================================
echo             CLIPAI GENERATOR - START
echo ===================================================
echo.
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

echo [1/2] Iniciando Backend FastAPI en http://localhost:8000 ...
start "ClipAI Backend" cmd /k "if exist .venv\Scripts\activate.bat (call .venv\Scripts\activate.bat) && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Esperando inicio del servidor...
timeout /t 3 /nobreak >nul

echo Iniciando Frontend Streamlit en http://localhost:8501 ...
streamlit run frontend/app.py --server.port 8501 --server.headless false

pause

