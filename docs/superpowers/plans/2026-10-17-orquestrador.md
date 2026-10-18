# Orquestrador: plano de implementação

> **Para quem executa:** este plano é executado em linha (superpowers:executing-plans)
> pela mesma sessão que escreveu a spec, com o usuário ausente. Por isso as tarefas do
> **gerador** trazem o código exato (é onde um erro corrompe o que funciona) e as do
> **orquestrador** trazem as interfaces, o comportamento e os testes que travam cada
> uma; o código delas é escrito na execução, contra esses testes. Passos com `- [ ]`.

**Objetivo:** construir o orquestrador da spec, um invólucro Streamlit em torno do
gerador `limpeza2/`, sem corromper o gerador.

**Arquitetura:** Streamlit nas telas; `fluxo.py` guarda a ordem das etapas e grava cada
transição no SQLite; o gerador e o limpador rodam em subprocesso; artefatos no S3 do
SeaweedFS por `boto3`. O gerador recebe as decisões do usuário por um `decisoes.json`
na pasta do guia e reaproveita respostas gravadas pelo modo `PROVEDOR=reaproveitar`.

**Tecnologia:** Python 3.14, pandas 3, streamlit 1.66, boto3 1.43, moto 5.2 (testes),
sqlite3 da biblioteca padrão.

**Spec:** `docs/superpowers/specs/2026-10-17-orquestrador-design.md`

## Restrições globais

- O gerador continua funcionando sozinho; `.venv/Scripts/python -m pytest` verde ao fim de cada tarefa.
- `tests/test_invariante.py` roda sem alteração depois de cada mudança no gerador.
- Mudanças no gerador são só inserções; nenhuma refatoração para caber no teto. Estouro do teto é aceito e declarado.
- Nenhum teste gasta API; nenhum teste precisa do SeaweedFS no ar. Nenhum run real é disparado.
- Todo teste novo tem prova por mutação: quebrar o código, ver falhar, reverter.
- Português em tudo; sem acento em identificadores e logs; docstring de 1 linha; comentário de no máximo 2 linhas; `try` só com degradação nomeada.
- O orquestrador não importa `limpeza2` (salvo `limpeza2.espinha.gerar_limpador` no filho de `geracao.py`), nem `medir`, nem `preparar_guia`, nem o limpador gerado.
- Dados lidos com `dtype=str, keep_default_na=False, na_values=[]`.
- Trabalho na branch `orquestrador`, commits pequenos; sem merge em `main`.
- Orçamento do orquestrador: 14 arquivos `.py`, 1.400 linhas, maior arquivo 200. Gerador: 16 arquivos, 1.850 linhas.

---

## Parte A: o gerador

### Tarefa 1: branch, dependências e medida do teto

**Arquivos:** `requirements.txt`, `.gitignore`, `CLAUDE.md` §2.

- [ ] `git checkout -b orquestrador`.
- [ ] `requirements.txt`: acrescentar `streamlit>=1.40`, `boto3>=1.34` e, sob o comentário `# so testes`, `moto[s3]>=5.0`.
- [ ] `.gitignore`: acrescentar `var/`.
- [ ] `CLAUDE.md` §2: a medida passa a `git ls-files "limpeza2/*.py" preparar_guia.py medir.py`; teto do gerador 1.850 linhas (decisão de 17/10/2026); orçamento do orquestrador declarado ao lado (14 arquivos, 1.400 linhas, maior 200), medido com `git ls-files "orquestrador/*.py"`.
- [ ] Suíte verde; commit.

### Tarefa 2: `Entrada.decisoes` e a leitura do `decisoes.json`

**Arquivos:** `limpeza2/tipos.py`, `limpeza2/e1_perfil.py`; teste `tests/test_decisoes_gerador.py`.

- [ ] Testes (falham antes):

