#!/usr/bin/env bash
# Sobe o SeaweedFS local com o S3 na porta 8333, escutando so em 127.0.0.1.
# Pelo Bash, e nao pelo PowerShell: o PowerShell quebra o argumento -ip=127.0.0.1.
set -euo pipefail
WEED="${WEED:-/c/Users/gusta/tools/seaweedfs/weed.exe}"
SEAWEED_DADOS="${SEAWEED_DADOS:-/c/Users/gusta/tools/seaweedfs/dados_orquestrador}"
mkdir -p "$SEAWEED_DADOS"
cd "$SEAWEED_DADOS"
exec "$WEED" server -dir="$SEAWEED_DADOS" -ip=127.0.0.1 -s3 -s3.port=8333
