@echo off
echo.
echo  ============================================
echo   SentriCore / NovaSentinel - API + Frontend
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

:: Kill any ghost process on port 8000 and 5173
echo [INFO] Cleaning up ghost processes...
FOR /F "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /f /pid %%a >nul 2>&1
FOR /F "tokens=5" %%a in ('netstat -aon ^| findstr :5173') do taskkill /f /pid %%a >nul 2>&1

:: Launch API Backend in a new window
echo [READY] Launching FastAPI Backend...
start "SentriCore API" cmd /k "python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload || pause"

:: Wait a moment for API to spin up
timeout /t 5 /nobreak >nul

:: Launch React frontend
echo.
echo [READY] Launching React frontend...
echo  Open: http://localhost:5173
echo.
start "SentriCore Frontend" cmd /k "cd frontend && npm run dev -- --host 127.0.0.1 --port=5173 || pause"