```python
"""As decisoes do usuario no gerador: leitura, crivo, herdadas, instrucao e reaproveitamento."""
import json
import shutil
from pathlib import Path

import pandas as pd

from limpeza2 import config
from limpeza2.e1_perfil import perfilar
from limpeza2.espinha import gerar_limpador
from tests.test_invariante import FIXTURES, GUIA, PASTA_DO_RUN, SUJO, sem_cr


def guia_com(tmp_path, decisoes):
    """Copia o guia do beers para tmp e grava nele o decisoes.json."""
    pasta = tmp_path / "guia"
    shutil.copytree(GUIA, pasta)
    (pasta / "decisoes.json").write_text(json.dumps(decisoes), encoding="utf-8")
    return pasta


def test_sem_decisoes_json_a_lista_e_vazia():
    assert perfilar(SUJO, GUIA).decisoes == []


def test_le_o_decisoes_json_da_pasta_do_guia(tmp_path):
    d = {"coluna": "ibu", "tipo": "faixa", "parametros": {"minimo": 0, "maximo": 150}, "decisao": "aprovar"}
    entrada = perfilar(SUJO, guia_com(tmp_path, [d]))
    assert entrada.decisao("ibu", "faixa", {"minimo": 0, "maximo": 150}) == d
    assert entrada.decisao("ibu", "faixa", {"minimo": 0, "maximo": 151}) is None


def test_decisoes_vazias_geram_o_mesmo_limpador_e_raciocinio(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROVEDOR", "gravado")
    monkeypatch.setattr(config, "RESPOSTAS_GRAVADAS", str(FIXTURES / "respostas_beers_poc2.jsonl"))
    sem = gerar_limpador(SUJO, GUIA, tmp_path / "a" / PASTA_DO_RUN)
    com = gerar_limpador(SUJO, guia_com(tmp_path, []), tmp_path / "b" / PASTA_DO_RUN)
    assert sem_cr(com) == sem_cr(sem) == sem_cr(FIXTURES / "limpador_beers_poc2.py")
    nome = f"raciocinio_{PASTA_DO_RUN}.md"
    assert sem_cr(com.parent / nome) == sem_cr(sem.parent / nome)
```

- [ ] `tipos.py`: em `Entrada`, depois de `perfil`:

```python
    decisoes: list = field(default_factory=list)

    def decisao(self, coluna, tipo, parametros):
        """A decisao do usuario sobre a regra (coluna, tipo, parametros), ou None."""
        chave = (coluna, tipo, parametros)
        return next((d for d in self.decisoes
                     if (d["coluna"], d["tipo"], d["parametros"]) == chave), None)
```

- [ ] `e1_perfil.py`: `import json`; no `return Entrada(...)` de `perfilar`, acrescentar `decisoes=_ler_decisoes(caminho_guia),`; e a função:

```python
def _ler_decisoes(caminho_guia):
    """As decisoes do usuario no decisoes.json da pasta do guia; sem arquivo, lista vazia."""
    arquivo = Path(caminho_guia) / "decisoes.json" if caminho_guia is not None else None
    if arquivo is None or not arquivo.exists():
        return []
    return json.loads(arquivo.read_text(encoding="utf-8"))
```

- [ ] Mutação: fazer `_ler_decisoes` devolver `[]` sempre → o segundo teste falha; reverter.
- [ ] Suíte inteira verde (inclui invariante); commit.

### Tarefa 3: o crivo honra as decisões

**Arquivo:** `limpeza2/e3_crivo.py`; testes em `tests/test_decisoes_gerador.py`.

- [ ] Testes (com `tests.apoio.monta_entrada` e `Candidata`):
  - `rejeitar` uma candidata que seria aprovada → `metricas["motivo"] == "rejeitada_pelo_usuario"` e fora do retorno de `crivar_deteccao`;
  - `aprovar` uma candidata que marca acima do teto → aprovada;
  - `aprovar` uma candidata que marca célula que o guia mostra correta → continua `marca_celula_correta`;
  - `aprovar` uma `dependencia` com par de `frac_ambiguos` acima do teto → passa de `ambigua`;
  - duas variantes do mesmo `(coluna, tipo)`, a de maior taxa aprovada pelo usuário → ela vence e a outra fica `superada`;
  - `crivar_residual` com decisão `{"tipo": "residual", "parametros": {"sujo": X}, "decisao": "rejeitar"}` → `X` sai do mapa e vai a `caidas` com `rejeitada_pelo_usuario`.
- [ ] Código (só inserções, e as duas condições estendidas):

```python
MOTIVOS = (..., "marca_valor_certificado", "superada", "rejeitada_pelo_usuario")
```

Em `crivar_deteccao`, a comparação passa a
`if anterior is None or _prioridade(candidata) < _prioridade(anterior[0]):`, com

```python
def _prioridade(candidata):
    """A aprovada pelo usuario vence a disputa; entre iguais, vence a de menor taxa."""
    return (candidata.metricas.get("decisao") != "aprovar", candidata.metricas["taxa"])
```

