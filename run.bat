@echo off
echo.
echo  ============================================
echo   SentriCore AgentShield - API Edition
echo  ============================================
echo.

:: Check venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [WARNING] Virtual environment not found! Using global python environment.
) else (
    call venv\Scripts\activate.bat
)

:: Initialize the database
echo [INFO] Initializing database...
python -c "import database; database.init_db()"
python -c "import audit_logger; audit_logger.init_log_table()"

:: Kill any ghost uvicorn process on port 8000 and 8501
echo [INFO] Cleaning up ghost processes...
FOR /F "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /f /pid %%a >nul 2>&1
FOR /F "tokens=5" %%a in ('netstat -aon ^| findstr :8501') do taskkill /f /pid %%a >nul 2>&1

:: Launch API Backend in a new window
echo [READY] Launching FastAPI Backend...
start "SentriCore API" cmd /k "python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload || pause"

:: Wait a moment for API to spin up
timeout /t 5 /nobreak >nul

:: Launch Streamlit app
echo.
echo [READY] Launching SentriCore dashboard...
echo  Open: http://localhost:8501
echo.
start "SentriCore UI" cmd /k "python -m streamlit run app.py || pause"
