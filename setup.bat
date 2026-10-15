@echo off
TITLE ClipAI Generator - Setup
color 0A

echo.
echo  ============================================
echo    CLIPAI GENERATOR - INSTALACION AUTOMATICA
echo  ============================================
echo.

:: Check Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    py --version >nul 2>&1
    IF ERRORLEVEL 1 (
        echo [INFO] Python no encontrado. Intentando instalar Python 3.11 via winget...
        winget install --id=Python.Python.3.11 -e --silent --accept-package-agreements --accept-source-agreements
        IF ERRORLEVEL 1 (
            echo [ERROR] No se pudo instalar Python automaticamente.
            echo         Por favor descarga e instala Python 3.10+ desde:
            echo         https://www.python.org/downloads/
            echo         (IMPORTANTE: Marca la casilla "Add python.exe to PATH")
            pause
            exit /b 1
        ) ELSE (
            echo [OK] Python instalado. Es posible que debas reiniciar tu terminal si no se reconoce de inmediato.
        )
    ) ELSE (
        echo [OK] Python Launcher (py) encontrado.
    )
) ELSE (
    echo [OK] Python encontrado.
)

:: Check ffmpeg
ffmpeg -version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [INFO] FFmpeg no encontrado. Instalando via winget...
    winget install --id=Gyan.FFmpeg -e --silent
    IF ERRORLEVEL 1 (
        echo [WARN] No se pudo instalar FFmpeg automaticamente.
        echo        Por favor descarga FFmpeg de: https://ffmpeg.org/download.html
        echo        y agrega al PATH del sistema.
        echo        Puedes continuar, pero el modulo de video no funcionara.
        pause
    ) ELSE (
        echo [OK] FFmpeg instalado correctamente.
    )
) ELSE (
    echo [OK] FFmpeg encontrado.
)

:: Create and activate virtual environment
IF NOT EXIST .venv (
    echo.
    echo [INFO] Creando entorno virtual .venv...
    python -m venv .venv
    IF ERRORLEVEL 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
)
call .venv\Scripts\activate.bat

:: Install Python dependencies
echo.
echo [INFO] Instalando dependencias Python en .venv...
pip install -r backend/requirements.txt
IF ERRORLEVEL 1 (
    echo [ERROR] Fallo al instalar dependencias.
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas.

:: Create .env if not exists
IF NOT EXIST .env (
    echo [INFO] Creando archivo .env de configuracion...
    copy .env.example .env >nul
    echo [OK] .env creado. Edita el archivo con tus claves de API cuando estes listo.
)

echo.
echo  ============================================
echo    INICIANDO CLIPAI GENERATOR...
echo  ============================================
echo.
echo  Backend API: http://localhost:8000
echo  App visual:  http://localhost:8501
echo.

:: Start FastAPI backend in background
start "ClipAI Backend" cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait 3 seconds for backend to start
timeout /t 3 /nobreak >nul

:: Start Streamlit frontend
streamlit run frontend/app.py --server.port 8501 --server.headless false

pause
