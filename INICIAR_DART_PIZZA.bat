@echo off
setlocal
cd /d "%~dp0"
echo ==============================================
echo          DART PIZZA AI - INICIO LOCAL
echo ==============================================
where py >nul 2>nul
if errorlevel 1 (
  echo No se encontro Python. Instala Python 3.10+ desde https://www.python.org/downloads/
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  echo Creando entorno virtual...
  py -3 -m venv .venv
  if errorlevel 1 goto error
)
echo Activando entorno...
call .venv\Scripts\activate.bat
echo Instalando o verificando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto error
echo.
echo Aplicacion lista: http://127.0.0.1:8000
echo Documentacion API: http://127.0.0.1:8000/docs
echo Detener con Ctrl+C.
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
exit /b 0
:error
echo Ocurrio un error durante la preparacion. Revisa el mensaje anterior.
pause
exit /b 1
