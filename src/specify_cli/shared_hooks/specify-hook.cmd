@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHON_LAUNCHER=%SCRIPT_DIR%specify-hook.py"
for %%I in ("%SCRIPT_DIR%..\..") do set "PROJECT_ROOT=%%~fI"

if not "%SPECIFY_HOOK_RUNTIME_COMMAND%"=="" (
  call %SPECIFY_HOOK_RUNTIME_COMMAND% "%PYTHON_LAUNCHER%" %*
  exit /b %ERRORLEVEL%
)

if not "%SPECIFY_HOOK_RUNTIME_ARGV%"=="" (
  echo SPECIFY_HOOK_RUNTIME_ARGV is not supported by specify-hook.cmd; use SPECIFY_HOOK_RUNTIME_COMMAND instead. 1>&2
  exit /b 2
)

if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
  "%PROJECT_ROOT%\.venv\Scripts\python.exe" "%PYTHON_LAUNCHER%" %*
  exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if not errorlevel 1 (
  py "%PYTHON_LAUNCHER%" %*
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if not errorlevel 1 (
  python "%PYTHON_LAUNCHER%" %*
  exit /b %ERRORLEVEL%
)

echo No usable Python runtime found for native hook launcher. Run "specify integration repair" or install Python. 1>&2
exit /b 2
