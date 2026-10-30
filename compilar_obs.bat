@echo off
setlocal
cd /d "%~dp0"
py -m pip install --upgrade pyinstaller numpy pyaudiowpatch faster-whisper av obsws-python pillow pystray
if errorlevel 1 (echo Falha instalando dependencias & pause & exit /b 1)
py -m PyInstaller --noconfirm --clean --onefile --windowed --name GravadorLegendasOBS --collect-all pyaudiowpatch --collect-all faster_whisper --collect-all ctranslate2 --collect-all av --collect-all pystray gravador_obs_residente.py
if errorlevel 1 (echo Falha compilando & pause & exit /b 1)
echo Executavel: dist\GravadorLegendasOBS.exe
echo Este BAT NAO habilita inicializacao com Windows.
pause