Em `_mascara`, logo depois de montar `candidata.metricas`:

```python
    decisao = entrada.decisao(candidata.coluna, candidata.tipo, candidata.parametros)
    if decisao:
        candidata.metricas["decisao"] = decisao["decisao"]
```

Em `_reprovar`, no início:

```python
    if candidata.metricas.get("decisao") == "rejeitar":
        return "rejeitada_pelo_usuario"
    aprovada = candidata.metricas.get("decisao") == "aprovar"
```

e `if par["frac_ambiguos"] > config.TETO_AMBIGUIDADE and not aprovada:`, e

```python
    if (candidata.tipo != "conformidade" and not aprovada
            and candidata.metricas["taxa"] > candidata.metricas["teto"]):
        return "marca_demais"
```

Em `crivar_residual`, depois do `elif sujo in certificados:` e do seu corpo:

```python
            elif (entrada.decisao(residual.coluna, "residual", {"sujo": sujo}) or {}).get(
                    "decisao") == "rejeitar":
                residual.caidas[sujo] = "rejeitada_pelo_usuario"
```

- [ ] Mutação: tirar `and not aprovada` do `marca_demais` → o teste de aprovar acima do teto falha; trocar `!=` por `==` em `_prioridade` → o de `superada` falha; reverter.
- [ ] Suíte inteira verde (o invariante prova que sem decisão nada mudou); commit.

### Tarefa 4: candidatas herdadas

**Arquivo:** `limpeza2/e2_detector.py`; testes em `tests/test_decisoes_gerador.py`.

- [ ] Testes: `propor` com o roteiro devolvendo `{"regras": []}` e uma decisão `aprovar` de `faixa` em `ibu` → a saída contém uma `Candidata` `faixa` com esses parâmetros e raciocínio que começa por `aprovada pelo usuario`; se o LLM propõe a mesma regra, ela não se duplica; decisão `rejeitar` e decisão de `residual` não viram candidata.
- [ ] Código: `return candidatas` de `propor` passa a `return candidatas + herdadas(entrada, conformes + candidatas)`, e

```python
def herdadas(entrada, propostas):
    """As regras aprovadas pelo usuario que nao foram propostas de novo, como candidatas."""
    ja = [(c.coluna, c.tipo, c.parametros) for c in propostas]
    return [Candidata(coluna=d["coluna"], tipo=d["tipo"], parametros=d["parametros"],
                      raciocinio=f"aprovada pelo usuario na versao {d.get('versao') or '?'}")
            for d in entrada.decisoes
            if d["decisao"] == "aprovar" and d["tipo"] != "residual"
            and (d["coluna"], d["tipo"], d["parametros"]) not in ja]
```

- [ ] Mutação: tirar o filtro `not in ja` → o teste de não duplicar falha; reverter. Suíte verde; commit.

### Tarefa 5: a instrução do usuário no especificador

**Arquivo:** `limpeza2/e4_especificador.py`; testes em `tests/test_decisoes_gerador.py`.

- [ ] Testes: `_conteudo` com decisão que tem `instrucao` → a última linha é `instrucao do usuario, valida desde que reproduza os exemplos do guia: <texto>`; com decisão sem instrução e sem decisão nenhuma → texto idêntico.
- [ ] Código, antes do `return` de `_conteudo`:

```python
    decisao = entrada.decisao(coluna, candidata.tipo, candidata.parametros)
    if decisao and decisao.get("instrucao"):
        linhas.append("instrucao do usuario, valida desde que reproduza os exemplos do guia: "
                      + decisao["instrucao"])
```

- [ ] Mutação: acrescentar a linha sempre → o teste "sem instrução, idêntico" falha (e o invariante também); reverter. Suíte verde; commit.

### Tarefa 6: `PROVEDOR=reaproveitar`

**Arquivos:** `limpeza2/config.py`, `limpeza2/provedor.py`; testes em `tests/test_decisoes_gerador.py`.

- [ ] Testes:
  - com `respostas_beers_poc2.jsonl` e `_api_viva` substituída por um `Roteiro` que conta, a geração do MVP com `reaproveitar` reproduz o limpador byte a byte e o roteiro recebe **zero** pedidos;
  - uma chave ausente vai ao roteiro e a resposta dele entra no `respostas.jsonl`;
  - `PROVEDOR_VIVO="opneai"` levanta `ValueError` com "nao caio para openai";
  - `MODELO` diferente do gravado levanta `ValueError`;
  - o teste antigo de provedor desconhecido continua passando.
