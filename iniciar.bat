@echo off
setlocal
cd /d "%~dp0"
title Barra de Skills

rem --- 1) Arquivos extraidos? (rodar de dentro do ZIP nao funciona) ---
if exist "skillbar.py" goto achou_arquivos
echo [ERRO] Nao encontrei o skillbar.py nesta pasta.
echo.
echo Provavelmente o iniciar.bat foi aberto de dentro do ZIP.
echo Clique com o botao direito no ZIP, escolha "Extrair tudo..."
echo e rode o iniciar.bat que esta na pasta extraida.
goto fim
:achou_arquivos

rem --- 2) Python instalado? (testa o "py" e depois o "python") ---
set "PY="
py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
if defined PY goto achou_python
python -c "import sys" >nul 2>nul && set "PY=python"
if defined PY goto achou_python
echo [ERRO] Python nao encontrado.
echo.
echo 1. Instale o Python em https://www.python.org/downloads/
echo 2. Na PRIMEIRA tela do instalador, marque "Add python.exe to PATH".
echo 3. Feche esta janela e rode o iniciar.bat de novo.
echo.
echo Se ja instalou sem marcar essa opcao, rode o instalador de novo,
echo escolha "Modify" e marque "Add Python to environment variables".
goto fim
:achou_python

%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if not errorlevel 1 goto versao_ok
echo [ERRO] Seu Python e antigo. Instale o 3.10 ou mais novo:
%PY% --version
echo https://www.python.org/downloads/
goto fim
:versao_ok

rem --- 3) Dependencias instaladas? Se nao, instala sozinho ---
%PY% -c "import tkinter, mss, PIL, numpy, customtkinter" >nul 2>nul
if not errorlevel 1 goto deps_ok
echo Instalando as dependencias, so na primeira vez...
echo.
%PY% -m pip install -r requirements.txt
%PY% -c "import tkinter, mss, PIL, numpy, customtkinter" >nul 2>nul
if not errorlevel 1 goto deps_ok
echo.
echo [ERRO] Nao consegui instalar as dependencias. Veja a mensagem acima.
echo Se falar de "tkinter", reinstale o Python pelo python.org marcando
echo a opcao "tcl/tk and IDLE".
goto fim
:deps_ok

rem --- 4) Inicia ---
echo Iniciando a Barra de Skills... Deixe esta janela aberta.
echo Para fechar o programa: botao direito na barra, "Sair do programa".
echo.
%PY% skillbar.py %*
if not errorlevel 1 goto fim
echo.
echo [ERRO] O programa fechou com erro. Tire um print desta janela
echo e mande para quem te passou o programa.

:fim
echo.
pause
