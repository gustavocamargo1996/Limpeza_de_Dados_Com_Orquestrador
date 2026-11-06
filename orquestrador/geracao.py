"""Roda o gerador em subprocesso e informa a etapa corrente pelo respostas.jsonl."""
import ctypes
import json
import os
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

from orquestrador import config

ETAPA_DO_REGISTRO = {"detector": 4, "especificador": 5, "residual": 5, "codificador": 6}
SUCESSO = "limpador: "
AINDA_ATIVO = 259
# 1601-01-01 em intervalos de 100 ns antes de 1970-01-01, a origem do FILETIME.
EPOCA_DO_WINDOWS = 116444736000000000


def ambiente(reaproveitar=None):
    """O ambiente do filho; com `reaproveitar`, as respostas gravadas e a API viva."""
    env = dict(os.environ)
    if reaproveitar is not None:
        provedor = env.get("PROVEDOR", "openai")
        # A API viva e a que a tela anuncia; PROVEDOR_VIVO so vale com PROVEDOR=gravado.
        vivo = env.get("PROVEDOR_VIVO", "") if provedor == "gravado" else provedor
        env.update(PROVEDOR="reaproveitar", RESPOSTAS_GRAVADAS=str(reaproveitar),
                   PROVEDOR_VIVO=vivo)
    return env


def log(destino):
    """O arquivo em que o filho escreve, ao lado da pasta da versao."""
    return Path(destino).parent / f"{Path(destino).name}.log"


def disparar(sujo, pasta_guia, destino, reaproveitar=None):
    """Sobe o filho que chama gerar_limpador e devolve o Popen."""
    Path(destino).mkdir(parents=True, exist_ok=True)
    argumentos = [config.PYTHON, "-m", "orquestrador.geracao", str(sujo),
                  str(pasta_guia or ""), str(destino)]
    with log(destino).open("w", encoding="utf-8") as saida:
        # Lista de argumentos, sem shell: nada e reinterpretado no caminho.
        # Sessao nova (ignorada no Windows): o encerrar mata o grupo inteiro.
        return subprocess.Popen(argumentos, cwd=config.RAIZ, env=ambiente(reaproveitar),
                                stdout=saida, stderr=subprocess.STDOUT, start_new_session=True)


def _registros(arquivo):
    """Os registros de chamada do respostas.jsonl, sem a origem e sem linha pela metade."""
    if not Path(arquivo).exists():
        return []
    registros = []
    for linha in Path(arquivo).read_text(encoding="utf-8").splitlines():
        try:
            registro = json.loads(linha)
        except json.JSONDecodeError:
            # A ultima linha pode estar sendo escrita pelo filho agora.
            continue
        if "chave" in registro:
            registros.append(registro)
    return registros


def etapa_corrente(destino):
    """A etapa 4, 5 ou 6 pela ultima chamada gravada; 4 enquanto nao ha chamada."""
    registros = _registros(Path(destino) / "respostas.jsonl")
    return ETAPA_DO_REGISTRO.get(registros[-1].get("etapa"), 4) if registros else 4


def chamadas(destino, anterior=None):
    """(total, novas): as chamadas gravadas e as que nao tinham resposta em `anterior`."""
    chaves = [r["chave"] for r in _registros(Path(destino) / "respostas.jsonl")]
    # Falha de rede gravada vai de novo a API viva: conta como chamada nova.
    gravadas = Counter(r["chave"] for r in _registros(anterior)
                       if not r.get("bruto", {}).get("rede")) if anterior else Counter()
    novas = 0
    for chave in chaves:
        if gravadas[chave]:
            gravadas[chave] -= 1
        else:
            novas += 1
    return len(chaves), novas


def _vivo_posix(pid, nascido):
    """No Linux e no macOS, pelo ps: zumbi conta como encerrado, e o etime da a idade."""
    saida = subprocess.run(["ps", "-o", "stat=", "-o", "etime=", "-p", str(pid)],
                           capture_output=True, text=True).stdout.split()
    if len(saida) < 2 or saida[0].startswith("Z"):
        return False
    # etime e [[dd-]hh:]mm:ss, o tempo desde que o processo nasceu.
    dias, _, relogio = saida[1].rpartition("-")
    decorrido = 0
    for parte in relogio.split(":"):
        decorrido = decorrido * 60 + int(parte)
    decorrido += int(dias or 0) * 86400
    return nascido is None or abs(time.time() - decorrido - nascido) < 60


def vivo(pid, nascido=None):
    """O processo `pid` ainda roda e, com `nascido`, foi criado ate um minuto antes ou depois."""
    if os.name != "nt":
        return _vivo_posix(pid, nascido)
    # Nunca os.kill(pid, 0): no Windows o sinal 0 e CTRL_C_EVENT.
    kernel = ctypes.windll.kernel32
    alca = kernel.OpenProcess(0x1000, False, pid)
    if not alca:
        return False
    codigo, tempos = ctypes.c_ulong(), [ctypes.c_ulonglong() for _ in range(4)]
    kernel.GetExitCodeProcess(alca, ctypes.byref(codigo))
    kernel.GetProcessTimes(alca, *(ctypes.byref(t) for t in tempos))
    kernel.CloseHandle(alca)
    # O Windows reaproveita PID: a hora de criacao diz se o processo ainda e o nosso filho.
    criado = (tempos[0].value - EPOCA_DO_WINDOWS) / 1e7
    return codigo.value == AINDA_ATIVO and (nascido is None or abs(criado - nascido) < 60)


def encerrar(pid):
    """Encerra o filho e os processos dele."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        return
    try:
        # O disparar abre sessao nova: o grupo do filho leva junto os processos dele.
        if os.getpgid(pid) == pid:
            os.killpg(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # o processo ja tinha terminado: nada a encerrar


def erro(destino):
    """O fim do log do filho, para o painel e para o erro.log."""
    arquivo = log(destino)
    texto = arquivo.read_text(encoding="utf-8", errors="replace") if arquivo.exists() else ""
    return "\n".join(texto.strip().splitlines()[-40:])


def situacao(destino, pid, nascido=None):
    """`ok` (o filho imprimiu o limpador), `rodando` ou `erro`."""
    arquivo = log(destino)
    texto = arquivo.read_text(encoding="utf-8", errors="replace") if arquivo.exists() else ""
    # O sinal de conclusao vem antes: o filho que ja terminou pode seguir listado.
    if any(linha.startswith(SUCESSO) for linha in texto.splitlines()):
        return "ok"
    return "rodando" if vivo(pid, nascido) else "erro"


if __name__ == "__main__":
    # Unico ponto do orquestrador que importa o gerador, e so dentro do filho.
    from limpeza2.espinha import gerar_limpador

    sujo, guia, destino = sys.argv[1:4]
    print(f"{SUCESSO}{gerar_limpador(Path(sujo), guia or None, Path(destino))}", flush=True)