- [ ] `config.py`, depois de `RESPOSTAS_GRAVADAS`:

```python
# A API que PROVEDOR=reaproveitar chama para o que nao tem resposta gravada.
PROVEDOR_VIVO = os.getenv("PROVEDOR_VIVO", "")
```

- [ ] `provedor.py`: em `_construir_api`, os dois ramos de rede passam a `if provedor in ("openai", "ollama"): return _api_viva(provedor)`; depois do ramo `gravado`:

```python
    if provedor == "reaproveitar":
        return _Reaproveitar(_Gravado(Path(config.RESPOSTAS_GRAVADAS)),
                             _api_viva(config.PROVEDOR_VIVO.strip().lower()))
```

e

```python
def _api_viva(provedor):
    """A API de rede de `provedor`; so openai e ollama existem."""
    if provedor == "openai":
        return _Api(esforco=config.ESFORCO_RACIOCINIO)
    if provedor == "ollama":
        return _Api(esforco=None, base_url=config.OLLAMA_URL, api_key="ollama")
    raise ValueError(
        f"PROVEDOR_VIVO={provedor!r} nao e suportado. Use openai ou ollama. "
        "Nao caio para openai em silencio: isso mandaria dado para fora da rede."
    )


class _Reaproveitar:
    """Responde do respostas.jsonl gravado e chama a API viva so para o que falta."""

    def __init__(self, gravado, vivo):
        modelo = (gravado.origem or {}).get("modelo")
        if modelo != config.MODELO:
            raise ValueError(f"MODELO={config.MODELO!r} difere do gravado {modelo!r}: "
                             "uma versao com respostas de dois modelos seria inexplicavel")
        self.gravado, self.vivo, self.origem = gravado, vivo, gravado.origem

    def responder(self, chave, instrucao, conteudo, esquema):
        """A resposta gravada desta chamada ou, sem ela, a da API viva."""
        api = self.gravado if self.gravado.fila.get(chave) else self.vivo
        return api.responder(chave, instrucao, conteudo, esquema)
```

- [ ] Mutação: em `responder`, usar sempre `self.vivo` → o teste de zero pedidos falha; reverter. Suíte verde; commit.

### Tarefa 7: ciclo de aperfeiçoamento no gerador e documentos

**Arquivos:** `tests/test_decisoes_gerador.py`, `docs/DECISOES.md`, `CLAUDE.md` §9 e §10.

- [ ] Achar, sem API, uma regra aprovada do MVP cuja rejeição muda o mínimo de prompts:
  gerar com `reaproveitar`, a decisão `rejeitar` e um roteiro vivo que conta; registrar
  quantas chamadas novas cada candidata a teste provoca.
- [ ] Teste: rejeitar essa regra → ela some de `REGRAS` do limpador gerado, aparece no
  raciocínio com `motivo: rejeitada_pelo_usuario`, e o roteiro vivo recebe exatamente o
  número de pedidos medido (o número é assinatura do comportamento, como no invariante).
- [ ] Teste: uma decisão `aprovar` com instrução para uma regra aprovada leva o
  especificador dela a uma chamada nova (o prompt mudou), e só ela.
- [ ] `docs/DECISOES.md`: âncoras `#decisoes-do-usuario` (formato, chave por igualdade,
  dois valores, o que o crivo faz com cada um, por que aprovar não dispensa o guia,
  rejeitar a vencedora deixa a próxima variante vencer) e `#reaproveitar` (por que o
  ciclo reaproveita, a trava do modelo, a trava do `PROVEDOR_VIVO`).
- [ ] `CLAUDE.md` §9: o `decisoes.json` na pasta do guia e o modo `reaproveitar`; §10:
  `orquestrador/` e a fronteira. Medir o teto do gerador e declarar o resultado.
- [ ] Suíte verde; commit.

## Parte B: o orquestrador

Todos os módulos em `orquestrador/` (pacote de namespace, sem `__init__.py`). Testes em
`tests/orquestrador/` com um `conftest.py` que: aponta `config.SQLITE` e
`config.TRABALHO` para `tmp_path`; liga `moto` (`mock_aws`) com
`MOTO_S3_CUSTOM_ENDPOINTS=http://127.0.0.1:8333`; e oferece a fixture `lago_falso`.

