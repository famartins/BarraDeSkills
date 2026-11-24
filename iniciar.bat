@echo off
setlocal
cd /d "%~dp0"
title Barra de Skills
rem Tudo o que acontece fica registrado em diagnostico.txt (mande esse arquivo
rem para quem te passou o programa se algo der errado).
set "LOG=%~dp0diagnostico.txt"
set "BARRA_LOG=%LOG%"
> "%LOG%" echo Barra de Skills - diagnostico
>> "%LOG%" echo Data: %date% %time%
>> "%LOG%" echo Pasta: %CD%
ver >> "%LOG%"

rem --- 1) Arquivos extraidos? (rodar de dentro do ZIP nao funciona) ---
if exist "skillbar.py" goto achou_arquivos
call :erro "Nao encontrei o skillbar.py nesta pasta."
echo.
echo Provavelmente o iniciar.bat foi aberto de dentro do ZIP.
echo Clique com o botao direito no ZIP, escolha "Extrair tudo..."
echo e rode o iniciar.bat que esta na pasta extraida.
goto fim
:achou_arquivos

rem --- 2) Python instalado? (testa o "py" e depois o "python") ---
>> "%LOG%" echo.
>> "%LOG%" echo [where py / where python]
where py >> "%LOG%" 2>&1
where python >> "%LOG%" 2>&1
set "PY="
py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
if defined PY goto achou_python
python -c "import sys" >nul 2>nul && set "PY=python"
if defined PY goto achou_python
call :erro "Python nao encontrado."
echo.
echo 1. Instale o Python em https://www.python.org/downloads/
echo 2. Na PRIMEIRA tela do instalador, marque "Add python.exe to PATH".
echo 3. Feche esta janela e rode o iniciar.bat de novo.
echo.
echo Se ja instalou sem marcar essa opcao, rode o instalador de novo,
echo escolha "Modify" e marque "Add Python to environment variables".
goto fim
:achou_python
>> "%LOG%" echo Usando: %PY%
%PY% -c "import sys; print(sys.executable); print(sys.version)" >> "%LOG%" 2>&1

%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if not errorlevel 1 goto versao_ok
call :erro "Seu Python e antigo. Instale o 3.10 ou mais novo."
%PY% --version
echo https://www.python.org/downloads/
goto fim
:versao_ok

rem --- 3) Dependencias instaladas? Se nao, instala sozinho ---
>> "%LOG%" echo.
>> "%LOG%" echo [dependencias]
%PY% -c "import tkinter, mss, PIL, numpy, customtkinter, pystray" >> "%LOG%" 2>&1
if not errorlevel 1 goto deps_ok
echo Instalando as dependencias, so na primeira vez (pode levar 1 ou 2 minutos)...
echo.
>> "%LOG%" echo [pip install]
%PY% -m pip install -r requirements.txt >> "%LOG%" 2>&1
%PY% -c "import tkinter, mss, PIL, numpy, customtkinter, pystray" >> "%LOG%" 2>&1
if not errorlevel 1 goto deps_ok
call :erro "Nao consegui instalar as dependencias."
echo Detalhes no arquivo diagnostico.txt, nesta pasta.
echo Se falar de "tkinter", reinstale o Python pelo python.org marcando
echo a opcao "tcl/tk and IDLE".
goto fim
:deps_ok
>> "%LOG%" echo dependencias OK

rem --- 4) Inicia ---
echo Iniciando a Barra de Skills... Deixe esta janela aberta.
echo Na primeira vez abre uma janela para escolher a vocacao.
echo Para fechar o programa: botao direito na barra, "Sair do programa".
echo.
>> "%LOG%" echo.
>> "%LOG%" echo [programa]
%PY% skillbar.py %*
set "CODIGO=%errorlevel%"
>> "%LOG%" echo Programa terminou com codigo %CODIGO%
if "%CODIGO%"=="0" goto fim
echo.
call :erro "O programa fechou com erro (codigo %CODIGO%)."
echo Mande o arquivo diagnostico.txt, que esta nesta pasta,
echo para quem te passou o programa.

:fim
echo.
pause
exit /b

:erro
echo [ERRO] %~1
>> "%LOG%" echo [ERRO] %~1
exit /b
