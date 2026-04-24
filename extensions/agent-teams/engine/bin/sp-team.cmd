@echo off
setlocal
set SCRIPT_DIR=%~dp0
set ENTRY=%SCRIPT_DIR%..\dist\cli\omx.js

if not exist "%ENTRY%" (
  echo sp-team: missing runtime entrypoint at %ENTRY% 1>&2
  exit /b 1
)

if "%~1"=="" (
  node "%ENTRY%" team api --help
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="status" (
  shift
  node "%ENTRY%" team status %*
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="await" (
  shift
  node "%ENTRY%" team await %*
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="resume" (
  shift
  node "%ENTRY%" team resume %*
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="shutdown" (
  shift
  node "%ENTRY%" team shutdown %*
  exit /b %ERRORLEVEL%
)

node "%ENTRY%" team api %*