### Tarefa 8: `config.py` e `controle.py`

**Interfaces produzidas:**

- `config`: `RAIZ`, `S3_ENDPOINT`, `S3_BUCKET`, `SQLITE`, `TRABALHO`, `PYTHON` (=`sys.executable`), `PROVEDOR`, `MODELO`, `LER_CSV`, `DOMINIOS`, `LINHAS_GUIA_PADRAO=20`, `LINHAS_GUIA_MINIMO=10`, `AMOSTRA_PADRAO=300`, `AMOSTRA_MINIMO=100`, `REGIME_TESTADO=300`, `SEMENTE=20261017`, `TIMEOUT_GERACAO=1800`, `TIMEOUT_APLICACAO=600`, `CELULAS_POR_REGRA=5`.
- `controle`: `ETAPAS` (10 tuplas), `ANDAMENTO`, `SUCESSO`, `ERRO`; `agora()`; `conectar(caminho=None) -> sqlite3.Connection` (cria as tabelas da spec §4 mais `CONTEXTOS(ID_PROCESSO, CONTEXTO, ENCERRADO)`, povoa `ETAPAS`, `row_factory=sqlite3.Row`, `check_same_thread=False`, autocommit); `abrir_processo(con, contexto) -> int`; `contexto(con, p) -> dict`; `atualizar_contexto(con, p, **campos) -> dict`; `processo_aberto(con) -> int|None`; `encerrar_processo(con, p)`; `iniciar_etapa(con, p, etapa, pid=None, detalhe="") -> dict` (fecha a aberta com sucesso; devolve o contexto); `concluir_etapa(con, p, status, detalhe=None)`; `marcar(con, p, detalhe)`; `etapa_atual(con, p) -> dict|None`; `etapas(con, p) -> list[dict]`; `buscar_esquema(con, dominio, campos) -> dict|None`; `esquema_por_diretorio(con, diretorio)`; `criar_esquema(con, dominio, nome, campos, diretorio) -> int`; `registrar_limpador(con, dominio, nome, diretorio, origem) -> int`; `mudar_status(con, id_limpador, status)`; `limpador_aprovado(con, dominio, nome) -> dict|None`; `dado_existente(con, dominio, nome, hash)`; `registrar_dado(con, hash, dominio, nome, diretorio) -> int`; `concluir_dado(con, id_dado, diretorio_corrigido, limpador)`.

- [ ] Testes `tests/orquestrador/test_controle.py`: as cinco tabelas da spec com os campos dela; etapas povoadas; `iniciar_etapa` fecha a anterior com sucesso e tempo; esquema achado pelo conjunto de colunas em qualquer ordem e só no mesmo domínio; `limpador_aprovado` devolve o mais recente aprovado, ignorando pendente e reprovado; conexão nova enxerga o estado (F5).
- [ ] Implementar; mutações (ordenar campos ao gravar mas não ao buscar; não fechar a etapa anterior); commit.

### Tarefa 9: `lago.py` e `subir_seaweed.sh`

**Interfaces:** `cliente()`; `disponivel() -> bool` (cria o bucket no primeiro uso; `BotoCoreError`/`ClientError` → `False`); `nome_de_pasta(texto) -> str`; `prefixo(dominio, esquema, area, carimbo) -> str`; `enviar(local, chave, metadados=None)` (`put_object` com os bytes); `enviar_pasta(pasta, prefixo, nomes=None) -> list[str]`; `baixar_pasta(prefixo, pasta) -> Path`; `listar(prefixo) -> list[str]`; `metadados(chave) -> dict`.

- [ ] Testes `tests/orquestrador/test_lago.py` (moto): `nome_de_pasta("Meio Ambiente")=="Meio_Ambiente"` e `"Saúde"→"Saude"`; enviar e listar no layout `<Dominio>/<Esquema>/Original/<carimbo>/dados.csv`; sha256 na metadado; baixar a pasta devolve os mesmos bytes; `disponivel()` falso com endpoint fechado (`http://127.0.0.1:9`, sem moto).
- [ ] `subir_seaweed.sh`: `"$WEED" server -dir="$SEAWEED_DADOS" -ip=127.0.0.1 -s3 -s3.port=8333`, com `WEED` padrão `/c/Users/gusta/tools/seaweedfs/weed.exe` e `SEAWEED_DADOS` padrão `/c/Users/gusta/tools/seaweedfs/dados_orquestrador`, criando a pasta.
- [ ] Implementar; mutação; commit.

