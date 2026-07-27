@echo off
cd /d "%~dp0backend"

REM Prefer Python 3.12/3.13 if installed (3.14 often breaks pip builds)
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3.12 -c "import sys" >nul 2>nul
  if %ERRORLEVEL%==0 (
    set PY=py -3.12
  ) else (
    py -3.13 -c "import sys" >nul 2>nul
    if %ERRORLEVEL%==0 (
      set PY=py -3.13
    ) else (
      set PY=python
    )
  )
) else (
  set PY=python
)

if not exist .venv (
  %PY% -m venv .venv
  call .venv\Scripts\python.exe -m pip install --upgrade pip
  call .venv\Scripts\python.exe -m pip install -r requirements.txt
)

call .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
