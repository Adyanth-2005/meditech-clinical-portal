@echo off
REM ==================================================================
REM  Bangalore City Hospital - Meditech Lab  (Windows launcher)
REM  Double-click this file, or run it from a terminal.
REM ==================================================================
setlocal

REM Find a Python interpreter (prefer the py launcher, fall back to python)
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PY=py -3"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL%==0 (
        set "PY=python"
    ) else (
        echo.
        echo   Python was not found on PATH.
        echo   Install Python 3.11+ from https://www.python.org/downloads/
        echo   During install, tick "Add python.exe to PATH".
        echo.
        pause
        exit /b 1
    )
)

cd /d "%~dp0"
%PY% run_lab.py %*

echo.
pause