### Tarefa 10: `amostra.py`

**Interfaces:** `COLUNAS_PARES`; `sortear(n_total, n, semente) -> dict` (`{"semente","n_total","linhas","trocas"}`, as `n` primeiras de uma permutação `numpy.random.default_rng(semente)`); `trocar(sorteio, posicao) -> dict` (a próxima livre da mesma permutação; registra `{"posicao","saiu","entrou"}`); `template(sujo, sorteio) -> DataFrame` (`_linha` + colunas, na ordem do sorteio); `divergencias(guia, sujo, sorteio) -> list[str]`; `completar_pares(pares, sujo) -> (DataFrame, list[str])`; `gravar_guia(pasta, guia, pares, sujo, sorteio)` (os quatro arquivos, **preservando a ordem das linhas**); `linhas_sujas(pasta_guia) -> DataFrame` (indexado por `_linha`); `montar_entrada(sujo, pasta_guia, destino, base, tamanho, semente, antigas=None) -> dict` (grava `destino/sujo.csv` e `destino/guia/` renumerado, copia `decisoes.json` se houver; devolve `{"base","tamanho","semente","origem"}`).

- [ ] Testes `tests/orquestrador/test_amostra.py`: mesma semente, mesmo sorteio; `trocar` não repete linha e registra; template devolvido com `_linha` alterada → divergência; par com linha inexistente → problema; `sujo` do par preenchido pela célula; amostra contém todas as linhas do guia e dos pares; base `inteira` → `sujo.csv` lido é igual ao original e o guia renumerado é igual ao original (identidade); esquema conhecido (`antigas`) → as primeiras linhas da entrada são as antigas e `_linha`/`linha` do guia apontam para elas, célula por célula.
- [ ] Implementar; mutações (esquecer de renumerar `pares["linha"]`; sortear sem semente); commit.

### Tarefa 11: `geracao.py`

**Interfaces:** `ETAPA_DO_REGISTRO`; `disparar(sujo, pasta_guia, destino, reaproveitar=None) -> Popen` (ambiente do pai; com `reaproveitar`, `PROVEDOR=reaproveitar`, `RESPOSTAS_GRAVADAS`, `PROVEDOR_VIVO = PROVEDOR_VIVO do ambiente ou PROVEDOR`; log em `destino.parent/<destino.name>.log`; argumentos em lista, `cwd=RAIZ`); `etapa_corrente(destino) -> int`; `chamadas(destino, anterior=None) -> (total, novas)` (multiconjunto de chaves); `situacao(destino, pid) -> "rodando"|"ok"|"erro"` (`ok` quando o log tem a linha `limpador: `); `vivo(pid) -> bool` (Windows: `OpenProcess` + `GetExitCodeProcess == 259`; nunca `os.kill(pid, 0)`, que no Windows manda CTRL_C); `encerrar(pid)` (`taskkill /F /T /PID`); `erro(destino) -> str` (fim do log); `__main__` importa `gerar_limpador` e o chama.

- [ ] Testes `tests/orquestrador/test_geracao.py`: `etapa_corrente` sem arquivo → 4; com `detector`/`especificador`/`residual`/`codificador` → 4/5/5/6; linha final pela metade é ignorada; `chamadas` com repetidas; `vivo` do próprio processo é verdadeiro e de um filho encerrado é falso; um `disparar` real com `PROVEDOR=gravado` e as respostas do MVP termina com `situacao == "ok"` e limpador byte a byte igual à fixture.
- [ ] Implementar; mutações; commit.

### Tarefa 12: `relatorio_geracao.py`

**Interfaces:** `CONTRADIZ` (os seis motivos da spec §9.2); `ler(caminho) -> dict` (`{"cabecalho": {...}, "colunas": {coluna: {"candidatas": [{"tipo","motivo","parametros","raciocinio","metricas","reparo","raciocinio_reparo"}], "residual": {"mapa": [(sujo, limpo, justificativa)], "caidas": [(sujo, motivo)]}, "registro": [str]}}}`; ignora blocos de código; `parametros` por `ast.literal_eval`); `descrever(candidata) -> str`; `justificar(candidata) -> str`; `montar(raciocinio, parametros, sorteio, chamadas, truncada) -> str`.

