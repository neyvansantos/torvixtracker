@echo off
set /p version="Digite a nova versao (ex: 0.1.2): "
set /p changelog="Digite o que mudou nesta versao: "

echo.
echo Lancando versao %version%...
python release.py %version% "%changelog%"

pause
