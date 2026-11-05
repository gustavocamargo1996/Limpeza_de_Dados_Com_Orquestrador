@echo off
rem Sobe o SeaweedFS local com o S3 na porta 8333, escutando so em 127.0.0.1.
rem E .cmd porque o PowerShell quebra o argumento -ip=127.0.0.1, e o bash dele e o do WSL.
rem WEED: caminho do weed.exe; sem ela, procura no PATH.
rem SEAWEED_DADOS: pasta dos dados; sem ela, var\seaweed dentro do projeto.
if not defined WEED for /f "delims=" %%i in ('where weed 2^>nul') do if not defined WEED set "WEED=%%i"
if not defined WEED (
  echo weed.exe nao encontrado. Baixe o SeaweedFS em https://github.com/seaweedfs/seaweedfs/releases
  echo e ponha o weed.exe no PATH, ou defina WEED com o caminho dele, por exemplo:
  echo   set WEED=C:\ferramentas\seaweedfs\weed.exe
  exit /b 1
)
if not defined SEAWEED_DADOS set "SEAWEED_DADOS=%~dp0var\seaweed"
if not exist "%SEAWEED_DADOS%" mkdir "%SEAWEED_DADOS%"
cd /d "%SEAWEED_DADOS%"
rem -volume.port=9340: a 8080 padrao costuma estar ocupada (por exemplo, pelo Docker).
rem -master.raftHashicorp: o raft padrao entra em panic no Windows ao reabrir o estado
rem ("failed to sync state dir ... Access is denied"), da segunda partida em diante.
"%WEED%" server -dir="%SEAWEED_DADOS%" -ip=127.0.0.1 -s3 -s3.port=8333 -volume.port=9340 -master.raftHashicorp
