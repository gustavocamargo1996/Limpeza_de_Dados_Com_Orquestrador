@echo off
rem Sobe o SeaweedFS local com o S3 na porta 8333, escutando so em 127.0.0.1.
rem E .cmd porque o PowerShell quebra o argumento -ip=127.0.0.1, e o bash dele e o do WSL.
if not defined WEED set "WEED=C:\Users\gusta\tools\seaweedfs\weed.exe"
if not defined SEAWEED_DADOS set "SEAWEED_DADOS=C:\Users\gusta\tools\seaweedfs\dados_orquestrador"
if not exist "%SEAWEED_DADOS%" mkdir "%SEAWEED_DADOS%"
cd /d "%SEAWEED_DADOS%"
rem -volume.port=9340: a 8080 padrao costuma estar com o Docker (Airflow) nesta maquina.
rem -master.raftHashicorp: o raft padrao entra em panic no Windows ao reabrir o estado
rem ("failed to sync state dir ... Access is denied"), da segunda partida em diante.
"%WEED%" server -dir="%SEAWEED_DADOS%" -ip=127.0.0.1 -s3 -s3.port=8333 -volume.port=9340 -master.raftHashicorp