- [ ] Testes `tests/orquestrador/test_relatorio_geracao.py`: contrato sobre o raciocínio do MVP em `docs/evidencia/parte-2/run-beers_2026-10-12_2152/` — 11 colunas; número de candidatas igual ao de cabeçalhos `### tipo: motivo` (contados por regex no teste); contagem por motivo igual à contada no arquivo; `ounces` tem residual `8.4 ounce -> 8.4`; `state` tem caída `''` com motivo `conflitante`; os parâmetros de `abv` são `{'padroes': ['9.9']}`. `montar` destaca as que contradizem o guia, mostra base e trocas.
- [ ] Implementar; mutação (não pular bloco de código); commit.

### Tarefa 13: `decisoes.py`

**Interfaces:** `APROVAVEIS = {"marca_demais","superada","ambigua"}`; `TENTAVEIS = {"sem_especificacao","especificacao_invalida","codigo_rejeitado","lancou"}`; `opcoes(candidata) -> list[str]` (`rejeitar`, `tentar`, `aprovar`, `desfazer`); `decidir(candidata, coluna, escolha, instrucao, versao) -> dict` (levanta `ValueError` fora de `opcoes`, e para `tentar` sem instrução); `decidir_residual(coluna, sujo, versao) -> dict`; `chave(decisao) -> tuple`; `acumular(anteriores, novas, regras=None, versao=None) -> list` (anteriores, herdadas de `REGRAS` com `origem: herdada`, novas por cima; `desfazer` remove); `ler(pasta) -> list`; `gravar(pasta, decisoes)`.

- [ ] Testes: cada motivo de `CONTRADIZ` não tem opção e `decidir` levanta; `vacua` sem opção; `marca_demais` → `aprovar`; aprovada com reparo `codigo_rejeitado` → `rejeitar` e `tentar`; `acumular` herda as `REGRAS` e a decisão nova vence a herdada da mesma chave; `desfazer` remove.
- [ ] Implementar; mutação; commit.

### Tarefa 14: `relatorio_limpeza.py`

**Interfaces:** `aplicar(limpador, entrada, pasta) -> dict` (filho `python -m orquestrador.relatorio_limpeza limpador entrada pasta`, que importa o limpador, roda `aplicar_detalhado` e grava `dados.csv`, `flags.csv`, `fontes.csv`, `regras.json` com `REGRAS`, `RESIDUAL`, `GERACAO_TRUNCADA`; o pai lê tudo; código de saída diferente de 0 → `RuntimeError` com o stderr); `resumir(aplicacao) -> dict`; `montar(resumo, versao) -> str`.

- [ ] Testes: com a fixture `limpador_beers_poc2.py` e `beers_dirty_300.csv`, as células alteradas por regra batem com `fontes` calculado no próprio teste, importando a fixture; a amostra tem no máximo 5 por regra, com antes ≠ depois; flags por coluna batem; limpador que lança → `RuntimeError`.
- [ ] Implementar; mutação; commit.

### Tarefa 15: `fluxo.py` e os testes ponta a ponta

**Interfaces:** `carimbo()` (substituível); `iniciar(con, conteudo, nome_arquivo, dominio) -> int`; `nomear(con, p, nome)`; `ressortear(con, p, n)`; `trocar_linha(con, p, posicao)`; `confirmar_guia(con, p, guia, pares)`; `gerar(con, p, base, tamanho, decisoes=None, reaproveitar=None)`; `acompanhar(con, p) -> int`; `aprovar(con, p)`; `aperfeicoar(con, p, novas)`; `nova_versao(con, p, base, tamanho)`; `tentar_de_novo(con, p)`; `cancelar(con, p)`; `sujo_de(contexto) -> DataFrame`; `ESPERA_NOME`, `ESPERA_PARAMETROS`.

- [ ] Testes `tests/orquestrador/test_fluxo.py` (moto, `PROVEDOR=gravado` no ambiente do filho, `carimbo` fixo em `2026-10-12_2152`, `amostra.sortear` devolvendo as linhas do guia do MVP):
  - **esquema novo, ponta a ponta:** `iniciar` → `ESPERA_NOME` → `nomear("beers")` → etapa 3 → `confirmar_guia` com o guia do MVP → `gerar("inteira", 300)` → `acompanhar` até 9 → o `limpador_beers_2026-10-12_2152.py` baixado do lago é byte a byte a fixture; o SQLite tem as etapas 1 a 9 com sucesso; limpador `pendente`; `aprovar` → `Corrigido/` com `dados.csv`, `flags.csv`, `relatorio_limpeza.md`, limpador `aprovado`, `DADOS` preenchido, processo encerrado;
  - **aperfeiçoamento:** depois do 9, `aperfeicoar` rejeitando a regra da tarefa 7, com `PROVEDOR_VIVO=openai`, `OPENAI_API_KEY` falsa e `OPENAI_BASE_URL=http://127.0.0.1:9/v1` (porta fechada: nenhum dado sai da máquina) → versão nova sem a regra, chamadas novas iguais às da tarefa 7, versão anterior `reprovado`;
  - **esquema conhecido:** depois de aprovado, `iniciar` com o mesmo CSV → aviso de extração repetida, etapas 1, 2, 8 e espera em 9 com o limpador aprovado aplicado, sem gerar;
  - **erro:** filho que falha (pasta do guia inexistente) → etapa `concluido com erro` e `erro.log` no lago; `PID` morto sem a linha `limpador:` → "interrompido";
  - **truncada:** `aprovar` com `truncada` verdadeira levanta.
- [ ] Implementar; se `fluxo.py` passar de 200 linhas, simplificar; se não bastar, separar pela função (as etapas automáticas num módulo próprio), nunca pelo tamanho, e declarar.
- [ ] Mutações; commit.

### Tarefa 16: as telas

**Arquivos:** `orquestrador/app.py`, `tela_ingestao.py`, `tela_guia.py`, `tela_painel.py`, `tela_resultado.py`.

- `app.py`: título; aviso e `st.stop()` se `lago.disponivel()` falso; barra lateral com as etapas do processo e "Cancelar processo"; roteia pela última etapa: nenhum processo → ingestão; 1 com `ESPERA_NOME` → nome; 3 → guia (com `ESPERA_PARAMETROS`, o quadro de parâmetros); 4–6 ou erro em 4–7 → painel; 8–9 → resultado.
- `tela_ingestao.py`: `st.file_uploader` CSV, `st.selectbox` de domínio, botão "Ingerir"; tela do nome do esquema novo.
- `tela_guia.py`: número de linhas (mínimo 10), abas Formulário (`st.data_editor` com `_linha` travada; "Sortear de novo" por linha; grade de pares) e Template (download e upload); `parametros(n_total, chave) -> (base, tamanho) | None` com o aviso de regime e o aviso do provedor.
- `tela_painel.py`: `st.fragment(run_every=1)` chamando `fluxo.acompanhar`; `st.status`; etapas 4–6 com marca; cronômetro; chamadas totais e novas; erro com "Tentar de novo".
- `tela_resultado.py`: abas Relatório de geração, Relatório de limpeza e Decisão; aprovar (bloqueado se truncada); aperfeiçoar com as opções de `decisoes.opcoes` por candidata e instrução; esquema conhecido: "Gerar nova versão" com o quadro de parâmetros.
- [ ] Testes `tests/orquestrador/test_telas.py` com `streamlit.testing.v1.AppTest`: sem processo → cabeçalho de ingestão; bucket fora → aviso; processo na etapa 3 → `data_editor` presente; processo na 9 (do teste ponta a ponta, em fixture de módulo) → três abas e botão de aprovar.
- [ ] Rodar `streamlit run orquestrador/app.py` com `PROVEDOR=gravado` e o SeaweedFS de `subir_seaweed.sh`, e percorrer o MVP de verdade na interface (sem API). Registrar o que for achado.
- [ ] Commit.

### Tarefa 17: fronteira, documentos e fechamento

- [ ] `tests/orquestrador/test_fronteira.py`: AST de cada `orquestrador/*.py`; nenhum import de `limpeza2` exceto `limpeza2.espinha` em `geracao.py`; nenhum de `medir`, `preparar_guia`; prova por mutação.
- [ ] `CLAUDE.md`: seção do orquestrador (árvore, orçamento medido, fronteira, como rodar); `docs/CONTINUACAO.md`: estado; `README` de execução dentro do `CLAUDE.md` ou do `CONTINUACAO.md` (sem arquivo novo de documentação se não for preciso).
- [ ] Medir os dois tetos e declarar; suíte inteira verde; revisão de código por subagente sobre o diff da branch; corrigir o que for real; commit.
