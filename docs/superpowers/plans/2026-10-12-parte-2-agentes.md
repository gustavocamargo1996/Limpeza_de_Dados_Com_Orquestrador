# Parte 2: agentes, espinha e limpador gerado — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Acoplar à fundação determinística os três agentes (detector, especificador, codificador), a rodada residual e a espinha, de modo que `gerar_limpador` produza um limpador autônomo que o `medir.py` mede executando-o.

**Architecture:** Doze tarefas. As onze primeiras não gastam API: os agentes falam com um dublê do provedor. O laço que combina regras vira `motor.aplicar_regras`, única implementação, usada pelo residual e embutida byte a byte no limpador. A tarefa 12 é o primeiro run pago, em degraus, cada um anunciado e aprovado pelo usuário antes.

**Tech Stack:** Python 3.14, pandas 3.0, SDK `openai` 3.29 (exceções sobre `httpx2`), pytest, uv.

**Spec:** [`docs/superpowers/specs/2026-10-12-parte-2-agentes-design.md`](../specs/2026-10-12-parte-2-agentes-design.md), que complementa [`2026-10-11-geracao-de-limpador-design.md`](../specs/2026-10-11-geracao-de-limpador-design.md). Leia as duas. Decisões com âncoras: [`docs/DECISOES.md`](../../DECISOES.md).

## Global Constraints

Valores copiados do `CLAUDE.md` e da spec. Valem em toda tarefa.

- **Idioma:** português do Brasil em identificadores, docstrings, comentários, logs, documentos, commits e respostas. Exceções: nomes de bibliotecas e colunas dos datasets.
- **Sem acento em identificadores e em strings de log** (stdout do Windows em cp1252). Documentos usam acentuação normal.
- **Docstring de 1 linha.** O raciocínio longo vai para `docs/DECISOES.md`, e o código guarda a âncora.
- **Comentário inline: no máximo 2 linhas**, descrevendo a mecânica. Sem histórico, medição, comparação ou planos.
- **Exceção só com degradação nomeada.** Cada agente tem uma fronteira por unidade (`except FalhaDoLLM`); erro fora disso é bug e propaga.
- **Teto de tamanho:** 16 arquivos `.py` fora de `tests/` (16 de 16 ao fim deste plano, folga zero); 1.800 linhas; 200 no maior arquivo. Todo arquivo cabe numa frase sem "e". **Nunca fracione para caber no teto de linhas;** estourou, simplifique.
- **Medir antes de todo commit que acrescenta código:** `git ls-files "*.py" ":!tests/" | wc -l` e `git ls-files "*.py" ":!tests/" | xargs wc -l | sort -n | tail -4`.
- **Carga de CSV sempre literal:** `pd.read_csv(p, dtype=str, keep_default_na=False, na_values=[])` (`config.LER_CSV`).
- **Nenhum teste gasta API.** Os agentes falam com o dublê `Roteiro` de `tests/apoio.py`.
- **Todo teste novo vem com prova por mutação:** o plano dá a mutação; aplique, veja falhar, reverta, e registre no commit que foi executada.
- **O CSV limpo só é aberto por `preparar_guia.py` e `medir.py`**, fora de `limpeza2/`.
- **Python:** `.venv/Scripts/python`. Dependências com `uv pip install -r requirements.txt`.
- **`../POC_Limpeza_de_Dados/` é somente leitura.**
- **Run pago é decisão do usuário, anunciada antes.** Só a tarefa 12 gasta API.
- **Modelo:** `gpt-6-luna`, `reasoning_effort="none"`, `temperature=0`, `seed=config.SEMENTE`.

## Estrutura de arquivos

| Arquivo | Frase | Tarefas |
|---|---|---|
| `limpeza2/__init__.py` | **apagado**: a vaga do 16º arquivo | 0 |
| `limpeza2/motor.py` | única implementação de aplicação de regra | 1 |
| `limpeza2/tipos.py` | o que viaja entre as etapas, até o limpador gerado | 2 |
| `limpeza2/limites.py` | calcula os limites que o guia sustenta para uma coluna | 2 |
| `limpeza2/e3_crivo.py` | etapa 3: reprova a regra candidata que não se sustenta | 2 |
| `limpeza2/config.py` | caminhos, limiares, semente e modelo | 3 |
| `limpeza2/provedor.py` | entrega o cliente do provedor de LLM escolhido | 3 |
| `limpeza2/e1_perfil.py` | etapa 1: perfila a tabela suja | 4 |
| `limpeza2/e2_detector.py` | etapa 2: agente detector -> predicados candidatos | 4 |
| `limpeza2/e4_especificador.py` | etapa 4: agente especificador -> JSON de reparo | 5 |
| `limpeza2/e6_codificador.py` | etapa 6: agente codificador -> escreve os artefatos de saída | 6 e 8 |
| `limpeza2/e5_residual.py` | etapa 5: rodada residual por entidade -> dicionário | 7 |
| `medir.py` | executa o limpador gerado e mede | 8 |
| `limpeza2/espinha.py` | a ordem das etapas, e nada mais | 9 |
| `tests/apoio.py` | entrada montada à mão e o dublê do provedor (fora do teto) | 3 |

Orçamento (spec §10): ~1.770 linhas ao fim. `motor`, `e3_crivo` e `e6` fecham perto de 200.

---

## Task 0: A vaga do 16º arquivo

**Files:**
- Delete: `limpeza2/__init__.py`
- Modify: `CLAUDE.md` (§2, parágrafo "Reserva conhecida"; §9, parágrafo "Quinze arquivos")

**Interfaces:** nenhuma.

- [ ] **Step 1: Confirmar que o arquivo está vazio**

Run: `wc -c limpeza2/__init__.py`
Expected: `0 limpeza2/__init__.py`

- [ ] **Step 2: Apagar e rodar a suíte**

```bash
git rm limpeza2/__init__.py
.venv/Scripts/python -m pytest
```
Expected: `187 passed`.

- [ ] **Step 3: Corrigir o `CLAUDE.md`**

No §2, troque o parágrafo que começa com "**Reserva conhecida:**" por:

```markdown
**A reserva foi usada.** `limpeza2/__init__.py` estava vazio e foi apagado na
parte 2 (12/10/2026), abrindo a vaga do 16º arquivo. O projeto fecha em 16 de 16,
sem folga.
```

No §9, troque o parágrafo que começa com "Quinze arquivos, cada um com uma função" por:

```markdown
Dezesseis arquivos, cada um com uma função que cabe numa frase. É o teto da
seção 2, e não resta folga: a vaga do 16º veio do `limpeza2/__init__.py`, que
estava vazio e foi apagado. Se `e6_codificador.py`, `motor.py` ou `e3_crivo.py`
passarem de 200 linhas, a saída é simplificar, nunca fracionar.
```

- [ ] **Step 4: Medir e commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l     # 10
git add -A limpeza2/__init__.py CLAUDE.md
git commit -m "Apaga limpeza2/__init__.py: a vaga do 16o arquivo

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 1: `motor.py` — simplificar `reparar` e acrescentar `aplicar_regras`

**Files:**
- Modify: `limpeza2/motor.py` (a função `reparar` inteira; nova `_escalar`; nova `aplicar_regras` no fim)
- Test: `tests/test_motor_reparo.py` (um teste novo), `tests/test_motor_aplicar.py` (novo)

**Interfaces:**
- Consumes: `detectar`, `_mais_proximo`, `_reparar_por_moda` (já em `motor.py`).
- Produces: `aplicar_regras(df, regras, residual, funcoes, dominancia=0.70) -> (df, flags, fontes)`, em que `regras` é uma lista de dicts `{"coluna", "tipo", "deteccao", "estrategia", "reparo"}` (`estrategia` e `reparo` podem ser `None`), `residual` é `{coluna: {sujo: limpo}}`, `flags` é um DataFrame booleano e `fontes` um DataFrame de strings (`""` onde nada escreveu; `"<tipo>/<estrategia>"` ou `"residual"` onde escreveu).

- [ ] **Step 1: Teste do caso de borda que muda de propósito**

Acrescente ao fim de `tests/test_motor_reparo.py`:

```python
def test_reparada_so_conta_valor_que_mudou(tabela):
    # Ver docs/DECISOES.md#reparada-e-mudanca: dicionario {v: v} nao repara nada.
    m = verdadeiro_em(tabela, [0])
    novo, reparada = reparar(tabela, "cidade", "dicionario", {"mapa": {"Boston": "Boston"}}, m)
    assert not reparada.any()
    assert novo.equals(tabela)
```

Run: `.venv/Scripts/python -m pytest tests/test_motor_reparo.py::test_reparada_so_conta_valor_que_mudou -v`
Expected: FAIL (`assert not True`): hoje o `dicionario` marca `reparada` sem olhar se mudou.

- [ ] **Step 2: Simplificar `reparar`**

Em `limpeza2/motor.py`, substitua a função `reparar` inteira (de `def reparar(` até o `raise ValueError(f"estrategia de reparo desconhecida: {estrategia}")` dela) por:

```python
def reparar(df, coluna, estrategia, parametros, mascara, funcoes=None, dominancia=0.70):
    """Aplica a estrategia onde a mascara e True; devolve (df novo, mascara do que mudou)."""
    novo = df.copy()
    reparada = pd.Series(False, index=df.index)
    alvos = df.index[mascara.fillna(False)]
    if estrategia == "moda_condicionada":
        return _reparar_por_moda(
            novo, df, coluna, parametros["determinantes"], alvos, dominancia, reparada
        )
    escalar = _escalar(estrategia, parametros, funcoes)
    for linha in alvos:
        antes = str(df.at[linha, coluna])
        depois = escalar(antes)
        # None e "nao sei reparar"; devolver o mesmo valor nao conta como reparo.
        if depois is not None and depois != antes:
            novo.at[linha, coluna] = depois
            reparada.loc[linha] = True
    return novo, reparada


def _escalar(estrategia, parametros, funcoes):
    """A funcao valor -> valor novo, ou None para nao reparar, de cada estrategia escalar."""
    if estrategia == "normalizar":
        return (funcoes or {})[parametros["funcao"]]
    if estrategia == "vizinho_no_dominio":
        return lambda v: _mais_proximo(v, parametros["dominio"], parametros["distancia"])
    if estrategia == "dicionario":
        return parametros["mapa"].get
    if estrategia == "esvaziar":
        return lambda v: ""
    raise ValueError(f"estrategia de reparo desconhecida: {estrategia}")
```

- [ ] **Step 3: A suíte inteira passa**

Run: `.venv/Scripts/python -m pytest`
Expected: `188 passed`. Se algum teste antigo falhar, **pare e reporte**: a simplificação só pode mudar o caso de borda do Step 1.

- [ ] **Step 4: Testes de `aplicar_regras`**

Crie `tests/test_motor_aplicar.py`:

```python
"""O laco que combina as regras: le sempre o original, primeiro a escrever vence."""
import pandas as pd

from limpeza2.motor import aplicar_regras


def regra(coluna, tipo, deteccao, estrategia=None, reparo=None):
    return {"coluna": coluna, "tipo": tipo, "deteccao": deteccao,
            "estrategia": estrategia, "reparo": reparo}


def cidades():
    return pd.DataFrame({"cidade": ["Boston", "Boston", "Boston", "Bostn"],
                         "estado": ["MA", "MA", "MA", "XX"]})


def oncas():
    return pd.DataFrame({"onca": ["12", "12 oz", "16", "N/A", "16"]})


def test_detecta_no_original_e_nao_no_que_outra_regra_escreveu():
    # Lendo o original, "Bostn" e grupo de uma linha so, e a dependencia nao marca nada.
    regras = [
        regra("cidade", "dominio", {"valores": ["Boston"]}, "dicionario", {"mapa": {"Bostn": "Boston"}}),
        regra("estado", "dependencia", {"determinantes": ["cidade"]},
              "moda_condicionada", {"determinantes": ["cidade"]}),
    ]
    novo, flags, fontes = aplicar_regras(cidades(), regras, {}, {})
    assert novo.at[3, "cidade"] == "Boston"
    assert novo.at[3, "estado"] == "XX"
    assert not flags.at[3, "estado"]
    assert fontes.at[3, "cidade"] == "dominio/dicionario"


def test_primeiro_a_escrever_vence():
    regras = [
        regra("onca", "dominio", {"valores": ["12", "16"]}, "dicionario", {"mapa": {"12 oz": "12"}}),
        regra("onca", "formato", {"regex": r"\d+"}, "dicionario", {"mapa": {"12 oz": "doze"}}),
    ]
    novo, _, fontes = aplicar_regras(oncas(), regras, {}, {})
    assert novo.at[1, "onca"] == "12"
    assert fontes.at[1, "onca"] == "dominio/dicionario"


def test_moda_escreve_tambem_no_determinante():
    regras = [regra("estado", "dominio", {"valores": ["MA"]},
                    "moda_condicionada", {"determinantes": ["cidade"]})]
    novo, flags, fontes = aplicar_regras(cidades(), regras, {}, {})
    assert (novo.at[3, "cidade"], novo.at[3, "estado"]) == ("Boston", "MA")
    assert fontes.at[3, "cidade"] == "dominio/moda_condicionada"
    assert not flags.any(axis=None)


def test_residual_age_so_em_celula_marcada_e_nao_reparada():
    regras = [regra("onca", "dominio", {"valores": ["12", "16"]})]
    residual = {"onca": {"12 oz": "12", "16": "dezesseis"}}
    novo, flags, fontes = aplicar_regras(oncas(), regras, residual, {})
    assert list(novo["onca"]) == ["12", "12", "16", "N/A", "16"]
    assert fontes.at[1, "onca"] == "residual"
    assert list(flags["onca"]) == [False, False, False, True, False]


def test_residual_nao_reescreve_o_que_a_regra_reparou():
    regras = [regra("onca", "dominio", {"valores": ["12", "16"]}, "dicionario", {"mapa": {"12 oz": "12"}})]
    novo, _, fontes = aplicar_regras(oncas(), regras, {"onca": {"12 oz": "XX"}}, {})
    assert novo.at[1, "onca"] == "12"
    assert fontes.at[1, "onca"] == "dominio/dicionario"


def test_nao_altera_o_dataframe_recebido():
    original = oncas()
    aplicar_regras(original, [regra("onca", "dominio", {"valores": ["12"]}, "esvaziar", {})], {}, {})
    assert original.equals(oncas())
```

Run: `.venv/Scripts/python -m pytest tests/test_motor_aplicar.py -v`
Expected: FAIL com `ImportError: cannot import name 'aplicar_regras'`.

- [ ] **Step 5: Implementar `aplicar_regras`**

Acrescente ao fim de `limpeza2/motor.py`:

```python
def aplicar_regras(df, regras, residual, funcoes, dominancia=0.70):
    """Aplica as regras lendo sempre o original; devolve (df novo, flags, fontes)."""
    novo = df.copy()
    marcadas = pd.DataFrame(False, index=df.index, columns=df.columns)
    fontes = pd.DataFrame("", index=df.index, columns=df.columns)
    for regra in regras:
        coluna, estrategia = regra["coluna"], regra["estrategia"]
        mascara = detectar(df, coluna, regra["tipo"], regra["deteccao"], dominancia).fillna(False)
        marcadas[coluna] = marcadas[coluna] | mascara
        if estrategia is None:
            continue
        reparado, _ = reparar(df, coluna, estrategia, regra["reparo"], mascara, funcoes, dominancia)
        # Quem escreve primeiro vence; a moda pode escrever tambem no determinante.
        livre = (reparado != df) & (fontes == "")
        novo = novo.mask(livre, reparado)
        fontes = fontes.mask(livre, f"{regra['tipo']}/{estrategia}")
    for coluna, mapa in residual.items():
        alvo = marcadas[coluna] & (fontes[coluna] == "") & df[coluna].isin(list(mapa))
        novo.loc[alvo, coluna] = df.loc[alvo, coluna].map(mapa)
        fontes.loc[alvo, coluna] = "residual"
    return novo, marcadas & (fontes == ""), fontes
```

- [ ] **Step 6: Passa**

Run: `.venv/Scripts/python -m pytest`
Expected: `194 passed`.

- [ ] **Step 7: Prova por mutação** (aplique uma de cada vez, veja falhar, reverta)

| Mutação em `motor.py` | Teste que tem de falhar |
|---|---|
| em `reparar`, trocar `depois is not None and depois != antes` por `depois is not None` | `test_reparada_so_conta_valor_que_mudou` |
| em `aplicar_regras`, `detectar(df, ...)` vira `detectar(novo, ...)` | `test_detecta_no_original_e_nao_no_que_outra_regra_escreveu` |
| tirar `& (fontes == "")` de `livre` | `test_primeiro_a_escrever_vence` |
| `livre = (reparado[[coluna]] != df[[coluna]]).reindex(columns=df.columns, fill_value=False) & (fontes == "")` | `test_moda_escreve_tambem_no_determinante` |
| tirar `marcadas[coluna] &` do `alvo` do residual | `test_residual_age_so_em_celula_marcada_e_nao_reparada` |
| tirar `(fontes[coluna] == "") &` do `alvo` do residual | `test_residual_nao_reescreve_o_que_a_regra_reparou` |

- [ ] **Step 8: Medir e commitar**

```bash
git ls-files "*.py" ":!tests/" | xargs wc -l | sort -n | tail -3   # motor.py <= 200
git add limpeza2/motor.py tests/test_motor_reparo.py tests/test_motor_aplicar.py
git commit -m "motor: reparar simplificado e aplicar_regras, o laco unico do limpador

reparada passa a significar 'o valor mudou' em toda estrategia.
Mutacoes executadas: as seis da tarefa 1 do plano da parte 2.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 2: `regras_literais`, a conta do guia num lugar só, `crivar_residual` e a idempotência do crivo

**Files:**
- Modify: `limpeza2/tipos.py` (docstring do módulo, campo `Residual.caidas`, função `regras_literais`)
- Modify: `limpeza2/limites.py` (novas `guia_na_coluna` e `exemplos_do_guia`; `teto_da_coluna` e `celulas_sujas_do_guia` passam a usar `guia_na_coluna`)
- Modify: `limpeza2/e3_crivo.py` (`_celulas_certas` usa `guia_na_coluna`; nova `crivar_residual`)
- Create: `tests/apoio.py` (recebe `monta_entrada` de `tests/test_e3_crivo.py`)
- Test: `tests/test_tipos.py` (novo), `tests/test_e3_crivo.py`

**Interfaces:**
- Consumes: `motor.TIPOS`.
- Produces:
  - `tipos.regras_literais(deteccoes, reparos) -> list[dict]` no formato de `aplicar_regras`, ordenada pelo índice do tipo em `motor.TIPOS` (estável), com o reparo associado à candidata **pela identidade do objeto**.
  - `tipos.Residual(coluna, mapa, justificativas, caidas={})`.
  - `limites.guia_na_coluna(entrada, coluna) -> (sujo: Series, guia: Series) | None`.
  - `limites.exemplos_do_guia(entrada, coluna) -> list[(sujo, limpo)]`, ordenada, sem repetição: as células sujas das linhas do guia mais os pares.
  - `e3_crivo.crivar_residual(residuais, entrada) -> list[Residual]`; a entrada que cai sai de `mapa` e vai para `caidas` com o motivo `contradiz_o_guia` ou `valor_certificado`.
  - `tests/apoio.monta_entrada(sujo, linhas_guia=(), pares=(), corrigidos=None)`.

- [ ] **Step 1: Mover `monta_entrada` para `tests/apoio.py`**

Crie `tests/apoio.py` com a função `monta_entrada` copiada **sem mudança** de `tests/test_e3_crivo.py` (com os imports de que ela precisa):

```python
"""Apoio dos testes: entrada montada a mao e o duble do provedor de LLM."""
import pandas as pd

from limpeza2.tipos import Entrada, Perfil


def monta_entrada(sujo, linhas_guia=(), pares=(), corrigidos=None):
    """O guia traz o valor do sujo, salvo nas celulas de `corrigidos` {(linha, coluna): valor}."""
    guia_linhas = sujo.loc[list(linhas_guia)].copy() if linhas_guia else pd.DataFrame(
        columns=sujo.columns
    )
    for (linha, coluna), valor in (corrigidos or {}).items():
        guia_linhas.at[linha, coluna] = valor
    guia_pares = pd.DataFrame(
        list(pares), columns=["linha", "coluna", "sujo", "limpo"]
    ) if pares else pd.DataFrame(columns=["linha", "coluna", "sujo", "limpo"])
    return Entrada(
        sujo=sujo,
        guia_linhas=guia_linhas,
        guia_pares=guia_pares,
        perfil=Perfil(colunas={}, pares={}, candidatas_sujeito=[]),
    )
```

Em `tests/test_e3_crivo.py`, apague a definição de `monta_entrada` e acrescente `from tests.apoio import monta_entrada` aos imports.

Run: `.venv/Scripts/python -m pytest tests/test_e3_crivo.py`
Expected: tudo passa, como antes.

- [ ] **Step 2: Testes de `regras_literais`**

Crie `tests/test_tipos.py`:

```python
"""A forma literal das regras, que o residual usa e o limpador embute."""
from limpeza2.tipos import Candidata, Reparo, regras_literais


def candidata(tipo, coluna="estado"):
    return Candidata(coluna=coluna, tipo=tipo, parametros={"valores": ["MA"]}, raciocinio="r")


def test_ordena_pelo_catalogo_de_tipos():
    dep, fmt = candidata("dependencia"), candidata("formato")
    assert [r["tipo"] for r in regras_literais([dep, fmt], [])] == ["formato", "dependencia"]


def test_reparo_vai_para_a_candidata_pela_identidade():
    # Duas candidatas iguais em tudo: so a segunda ganhou reparo.
    primeira, segunda = candidata("dominio"), candidata("dominio")
    reparo = Reparo(candidata=segunda, estrategia="esvaziar", parametros={}, raciocinio="r")
    regras = regras_literais([primeira, segunda], [reparo])
    assert [r["estrategia"] for r in regras] == [None, "esvaziar"]
    assert regras[0]["reparo"] is None


def test_formato_literal():
    c = candidata("dominio")
    reparo = Reparo(candidata=c, estrategia="dicionario", parametros={"mapa": {"XX": "MA"}}, raciocinio="r")
    assert regras_literais([c], [reparo]) == [{
        "coluna": "estado", "tipo": "dominio", "deteccao": {"valores": ["MA"]},
        "estrategia": "dicionario", "reparo": {"mapa": {"XX": "MA"}},
    }]
```

Run: `.venv/Scripts/python -m pytest tests/test_tipos.py -v`
Expected: FAIL com `ImportError: cannot import name 'regras_literais'`.

- [ ] **Step 3: Implementar em `tipos.py`**

Troque a docstring do módulo por `"""O que viaja entre as etapas, ate o limpador gerado."""`. Acrescente `from limpeza2.motor import TIPOS` aos imports. Substitua a classe `Residual` por:

```python
@dataclass
class Residual:
    """Dicionario de substituicao congelado no limpador, de uma coluna."""

    coluna: str
    mapa: dict
    justificativas: dict
    caidas: dict = field(default_factory=dict)
```

E acrescente ao fim:

```python
def regras_literais(deteccoes, reparos):
    """As regras na forma literal que o limpador embute, na ordem do catalogo de tipos."""
    reparo_de = {id(r.candidata): r for r in reparos}
    regras = []
    for c in sorted(deteccoes, key=lambda c: TIPOS.index(c.tipo)):
        r = reparo_de.get(id(c))
        regras.append({
            "coluna": c.coluna, "tipo": c.tipo, "deteccao": c.parametros,
            "estrategia": r.estrategia if r else None, "reparo": r.parametros if r else None,
        })
    return regras
```

Run: `.venv/Scripts/python -m pytest tests/test_tipos.py -v`
Expected: 3 passed.

**Confira a frase:** "o que viaja entre as etapas, até o limpador gerado" descreve o arquivo inteiro? Se ao reler a função não couber nela, mova `regras_literais` para `e6_codificador.py` (o `e5` importa de lá) e registre a troca no commit.

- [ ] **Step 4: Consolidar a conta do guia em `limites.py`**

Em `limpeza2/limites.py`, acrescente depois dos imports:

```python
def guia_na_coluna(entrada, coluna):
    """O sujo e o guia da coluna nas linhas do guia, ou None se o guia nao tem a coluna."""
    if coluna not in entrada.guia_linhas.columns:
        return None
    linhas = entrada.guia_linhas.index.intersection(entrada.sujo.index)
    return entrada.sujo.loc[linhas, coluna], entrada.guia_linhas.loc[linhas, coluna]
```

Substitua `teto_da_coluna` e `celulas_sujas_do_guia` por:

```python
def teto_da_coluna(entrada, coluna):
    """O teto de marcacao da coluna: o a priori, ou a taxa suja do guia mais 2 erros padrao."""
    par = guia_na_coluna(entrada, coluna)
    if par is None or len(par[0]) == 0:
        return config.TETO_MARCACAO
    sujo, certo = par
    # Margem de 2 erros padrao de uma proporcao no pior caso (p = 0,5).
    return max(config.TETO_MARCACAO, float((sujo != certo).mean()) + 2 * sqrt(0.25 / len(sujo)))


def celulas_sujas_do_guia(entrada, coluna):
    """As celulas da coluna em que o guia corrige o sujo, no formato (linha, coluna, limpo)."""
    par = guia_na_coluna(entrada, coluna)
    if par is None:
        return []
    sujo, certo = par
    return [(int(linha), coluna, certo[linha]) for linha in sujo.index[sujo != certo]]


def exemplos_do_guia(entrada, coluna):
    """Os pares (sujo, limpo) distintos que o guia mostra na coluna, das linhas e dos pares."""
    par = guia_na_coluna(entrada, coluna)
    vistos = set() if par is None else {(s, c) for s, c in zip(*par) if s != c}
    pares = entrada.guia_pares[entrada.guia_pares["coluna"] == coluna]
    return sorted(vistos | set(zip(pares["sujo"], pares["limpo"])))
```

Em `limpeza2/e3_crivo.py`, troque o import de `limites` por:

```python
from limpeza2.limites import (
    celulas_sujas_do_guia, exemplos_do_guia, guia_na_coluna, teto_da_coluna,
    valores_certificados,
)
```

e substitua `_celulas_certas` por:

```python
def _celulas_certas(entrada, coluna, mascara):
    """Linhas do guia em que a celula ja estava certa no sujo e a mascara marca."""
    par = guia_na_coluna(entrada, coluna)
    if par is None:
        return False
    sujo, certo = par
    return bool(mascara.loc[sujo.index][sujo == certo].any())
```

Run: `.venv/Scripts/python -m pytest`
Expected: tudo passa (`197 passed`): a consolidação não muda comportamento.

- [ ] **Step 5: Testes de `crivar_residual` e da idempotência**

Acrescente a `tests/test_e3_crivo.py` (e `crivar_residual` ao import de `limpeza2.e3_crivo`; `Residual` ao import de `limpeza2.tipos`):

```python
def residual(mapa):
    return Residual(coluna="estado", mapa=dict(mapa), justificativas={s: "j" for s in mapa})


def test_residual_que_contradiz_par_do_guia_cai(sujo):
    entrada = monta_entrada(sujo, pares=[(4, "estado", "XX", "MA")])
    [r] = crivar_residual([residual({"XX": "TX"})], entrada)
    assert r.mapa == {}
    assert r.caidas == {"XX": "contradiz_o_guia"}


def test_residual_que_contradiz_celula_suja_do_guia_cai(sujo):
    entrada = monta_entrada(sujo, linhas_guia=[9], corrigidos={(9, "estado"): "TX"})
    [r] = crivar_residual([residual({"YY": "MA"})], entrada)
    assert r.caidas == {"YY": "contradiz_o_guia"}


def test_residual_que_troca_valor_certificado_cai(sujo):
    entrada = monta_entrada(sujo, linhas_guia=[0])
    [r] = crivar_residual([residual({"MA": "TX"})], entrada)
    assert r.caidas == {"MA": "valor_certificado"}


def test_residual_que_concorda_com_o_guia_fica(sujo):
    entrada = monta_entrada(sujo, pares=[(4, "estado", "XX", "MA")])
    [r] = crivar_residual([residual({"XX": "MA"})], entrada)
    assert r.mapa == {"XX": "MA"} and r.caidas == {}


def test_sem_guia_o_residual_passa_inteiro(sujo):
    [r] = crivar_residual([residual({"XX": "TX", "MA": "TX"})], monta_entrada(sujo))
    assert r.mapa == {"XX": "TX", "MA": "TX"}


def test_recrivar_a_conformidade_so_muda_a_taxa_da_uniao():
    sujo = pd.DataFrame({"estado": ["MA", "MA", "TX", "TX", "M4", "MA", "TX", "MA", "MA", "Z"]})
    entrada = monta_entrada(sujo)
    conformidade = candidata("conformidade", {"padroes": ["A"]})  # marca so "M4"
    assert crivar_deteccao([conformidade], entrada) == [conformidade]
    antes = dict(conformidade.metricas)
    dominio = candidata("dominio", {"valores": ["MA", "TX", "M4"]})  # marca so "Z"
    crivar_deteccao([conformidade, dominio], entrada)
    for chave in ("motivo", "marcadas", "taxa", "teto"):
        assert conformidade.metricas[chave] == antes[chave]
    assert (antes["taxa_uniao"], conformidade.metricas["taxa_uniao"]) == (0.1, 0.2)
```

Run: `.venv/Scripts/python -m pytest tests/test_e3_crivo.py -v`
Expected: FAIL com `ImportError: cannot import name 'crivar_residual'`.

- [ ] **Step 6: Implementar `crivar_residual`**

Acrescente ao fim de `limpeza2/e3_crivo.py`:

```python
def crivar_residual(residuais, entrada):
    """Tira do dicionario a entrada que contradiz o guia ou troca valor que ele certifica."""
    for residual in residuais:
        exemplos = exemplos_do_guia(entrada, residual.coluna)
        certificados = valores_certificados(entrada, residual.coluna)
        for sujo, limpo in sorted(residual.mapa.items()):
            if any(s == sujo and c != limpo for s, c in exemplos):
                residual.caidas[sujo] = "contradiz_o_guia"
            elif sujo in certificados:
                # Sem excecao: a chave do dicionario nao carrega contexto.
                residual.caidas[sujo] = "valor_certificado"
            else:
                continue
            del residual.mapa[sujo]
    return residuais
```

Run: `.venv/Scripts/python -m pytest`
Expected: `203 passed`.

- [ ] **Step 7: Prova por mutação**

| Mutação | Teste que tem de falhar |
|---|---|
| `regras_literais`: `reparo_de` indexado por `(r.candidata.coluna, r.candidata.tipo)` (e a busca idem) | `test_reparo_vai_para_a_candidata_pela_identidade` |
| `regras_literais`: tirar o `sorted` | `test_ordena_pelo_catalogo_de_tipos` |
| `exemplos_do_guia`: tirar `\| set(zip(pares[...]))` | `test_residual_que_contradiz_par_do_guia_cai` |
| `exemplos_do_guia`: `vistos = set()` sempre | `test_residual_que_contradiz_celula_suja_do_guia_cai` |
| `crivar_residual`: tirar o ramo `elif sujo in certificados` | `test_residual_que_troca_valor_certificado_cai` |
| `crivar_residual`: `c != limpo` vira `c == limpo` | `test_residual_que_concorda_com_o_guia_fica` |
| `_gravar_uniao` grava em `"taxa"` em vez de `"taxa_uniao"` | `test_recrivar_a_conformidade_so_muda_a_taxa_da_uniao` |

- [ ] **Step 8: Medir e commitar**

```bash
git ls-files "*.py" ":!tests/" | xargs wc -l | sort -n | tail -3   # e3_crivo.py <= 200
git add limpeza2/tipos.py limpeza2/limites.py limpeza2/e3_crivo.py tests/apoio.py tests/test_tipos.py tests/test_e3_crivo.py
git commit -m "regras_literais, a conta do guia num lugar so e crivar_residual

Mutacoes executadas: as sete da tarefa 2 do plano da parte 2.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 3: `config.py`, `provedor.py` e o dublê

**Files:**
- Modify: `limpeza2/config.py` (bloco do provedor no fim), `.env.exemplo`
- Create: `limpeza2/provedor.py`, `tests/conftest.py`
- Modify: `tests/apoio.py` (o dublê)
- Test: `tests/test_provedor.py`

**Interfaces:**
- Produces:
  - `provedor.iniciar(destino) -> Cliente` abre uma geração (zera registro e contador; grava `destino/respostas.jsonl`).
  - `provedor.cliente() -> Cliente`, o da geração aberta.
  - `Cliente.pedir_json(etapa, unidade, instrucao, conteudo, esquema) -> dict`, ou `FalhaDoLLM`.
  - `Cliente.anotar(etapa, unidade, status, detalhe="") -> dict`.
  - `Cliente.registro`: lista de `{"etapa", "unidade", "status", "detalhe", "tokens"}`; `Cliente.chamadas`: int.
  - `provedor.FalhaDoLLM(motivo)`, com `motivo` em `rede`, `cortada`, `recusada`, `json_invalido`, `teto`.
  - `provedor._construir_api()` (os testes o substituem por `monkeypatch`); a API tem `responder(chave, instrucao, conteudo, esquema) -> dict cru` com `texto`, `fim`, `tokens`, `recusa` (ou `{"rede": True}`).
  - `config`: `PROVEDOR`, `MODELO`, `OLLAMA_URL`, `RESPOSTAS_GRAVADAS`, `ESFORCO_RACIOCINIO`, `TEMPERATURA`, `SAIDA_ESTRITA`, `TIMEOUT_LLM`, `TENTATIVAS_API`, `TETO_CHAMADAS`, `VALORES_NO_PROMPT`, `LINHAS_POR_LOTE`, `MAX_LOTES_RESIDUAL`.
  - `tests/apoio`: `ok(dados)`, `CORTADA`, `Roteiro(responder)`, `em_fila(*respostas)`; fixture `roteiro(responder, destino=None) -> Roteiro` em `tests/conftest.py`.

- [ ] **Step 1: Config**

Em `limpeza2/config.py`, substitua as duas últimas linhas (`PROVEDOR = ...` e `MODELO = ...`) por:

```python
PROVEDOR = os.getenv("PROVEDOR", "openai")
MODELO = os.getenv("MODELO", "gpt-6-luna")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
# O respostas.jsonl que PROVEDOR=gravado reproduz.
RESPOSTAS_GRAVADAS = os.getenv("RESPOSTAS_GRAVADAS", "")
# So com raciocinio em none o modelo aceita temperature; None tira o parametro do pedido.
ESFORCO_RACIOCINIO = "none"
TEMPERATURA = 0
SAIDA_ESTRITA = True
TIMEOUT_LLM = 120
TENTATIVAS_API = 2
TETO_CHAMADAS = 80
VALORES_NO_PROMPT = 30
LINHAS_POR_LOTE = 40
MAX_LOTES_RESIDUAL = 10
```

Troque o conteúdo de `.env.exemplo` por:

```
PROVEDOR=openai
MODELO=gpt-6-luna
OPENAI_API_KEY=cole-a-chave-aqui
# Para PROVEDOR=ollama:
# OLLAMA_URL=http://localhost:11434/v1
# Para PROVEDOR=gravado (reproduz um run):
# RESPOSTAS_GRAVADAS=saida/beers_2026-10-12_1500/respostas.jsonl
```

- [ ] **Step 2: O dublê**

Acrescente a `tests/apoio.py` (e `import json` aos imports):

```python
def ok(dados):
    """A resposta crua de uma chamada que deu certo."""
    return {"texto": json.dumps(dados), "fim": "stop", "tokens": 5, "recusa": None}


CORTADA = {"texto": "", "fim": "length", "tokens": 0, "recusa": None}


class Roteiro:
    """API falsa: responde o que `responder(instrucao, conteudo)` devolver e guarda os pedidos."""

    def __init__(self, responder):
        self.responder_fn, self.pedidos = responder, []

    def responder(self, chave, instrucao, conteudo, esquema):
        self.pedidos.append((instrucao, conteudo))
        resposta = self.responder_fn(instrucao, conteudo)
        if isinstance(resposta, Exception):
            raise resposta
        # Resposta crua (com "fim" ou "rede") passa direto; dict de dados vira resposta valida.
        return resposta if ("fim" in resposta or "rede" in resposta) else ok(resposta)


def em_fila(*respostas):
    """Um Roteiro que devolve as respostas na ordem, uma por chamada."""
    fila = list(respostas)
    return Roteiro(lambda instrucao, conteudo: fila.pop(0))
```

Crie `tests/conftest.py`:

```python
"""Fixtures compartilhadas: o provedor de mentira."""
import pytest

from limpeza2 import provedor
from tests.apoio import Roteiro


@pytest.fixture
def roteiro(monkeypatch, tmp_path):
    """Abre uma geracao com a API falsa; devolve a funcao que instala as respostas."""
    def instalar(responder, destino=None):
        api = Roteiro(responder)
        monkeypatch.setattr(provedor, "_construir_api", lambda: api)
        provedor.iniciar(destino or tmp_path / "geracao")
        return api
    return instalar
```

- [ ] **Step 3: Testes do provedor**

Crie `tests/test_provedor.py`:

```python
"""O provedor: falha alto no desconhecido, degrada com nome no resto, e reproduz."""
import httpx2
import openai
import pytest

from limpeza2 import config, provedor
from tests.apoio import CORTADA, em_fila, ok

REQUISICAO = httpx2.Request("POST", "http://x")


def pedir(c, conteudo="conteudo"):
    return c.pedir_json("detector", "estado", "instrucao", conteudo, {})


def test_provedor_desconhecido_falha_alto(monkeypatch):
    monkeypatch.setattr(config, "PROVEDOR", "opneai")
    with pytest.raises(ValueError, match="opneai"):
        provedor._construir_api()


def test_resposta_valida_vira_dict_e_entra_no_registro(tmp_path):
    c = provedor.Cliente(tmp_path, em_fila(ok({"regras": []})))
    assert pedir(c) == {"regras": []}
    assert c.registro == [{"etapa": "detector", "unidade": "estado", "status": "ok",
                           "detalhe": "", "tokens": 5}]


@pytest.mark.parametrize("bruto, motivo", [
    ({"texto": '{"a": 1', "fim": "stop", "tokens": 0, "recusa": None}, "json_invalido"),
    ({"texto": "[1, 2]", "fim": "stop", "tokens": 0, "recusa": None}, "json_invalido"),
    (CORTADA, "cortada"),
    ({"texto": None, "fim": "stop", "tokens": 0, "recusa": "nao posso"}, "recusada"),
])
def test_falha_vira_falha_do_llm_com_motivo(tmp_path, bruto, motivo):
    c = provedor.Cliente(tmp_path, em_fila(bruto))
    with pytest.raises(provedor.FalhaDoLLM) as erro:
        pedir(c)
    assert erro.value.motivo == motivo
    assert c.registro[-1]["status"] == motivo


def test_rede_esgotada_vira_falha_do_llm(tmp_path):
    c = provedor.Cliente(tmp_path, em_fila(openai.APIConnectionError(request=REQUISICAO)))
    with pytest.raises(provedor.FalhaDoLLM) as erro:
        pedir(c)
    assert erro.value.motivo == "rede"


def test_autenticacao_nao_degrada(tmp_path):
    negada = openai.AuthenticationError(
        "chave", response=httpx2.Response(401, request=REQUISICAO), body=None
    )
    with pytest.raises(openai.AuthenticationError):
        pedir(provedor.Cliente(tmp_path, em_fila(negada)))


def test_teto_de_chamadas(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TETO_CHAMADAS", 2)
    c = provedor.Cliente(tmp_path, em_fila(ok({}), ok({})))
    pedir(c)
    pedir(c)
    with pytest.raises(provedor.FalhaDoLLM) as erro:
        pedir(c)
    assert erro.value.motivo == "teto"
    assert [n["status"] for n in c.registro] == ["ok", "ok", "teto"]
    assert c.chamadas == 2


def test_gravado_reproduz_a_geracao_na_mesma_ordem(tmp_path, monkeypatch):
    original = provedor.Cliente(tmp_path / "a", em_fila(ok({"x": 1}), ok({"x": 2}), CORTADA))
    assert [pedir(original, "c1"), pedir(original, "c1")] == [{"x": 1}, {"x": 2}]
    with pytest.raises(provedor.FalhaDoLLM):
        pedir(original, "c2")
    monkeypatch.setattr(config, "PROVEDOR", "gravado")
    monkeypatch.setattr(config, "RESPOSTAS_GRAVADAS", str(tmp_path / "a" / "respostas.jsonl"))
    copia = provedor.iniciar(tmp_path / "b")
    assert [pedir(copia, "c1"), pedir(copia, "c1")] == [{"x": 1}, {"x": 2}]
    with pytest.raises(provedor.FalhaDoLLM) as erro:
        pedir(copia, "c2")
    assert erro.value.motivo == "cortada"


def test_gravado_sem_a_resposta_levanta(tmp_path, monkeypatch):
    (tmp_path / "vazio.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setattr(config, "PROVEDOR", "gravado")
    monkeypatch.setattr(config, "RESPOSTAS_GRAVADAS", str(tmp_path / "vazio.jsonl"))
    with pytest.raises(KeyError):
        pedir(provedor.iniciar(tmp_path / "b"))


def test_cada_geracao_zera_registro_e_contador(tmp_path, monkeypatch):
    monkeypatch.setattr(provedor, "_construir_api", lambda: em_fila(ok({})))
    pedir(provedor.iniciar(tmp_path / "a"))
    segunda = provedor.iniciar(tmp_path / "b")
    assert (segunda.registro, segunda.chamadas) == ([], 0)
    assert provedor.cliente() is segunda


class SdkFalso:
    """Guarda os argumentos de chat.completions.create."""

    def __init__(self):
        self.chat = self
        self.completions = self

    def create(self, **argumentos):
        self.argumentos = argumentos
        raise openai.APIConnectionError(request=REQUISICAO)


def api_com_sdk_falso(esforco):
    api = provedor._Api.__new__(provedor._Api)
    api.sdk, api.esforco = SdkFalso(), esforco
    return api


def test_pedido_leva_esquema_estrito_temperatura_semente_e_esforco():
    api = api_com_sdk_falso("none")
    with pytest.raises(openai.APIConnectionError):
        api.responder("k", "instrucao", "conteudo", {"type": "object"})
    a = api.sdk.argumentos
    assert a["response_format"]["json_schema"]["strict"] is True
    assert (a["temperature"], a["seed"], a["reasoning_effort"]) == (0, config.SEMENTE, "none")
    assert a["model"] == config.MODELO


def test_parametro_none_sai_do_pedido(monkeypatch):
    monkeypatch.setattr(config, "TEMPERATURA", None)
    api = api_com_sdk_falso(None)
    with pytest.raises(openai.APIConnectionError):
        api.responder("k", "instrucao", "conteudo", {})
    assert "temperature" not in api.sdk.argumentos
    assert "reasoning_effort" not in api.sdk.argumentos


def test_plano_b_pede_json_object_e_descreve_o_esquema(monkeypatch):
    monkeypatch.setattr(config, "SAIDA_ESTRITA", False)
    api = api_com_sdk_falso("none")
    with pytest.raises(openai.APIConnectionError):
        api.responder("k", "instrucao", "conteudo", {"type": "object"})
    assert api.sdk.argumentos["response_format"] == {"type": "json_object"}
    assert '"type": "object"' in api.sdk.argumentos["messages"][0]["content"]
```

Run: `.venv/Scripts/python -m pytest tests/test_provedor.py -v`
Expected: FAIL com `ImportError` (o módulo não existe).

- [ ] **Step 4: Implementar `limpeza2/provedor.py`**

```python
"""Entrega o cliente do provedor de LLM escolhido; nenhum outro modulo conhece provedor."""
import hashlib
import json
from pathlib import Path

import openai

from limpeza2 import config

# Falhas transitorias que o SDK ja tentou de novo; viram FalhaDoLLM("rede").
_REDE = (openai.APIConnectionError, openai.RateLimitError, openai.InternalServerError)
_atual = None


class FalhaDoLLM(Exception):
    """Chamada que falhou com degradacao nomeada: a unidade fica sem regra."""

    def __init__(self, motivo):
        super().__init__(motivo)
        self.motivo = motivo


def iniciar(destino):
    """Abre uma geracao: registro e contador zerados, respostas gravadas em `destino`."""
    global _atual
    _atual = Cliente(Path(destino), _construir_api())
    return _atual


def cliente():
    """O cliente da geracao aberta por `iniciar`."""
    if _atual is None:
        raise RuntimeError("provedor.iniciar(destino) nao foi chamado")
    return _atual


def _construir_api():
    """A API do provedor em config.PROVEDOR; valor desconhecido levanta."""
    provedor = config.PROVEDOR.strip().lower()
    if provedor == "openai":
        return _Api(esforco=config.ESFORCO_RACIOCINIO)
    if provedor == "ollama":
        return _Api(esforco=None, base_url=config.OLLAMA_URL, api_key="ollama")
    if provedor == "gravado":
        return _Gravado(Path(config.RESPOSTAS_GRAVADAS))
    raise ValueError(
        f"PROVEDOR={provedor!r} nao e suportado. Use openai, ollama ou gravado. "
        "Nao caio para openai em silencio: isso mandaria dado para fora da rede."
    )


class Cliente:
    """Pede JSON ao modelo, grava cada resposta crua e anota cada chamada no registro."""

    def __init__(self, destino, api):
        destino.mkdir(parents=True, exist_ok=True)
        self.api, self.registro, self.chamadas = api, [], 0
        self.arquivo = destino / "respostas.jsonl"
        self.arquivo.write_text("", encoding="utf-8")

    def anotar(self, etapa, unidade, status, detalhe=""):
        """Acrescenta uma nota ao registro da geracao e a devolve."""
        nota = {"etapa": etapa, "unidade": unidade, "status": status, "detalhe": detalhe, "tokens": 0}
        self.registro.append(nota)
        return nota

    def pedir_json(self, etapa, unidade, instrucao, conteudo, esquema):
        """Uma chamada: devolve o dict da resposta ou levanta FalhaDoLLM."""
        if self.chamadas >= config.TETO_CHAMADAS:
            self.anotar(etapa, unidade, "teto")
            raise FalhaDoLLM("teto")
        self.chamadas += 1
        chave = hashlib.sha256(json.dumps([instrucao, conteudo]).encode()).hexdigest()
        try:
            bruto = self.api.responder(chave, instrucao, conteudo, esquema)
        except _REDE:
            bruto = {"rede": True}
        with self.arquivo.open("a", encoding="utf-8") as saida:
            saida.write(json.dumps({"chave": chave, "etapa": etapa, "unidade": unidade,
                                    "bruto": bruto}, ensure_ascii=False) + "\n")
        nota = self.anotar(etapa, unidade, "ok")
        nota["tokens"] = bruto.get("tokens", 0)
        motivo, dados = _interpretar(bruto)
        if motivo:
            nota["status"] = motivo
            raise FalhaDoLLM(motivo)
        return dados


def _interpretar(bruto):
    """O motivo da falha e None, ou None e o dict da resposta."""
    if bruto.get("rede"):
        return "rede", None
    if bruto.get("recusa"):
        return "recusada", None
    if bruto.get("fim") == "length":
        return "cortada", None
    try:
        dados = json.loads(bruto.get("texto") or "")
    except json.JSONDecodeError:
        return "json_invalido", None
    return (None, dados) if isinstance(dados, dict) else ("json_invalido", None)


class _Api:
    """Chat Completions do SDK openai, que serve a OpenAI e ao Ollama."""

    def __init__(self, esforco, **conexao):
        self.sdk = openai.OpenAI(
            timeout=config.TIMEOUT_LLM, max_retries=config.TENTATIVAS_API, **conexao
        )
        self.esforco = esforco

    def responder(self, chave, instrucao, conteudo, esquema):
        """A resposta crua: texto, motivo de parada, tokens e recusa."""
        if config.SAIDA_ESTRITA:
            formato = {"type": "json_schema",
                       "json_schema": {"name": "resposta", "strict": True, "schema": esquema}}
        else:
            formato = {"type": "json_object"}
            instrucao += "\nResponda em JSON com este esquema: " + json.dumps(esquema)
        opcionais = {"temperature": config.TEMPERATURA, "seed": config.SEMENTE,
                     "reasoning_effort": self.esforco}
        resposta = self.sdk.chat.completions.create(
            model=config.MODELO, response_format=formato,
            messages=[{"role": "system", "content": instrucao},
                      {"role": "user", "content": conteudo}],
            **{k: v for k, v in opcionais.items() if v is not None},
        )
        escolha = resposta.choices[0]
        return {"texto": escolha.message.content, "fim": escolha.finish_reason,
                "tokens": resposta.usage.total_tokens if resposta.usage else 0,
                "recusa": getattr(escolha.message, "refusal", None)}


class _Gravado:
    """Reproduz um respostas.jsonl, na ordem em que cada chamada foi feita."""

    def __init__(self, caminho):
        self.fila = {}
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            registro = json.loads(linha)
            self.fila.setdefault(registro["chave"], []).append(registro["bruto"])

    def responder(self, chave, instrucao, conteudo, esquema):
        """A proxima resposta gravada para esta chamada; ausente levanta, nao degrada."""
        if not self.fila.get(chave):
            raise KeyError(f"resposta nao gravada para a chamada {chave}")
        return self.fila[chave].pop(0)
```

Run: `.venv/Scripts/python -m pytest`
Expected: tudo passa (`218 passed`).

- [ ] **Step 5: Prova por mutação**

| Mutação em `provedor.py` | Teste que tem de falhar |
|---|---|
| `raise ValueError(...)` vira `return _Api(esforco=config.ESFORCO_RACIOCINIO)` | `test_provedor_desconhecido_falha_alto` |
| tirar o `if bruto.get("fim") == "length"` | `test_falha_vira_falha_do_llm_com_motivo[...cortada]` |
| `isinstance(dados, dict)` vira `True` | `test_falha_vira_falha_do_llm_com_motivo[...json_invalido...]` (o de `[1, 2]`) |
| acrescentar `openai.AuthenticationError` a `_REDE` | `test_autenticacao_nao_degrada` |
| `>=` vira `>` no teto | `test_teto_de_chamadas` |
| em `_Gravado.responder`, `pop(0)` vira `[0]` | `test_gravado_reproduz_a_geracao_na_mesma_ordem` |
| em `_Gravado.responder`, devolver `ok({})` quando a fila está vazia | `test_gravado_sem_a_resposta_levanta` |
| tirar o filtro `if v is not None` | `test_parametro_none_sai_do_pedido` |

- [ ] **Step 6: Medir e commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l     # 11
git add limpeza2/config.py limpeza2/provedor.py .env.exemplo tests/apoio.py tests/conftest.py tests/test_provedor.py
git commit -m "provedor: cliente por geracao, falhas com nome, registro e reproducao gravada

Modelo padrao gpt-6-luna com raciocinio none.
Mutacoes executadas: as oito da tarefa 3 do plano da parte 2.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 4: `e2_detector.py`

**Files:**
- Modify: `limpeza2/e1_perfil.py` (contagens viram `int` do Python, para o prompt ler `('12', 3)` e não `np.int64(3)`)
- Create: `limpeza2/e2_detector.py`
- Test: `tests/test_e1_perfil.py` (um teste), `tests/test_e2_detector.py` (novo)

**Interfaces:**
- Consumes: `provedor.cliente()`, `provedor.FalhaDoLLM`, `limites.exemplos_do_guia`, `config.VARIANTES_POR_TIPO`, `Candidata`.
- Produces:
  - `e2_detector.propor(entrada, schema, conformes) -> list[Candidata]`. `schema` é a lista de conformidades **aprovadas** que o crivo devolveu; `conformes`, todas.
  - `e2_detector.catalogo(entrada, coluna, schema) -> list[str]`.
  - `e2_detector.caso_da_conformidade(coluna, schema, conformes) -> str`, que começa com `aprovada:`, `reprovada (`, `vacua:` ou `sem schema:`.
  - `e2_detector.INSTRUCAO` (o dublê reconhece o agente por ela).
  - O conteúdo do prompt tem uma linha `coluna: <nome>`.

- [ ] **Step 1: Contagens como `int`**

Acrescente a `tests/test_e1_perfil.py`:

```python
def test_contagens_do_perfil_sao_int_do_python():
    perfil = perfilar_coluna(pd.Series(["a", "a", "b"]))
    for chave in ("frequentes", "raros", "padroes"):
        assert all(type(n) is int for _, n in perfil[chave])
```

(acrescente `perfilar_coluna` ao import de `limpeza2.e1_perfil`, se ainda não estiver.)

Run: `.venv/Scripts/python -m pytest tests/test_e1_perfil.py::test_contagens_do_perfil_sao_int_do_python -v`
Expected: FAIL.

Em `perfilar_coluna`, troque as três linhas:

```python
        "frequentes": [(v, int(n)) for v, n in contagem.head(FREQUENTES).items()],
        "raros": [(v, int(n)) for v, n in contagem.tail(RAROS).items()],
        "padroes": [(v, int(n)) for v, n in padroes.head(FREQUENTES).items()],
```

Run: `.venv/Scripts/python -m pytest`
Expected: tudo passa.

- [ ] **Step 2: Testes do detector**

Crie `tests/test_e2_detector.py`:

```python
"""O detector: catalogo por coluna, conversao que descarta o malformado, degradacao."""
import pandas as pd

from limpeza2 import e2_detector
from limpeza2.e1_perfil import perfilar_coluna
from limpeza2.tipos import Candidata, Entrada, Perfil
from tests.apoio import CORTADA

PAR = {("cidade", "estado"): {"det": 0.83, "n_grupos": 2, "n_divergentes": 1,
                              "frac_ambiguos": 0.0, "cobertura": 1.0}}


def entrada_minima(pares=None):
    sujo = pd.DataFrame({"cidade": ["Boston"] * 3 + ["Austin"] * 3,
                         "estado": ["MA", "MA", "XX", "TX", "TX", "TX"]})
    return Entrada(
        sujo=sujo, guia_linhas=pd.DataFrame(columns=sujo.columns),
        guia_pares=pd.DataFrame(columns=["linha", "coluna", "sujo", "limpo"]),
        perfil=Perfil(colunas={c: perfilar_coluna(sujo[c]) for c in sujo},
                      pares=pares or {}, candidatas_sujeito=[]),
    )


def conformidade(coluna, motivo):
    c = Candidata(coluna=coluna, tipo="conformidade", parametros={"padroes": ["A"]}, raciocinio="x")
    c.metricas = {"motivo": motivo}
    return c


def variante(tipo, **campos):
    base = dict.fromkeys(["regex", "valores", "minimo", "maximo", "sentinelas", "determinantes"])
    return {**base, **campos, "tipo": tipo, "raciocinio": "r"}


def so_na(coluna, regras):
    """Responde `regras` para a coluna pedida e nada para as outras."""
    return lambda instrucao, conteudo: {"regras": regras if f"coluna: {coluna}\n" in conteudo else []}


def test_formato_sai_so_quando_a_conformidade_da_coluna_foi_aprovada():
    entrada, aprovada = entrada_minima(), conformidade("estado", "aprovada")
    assert "formato" not in e2_detector.catalogo(entrada, "estado", [aprovada])
    assert "formato" in e2_detector.catalogo(entrada, "cidade", [aprovada])
    assert "formato" in e2_detector.catalogo(entrada, "estado", [])


def test_dependencia_so_onde_a_coluna_e_o_lado_determinado():
    assert "dependencia" in e2_detector.catalogo(entrada_minima(PAR), "estado", [])
    assert "dependencia" not in e2_detector.catalogo(entrada_minima(PAR), "cidade", [])
    assert "dependencia" not in e2_detector.catalogo(entrada_minima(), "estado", [])


def test_caso_da_conformidade_nos_quatro_casos():
    aprovada, vacua = conformidade("estado", "aprovada"), conformidade("estado", "vacua")
    reprovada = conformidade("estado", "perde_par_do_guia")
    caso = e2_detector.caso_da_conformidade
    assert caso("estado", [aprovada], [aprovada]).startswith("aprovada:")
    assert caso("estado", [], [vacua]).startswith("vacua:")
    assert caso("estado", [], [reprovada]).startswith("reprovada (perde_par_do_guia)")
    assert caso("estado", [], []).startswith("sem schema:")


def test_variante_malformada_cai_sozinha(roteiro):
    roteiro(so_na("estado", [
        variante("dominio", valores=["MA", "TX"]),
        variante("dominio", valores=[]),
        variante("faixa", minimo=None, maximo=3),
        variante("faixa", minimo=5, maximo=1),
        variante("formato", regex=None),
        {"tipo": "inexistente"},
        "nem e objeto",
    ]))
    candidatas = e2_detector.propor(entrada_minima(), [], [])
    assert [(c.coluna, c.tipo, c.parametros) for c in candidatas] == [
        ("estado", "dominio", {"valores": ["MA", "TX"]})
    ]


def test_no_maximo_tres_variantes_por_tipo(roteiro):
    roteiro(so_na("estado", [variante("dominio", valores=[v]) for v in ("MA", "TX", "XX", "YY")]))
    candidatas = e2_detector.propor(entrada_minima(), [], [])
    assert [c.parametros["valores"] for c in candidatas] == [["MA"], ["TX"], ["XX"]]


def test_tipo_fora_do_catalogo_da_coluna_cai(roteiro):
    aprovada = conformidade("estado", "aprovada")
    roteiro(so_na("estado", [variante("formato", regex="[A-Z]{2}")]))
    assert e2_detector.propor(entrada_minima(), [aprovada], [aprovada]) == []


def test_falha_do_llm_deixa_so_aquela_coluna_sem_regra(roteiro):
    def responder(instrucao, conteudo):
        if "coluna: cidade\n" in conteudo:
            return CORTADA
        return {"regras": [variante("dominio", valores=["MA", "TX"])]}
    api = roteiro(responder)
    candidatas = e2_detector.propor(entrada_minima(), [], [])
    assert [c.coluna for c in candidatas] == ["estado"]
    assert len(api.pedidos) == 2


def test_prompt_leva_o_caso_o_catalogo_e_o_par_minerado(roteiro):
    api = roteiro(lambda instrucao, conteudo: {"regras": []})
    e2_detector.propor(entrada_minima(PAR), [], [conformidade("estado", "vacua")])
    instrucao, conteudo = next(p for p in api.pedidos if "coluna: estado\n" in p[1])
    assert instrucao == e2_detector.INSTRUCAO
    assert "conformidade de schema: vacua:" in conteudo
    assert "catalogo: formato, dominio, faixa, ausente_disfarcado, dependencia" in conteudo
    assert "par minerado: cidade -> estado" in conteudo
```

Run: `.venv/Scripts/python -m pytest tests/test_e2_detector.py -v`
Expected: FAIL com `ImportError`.

- [ ] **Step 3: Implementar `limpeza2/e2_detector.py`**

```python
"""Etapa 2: agente detector -> predicados candidatos, uma chamada por coluna."""
from limpeza2 import config, provedor
from limpeza2.limites import exemplos_do_guia
from limpeza2.tipos import Candidata

CAMPOS = {
    "formato": ("regex",), "dominio": ("valores",), "faixa": ("minimo", "maximo"),
    "ausente_disfarcado": ("sentinelas",), "dependencia": ("determinantes",),
}

INSTRUCAO = """Voce e o agente detector de uma ferramenta de limpeza de dados.
Recebe o perfil de UMA coluna de uma tabela suja e propoe regras que apontam as celulas
erradas dela. Voce nao corrige nada: so detecta.
Cada regra e de um tipo do catalogo fechado, e voce so pode usar os tipos listados em "catalogo":
- formato: "regex" (sintaxe Python, casada com fullmatch) que todo valor VALIDO casa.
- dominio: "valores", a lista dos valores validos; o que estiver fora e erro.
- faixa: "minimo" e "maximo" numericos; numero fora da faixa e erro (texto nunca e marcado por faixa).
- ausente_disfarcado: "sentinelas", valores que significam ausencia (ex.: N/A, -, 0) no lugar de um dado.
- dependencia: "determinantes", colunas que determinam esta, escolhidas entre os pares minerados.
A linha "conformidade de schema" diz o que uma regra derivada do guia ja cobre nesta coluna.
Proponha ate 3 variantes por tipo, da mais estrita a mais permissiva, e so os tipos que fazem sentido.
Uma regra que marca celula que o guia mostra correta e reprovada; uma que marca mais de 30% da coluna
tambem. Preencha so os campos do tipo; os outros vao null. "raciocinio": uma frase.
Responda em JSON."""


def propor(entrada, schema, conformes):
    """Uma chamada por coluna; devolve as candidatas validas de todas as colunas."""
    candidatas = []
    for coluna in entrada.sujo.columns:
        tipos = catalogo(entrada, coluna, schema)
        conteudo = _conteudo(entrada, coluna, tipos, caso_da_conformidade(coluna, schema, conformes))
        try:
            resposta = provedor.cliente().pedir_json(
                "detector", coluna, INSTRUCAO, conteudo, _esquema(tipos)
            )
        except provedor.FalhaDoLLM:
            # Degradacao nomeada: a coluna fica sem regra do LLM; o motivo esta no registro.
            continue
        candidatas += _candidatas(coluna, resposta.get("regras"), tipos)
    return candidatas


def catalogo(entrada, coluna, schema):
    """Os tipos que o detector pode propor na coluna; ver a spec da parte 2, secao 3.2."""
    tipos = list(CAMPOS)
    if any(c.coluna == coluna for c in schema):
        tipos.remove("formato")
    if not any(determinado == coluna for _, determinado in entrada.perfil.pares):
        tipos.remove("dependencia")
    return tipos


def caso_da_conformidade(coluna, schema, conformes):
    """A frase que diz ao LLM o que a conformidade ja cobre na coluna."""
    if any(c.coluna == coluna for c in schema):
        return "aprovada: a forma ja esta coberta; procure erro de valor, de magnitude, de ausencia ou contextual"
    propria = [c for c in conformes if c.coluna == coluna]
    if not propria:
        return "sem schema: o guia mostra formatos variados, ou nao ha guia"
    motivo = propria[0].metricas.get("motivo")
    if motivo == "vacua":
        return "vacua: schema apertado sem nenhuma violacao; o erro, se existe, e contextual"
    return f"reprovada ({motivo}): existe schema, mas a regra dele nao passou"


def _conteudo(entrada, coluna, tipos, caso):
    """O perfil da coluna em uma linha por item, no estilo do catalogo do CatDB."""
    p = entrada.perfil.colunas[coluna]
    linhas = [
        f"colunas da tabela: {', '.join(entrada.sujo.columns)} ({len(entrada.sujo)} linhas)",
        f"coluna: {coluna}",
        f"catalogo: {', '.join(tipos)}",
        f"conformidade de schema: {caso}",
        f"distintos: {p['n_distintos']}; vazios: {p['n_vazios']}; comprimentos: {p['comprimentos']}",
        f"frequentes: {p['frequentes']}",
        f"raros: {p['raros']}",
        f"padroes: {p['padroes']}",
    ]
    linhas += [f"par minerado: {det} -> {coluna} {_arredondado(numeros)}"
               for (det, alvo), numeros in entrada.perfil.pares.items() if alvo == coluna]
    linhas += [f"exemplo do guia: {s!r} -> {c!r}" for s, c in exemplos_do_guia(entrada, coluna)]
    guia = entrada.guia_linhas.to_csv() if len(entrada.guia_linhas) else "nenhuma\n"
    return "\n".join(linhas) + "\nlinhas corrigidas do guia:\n" + guia


def _arredondado(numeros):
    """Os numeros do par com tres casas, para o prompt."""
    return {k: round(v, 3) for k, v in numeros.items()}


def _esquema(tipos):
    """O esquema estrito de uma resposta: lista de variantes num objeto plano com nulos."""
    texto, numero = {"type": ["string", "null"]}, {"type": ["number", "null"]}
    lista = {"type": ["array", "null"], "items": {"type": "string"}}
    campos = {"tipo": {"type": "string", "enum": list(tipos)}, "regex": texto, "valores": lista,
              "minimo": numero, "maximo": numero, "sentinelas": lista, "determinantes": lista,
              "raciocinio": {"type": "string"}}
    variante = {"type": "object", "additionalProperties": False,
                "required": list(campos), "properties": campos}
    return {"type": "object", "additionalProperties": False, "required": ["regras"],
            "properties": {"regras": {"type": "array", "items": variante}}}


def _candidatas(coluna, regras, tipos):
    """Converte as variantes validas em Candidatas; a malformada cai sozinha."""
    candidatas, por_tipo = [], {}
    for regra in regras if isinstance(regras, list) else []:
        if not isinstance(regra, dict) or regra.get("tipo") not in tipos:
            continue
        tipo = regra["tipo"]
        parametros = {campo: regra.get(campo) for campo in CAMPOS[tipo]}
        if not _valida(tipo, parametros) or por_tipo.get(tipo, 0) >= config.VARIANTES_POR_TIPO:
            continue
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        candidatas.append(Candidata(coluna=coluna, tipo=tipo, parametros=parametros,
                                    raciocinio=str(regra.get("raciocinio") or "")))
    return candidatas


def _valida(tipo, parametros):
    """Os parametros tem a forma que o motor espera; regex invalida o crivo reprova como lancou."""
    if tipo == "formato":
        return isinstance(parametros["regex"], str) and parametros["regex"] != ""
    if tipo == "faixa":
        minimo, maximo = parametros["minimo"], parametros["maximo"]
        numeros = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (minimo, maximo))
        return numeros and minimo <= maximo
    (lista,) = parametros.values()
    return isinstance(lista, list) and len(lista) > 0 and all(isinstance(v, str) for v in lista)
```

Run: `.venv/Scripts/python -m pytest`
Expected: tudo passa.

- [ ] **Step 4: Prova por mutação**

| Mutação em `e2_detector.py` | Teste que tem de falhar |
|---|---|
| `catalogo`: tirar o `if any(c.coluna == coluna for c in schema)` (o `formato` nunca sai) | `test_formato_sai_so_quando_a_conformidade_da_coluna_foi_aprovada` |
| `catalogo`: `determinado == coluna` vira `det == coluna` no par | `test_dependencia_so_onde_a_coluna_e_o_lado_determinado` |
| `caso_da_conformidade`: tirar o ramo `vacua` | `test_caso_da_conformidade_nos_quatro_casos` |
| `_valida`: tirar `and minimo <= maximo` | `test_variante_malformada_cai_sozinha` |
| `_candidatas`: tirar a condição `por_tipo.get(...) >= config.VARIANTES_POR_TIPO` | `test_no_maximo_tres_variantes_por_tipo` |
| `_candidatas`: tirar `or regra.get("tipo") not in tipos` (fica `regra.get("tipo") not in CAMPOS`) | `test_tipo_fora_do_catalogo_da_coluna_cai` |
| `propor`: trocar `continue` do `except` por `return candidatas` | `test_falha_do_llm_deixa_so_aquela_coluna_sem_regra` |

- [ ] **Step 5: Medir e commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l     # 12
git ls-files "*.py" ":!tests/" | xargs wc -l | sort -n | tail -4
git add limpeza2/e1_perfil.py limpeza2/e2_detector.py tests/test_e1_perfil.py tests/test_e2_detector.py
git commit -m "e2_detector: catalogo roteado pela conformidade aprovada, variante malformada cai sozinha

Mutacoes executadas: as sete da tarefa 4 do plano da parte 2.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 5: `e4_especificador.py`

**Files:**
- Create: `limpeza2/e4_especificador.py`
- Test: `tests/test_e4_especificador.py`

**Interfaces:**
- Consumes: `provedor`, `motor.detectar`, `motor.ESTRATEGIAS`, `limites.exemplos_do_guia`, `limites.valores_certificados`, `Reparo`.
- Produces:
  - `e4_especificador.especificar(deteccoes, entrada) -> list[Reparo]`. Os parâmetros saem no formato do motor: `normalizar` → `{"transformacao": str}` (o `"funcao"` entra na tarefa 6); `moda_condicionada` → `{"determinantes": [...]}`; `vizinho_no_dominio` → `{"distancia": int, "dominio": [...]}`; `dicionario` → `{"mapa": {sujo: limpo}}`; `esvaziar` → `{}`.
  - Sem proposta válida, `candidata.metricas["motivo_reparo"]` recebe `sem_especificacao` (falha do LLM) ou `especificacao_invalida`.
  - `e4_especificador.dominio(entrada, coluna, mascara) -> list[str]`.
  - `e4_especificador.INSTRUCAO`. O conteúdo tem as linhas `coluna: <nome>` e `regra de deteccao: <tipo> <parametros>`.

- [ ] **Step 1: Testes**

Crie `tests/test_e4_especificador.py`:

```python
"""O especificador: estrategia de catalogo fechado, dominio deterministico, degradacao."""
import pandas as pd
import pytest

from limpeza2 import e4_especificador
from limpeza2.tipos import Candidata
from tests.apoio import CORTADA, monta_entrada


def sujo():
    return pd.DataFrame({
        "estado": ["MA", "MA", "TX", "TX", "XX", "MA", "TX", "MA", "MA", "YY"],
        "cidade": ["Boston", "Boston", "Austin", "Austin", "Boston",
                   "Boston", "Austin", "Boston", "Boston", "Austin"],
    })


def deteccao():
    return Candidata(coluna="estado", tipo="dominio", parametros={"valores": ["MA", "TX"]}, raciocinio="r")


def especificacao(estrategia, **campos):
    base = dict.fromkeys(["transformacao", "determinantes", "distancia", "mapa"])
    return {**base, **campos, "estrategia": estrategia,
            "raciocinio": {"padrao": "Duas letras.", "analise": "XX nao existe.", "acao": "Use a moda."}}


def test_dominio_e_deterministico_e_inclui_o_certificado():
    entrada = monta_entrada(sujo(), linhas_guia=[9], corrigidos={(9, "estado"): "RJ"})
    mascara = pd.Series([False] * 4 + [True] + [False] * 4 + [True])
    assert e4_especificador.dominio(entrada, "estado", mascara) == ["MA", "RJ", "TX"]


@pytest.mark.parametrize("resposta, esperado", [
    (especificacao("normalizar", transformacao="tirar o sufixo"), {"transformacao": "tirar o sufixo"}),
    (especificacao("moda_condicionada", determinantes=["cidade"]), {"determinantes": ["cidade"]}),
    (especificacao("dicionario", mapa=[{"sujo": "XX", "limpo": "MA"}]), {"mapa": {"XX": "MA"}}),
    (especificacao("esvaziar"), {}),
])
def test_converte_cada_estrategia_no_formato_do_motor(roteiro, resposta, esperado):
    roteiro(lambda instrucao, conteudo: resposta)
    [reparo] = e4_especificador.especificar([deteccao()], monta_entrada(sujo()))
    assert (reparo.estrategia, reparo.parametros) == (resposta["estrategia"], esperado)
    assert reparo.raciocinio == "Duas letras. XX nao existe. Use a moda."


def test_vizinho_recebe_o_dominio_calculado_e_nao_o_do_llm(roteiro):
    roteiro(lambda instrucao, conteudo: {**especificacao("vizinho_no_dominio", distancia=1),
                                         "dominio": ["inventado"]})
    [reparo] = e4_especificador.especificar([deteccao()], monta_entrada(sujo()))
    assert reparo.parametros == {"distancia": 1, "dominio": ["MA", "TX"]}


@pytest.mark.parametrize("resposta", [
    especificacao("normalizar", transformacao=""),
    especificacao("moda_condicionada", determinantes=["estado"]),
    especificacao("moda_condicionada", determinantes=["inexistente"]),
    especificacao("vizinho_no_dominio", distancia=7),
    especificacao("dicionario", mapa=[]),
    especificacao("inventada"),
])
def test_especificacao_invalida_nao_vira_proposta(roteiro, resposta):
    roteiro(lambda instrucao, conteudo: resposta)
    c = deteccao()
    assert e4_especificador.especificar([c], monta_entrada(sujo())) == []
    assert c.metricas["motivo_reparo"] == "especificacao_invalida"


def test_falha_do_llm_deixa_a_deteccao_sem_reparo(roteiro):
    roteiro(lambda instrucao, conteudo: CORTADA)
    c = deteccao()
    assert e4_especificador.especificar([c], monta_entrada(sujo())) == []
    assert c.metricas["motivo_reparo"] == "sem_especificacao"


def test_prompt_leva_os_valores_marcados_e_os_exemplos_do_guia(roteiro):
    api = roteiro(lambda instrucao, conteudo: especificacao("esvaziar"))
    entrada = monta_entrada(sujo(), pares=[(4, "estado", "XX", "MA")])
    e4_especificador.especificar([deteccao()], entrada)
    instrucao, conteudo = api.pedidos[0]
    assert instrucao == e4_especificador.INSTRUCAO
    assert "valores marcados (2 celulas): [('XX', 1), ('YY', 1)]" in conteudo
    assert "exemplo do guia: 'XX' -> 'MA'" in conteudo
```

Run: `.venv/Scripts/python -m pytest tests/test_e4_especificador.py -v`
Expected: FAIL com `ImportError`.

- [ ] **Step 2: Implementar `limpeza2/e4_especificador.py`**

```python
"""Etapa 4: agente especificador -> JSON de reparo, uma chamada por deteccao aprovada."""
from limpeza2 import config, provedor
from limpeza2.limites import exemplos_do_guia, valores_certificados
from limpeza2.motor import ESTRATEGIAS, detectar
from limpeza2.tipos import Reparo

INSTRUCAO = """Voce e o agente especificador de uma ferramenta de limpeza de dados.
Recebe uma regra de deteccao ja aprovada e os valores que ela marcou numa coluna. Escolha COMO
corrigi-los, com uma estrategia do catalogo fechado. Voce nao escreve codigo.
- normalizar: transformacao previsivel do texto; descreva-a em "transformacao" com precisao
  (ex.: "remover o sufixo ' oz' e a parte decimal .0"). Um programador a traduzira em Python.
- moda_condicionada: o valor certo e o mais comum entre as linhas que tem o mesmo valor nas
  colunas "determinantes".
- vizinho_no_dominio: o valor certo e o valor valido mais parecido, a ate "distancia" edicoes (1 a 3).
- dicionario: pares literais em "mapa", para o que nao segue padrao.
- esvaziar: o valor marcado significa ausencia e deve virar vazio.
Os exemplos sujo -> limpo do guia sao corretos: a estrategia tem de reproduzi-los.
"raciocinio": tres frases curtas: "padrao" (o que os valores certos seguem), "analise" (o que esta
errado nos marcados) e "acao" (o que fazer). Campos que nao se aplicam vao null. Responda em JSON."""

_LISTA = {"type": ["array", "null"], "items": {"type": "string"}}
_PAR = {"type": "object", "additionalProperties": False, "required": ["sujo", "limpo"],
        "properties": {"sujo": {"type": "string"}, "limpo": {"type": "string"}}}
_COT = {"type": "object", "additionalProperties": False, "required": ["padrao", "analise", "acao"],
        "properties": {k: {"type": "string"} for k in ("padrao", "analise", "acao")}}
ESQUEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["estrategia", "transformacao", "determinantes", "distancia", "mapa", "raciocinio"],
    "properties": {
        "estrategia": {"type": "string", "enum": list(ESTRATEGIAS)},
        "transformacao": {"type": ["string", "null"]}, "determinantes": _LISTA,
        "distancia": {"type": ["integer", "null"]},
        "mapa": {"type": ["array", "null"], "items": _PAR}, "raciocinio": _COT,
    },
}


def especificar(deteccoes, entrada):
    """Uma chamada por deteccao aprovada; devolve as propostas de reparo validas."""
    propostas = []
    for candidata in deteccoes:
        mascara = detectar(entrada.sujo, candidata.coluna, candidata.tipo, candidata.parametros,
                           config.DOMINANCIA_MODA).fillna(False)
        try:
            resposta = provedor.cliente().pedir_json(
                "especificador", f"{candidata.coluna}/{candidata.tipo}", INSTRUCAO,
                _conteudo(candidata, entrada, mascara), ESQUEMA,
            )
        except provedor.FalhaDoLLM:
            # Degradacao nomeada: a deteccao fica sem reparo, e suas celulas viram flag.
            candidata.metricas["motivo_reparo"] = "sem_especificacao"
            continue
        parametros = _parametros(resposta, entrada, candidata.coluna, mascara)
        if parametros is None:
            candidata.metricas["motivo_reparo"] = "especificacao_invalida"
            continue
        propostas.append(Reparo(candidata=candidata, estrategia=resposta["estrategia"],
                                parametros=parametros, raciocinio=_raciocinio(resposta)))
    return propostas


def dominio(entrada, coluna, mascara):
    """Valores nao marcados com duas ou mais ocorrencias, mais os que o guia certifica."""
    contagem = entrada.sujo.loc[~mascara, coluna].value_counts()
    return sorted(set(contagem[contagem >= 2].index) | valores_certificados(entrada, coluna))


def _parametros(resposta, entrada, coluna, mascara):
    """Os parametros da estrategia no formato do motor, ou None se a resposta e invalida."""
    estrategia = resposta.get("estrategia")
    if estrategia == "normalizar":
        texto = resposta.get("transformacao")
        return {"transformacao": texto} if isinstance(texto, str) and texto else None
    if estrategia == "moda_condicionada":
        det = resposta.get("determinantes")
        valido = isinstance(det, list) and det and all(
            c in entrada.sujo.columns and c != coluna for c in det)
        return {"determinantes": det} if valido else None
    if estrategia == "vizinho_no_dominio":
        d = resposta.get("distancia")
        valido = isinstance(d, int) and not isinstance(d, bool) and 1 <= d <= 3
        return {"distancia": d, "dominio": dominio(entrada, coluna, mascara)} if valido else None
    if estrategia == "dicionario":
        mapa = {p["sujo"]: p["limpo"] for p in resposta.get("mapa") or []
                if isinstance(p, dict) and isinstance(p.get("sujo"), str)
                and isinstance(p.get("limpo"), str)}
        return {"mapa": mapa} if mapa else None
    if estrategia == "esvaziar":
        return {}
    return None


def _raciocinio(resposta):
    """As tres frases do CoT, numa linha."""
    cot = resposta.get("raciocinio")
    if not isinstance(cot, dict):
        return ""
    return " ".join(str(cot.get(k) or "") for k in ("padrao", "analise", "acao")).strip()


def _conteudo(candidata, entrada, mascara):
    """A regra, os valores que ela marcou, os exemplos do guia e os pares minerados."""
    coluna = candidata.coluna
    marcados = entrada.sujo.loc[mascara, coluna].value_counts().head(config.VALORES_NO_PROMPT)
    certificados = sorted(valores_certificados(entrada, coluna))[: config.VALORES_NO_PROMPT]
    linhas = [
        f"colunas da tabela: {', '.join(entrada.sujo.columns)}",
        f"coluna: {coluna}",
        f"regra de deteccao: {candidata.tipo} {candidata.parametros}",
        f"raciocinio do detector: {candidata.raciocinio}",
        f"valores marcados ({int(mascara.sum())} celulas): {[(v, int(n)) for v, n in marcados.items()]}",
        f"valores que o guia certifica: {certificados}",
    ]
    linhas += [f"exemplo do guia: {s!r} -> {c!r}" for s, c in exemplos_do_guia(entrada, coluna)]
    linhas += [f"par minerado: {det} -> {coluna}" for det, alvo in entrada.perfil.pares if alvo == coluna]
    return "\n".join(linhas)
```

Run: `.venv/Scripts/python -m pytest`
Expected: tudo passa.

- [ ] **Step 3: Prova por mutação**

| Mutação em `e4_especificador.py` | Teste que tem de falhar |
|---|---|
| `dominio`: tirar `\| valores_certificados(...)` | `test_dominio_e_deterministico_e_inclui_o_certificado` |
| `vizinho_no_dominio`: `"dominio": resposta.get("dominio")` | `test_vizinho_recebe_o_dominio_calculado_e_nao_o_do_llm` |
| `moda_condicionada`: tirar `and c != coluna` | `test_especificacao_invalida_nao_vira_proposta[...estado...]` |
| `vizinho_no_dominio`: tirar `1 <= d <= 3` | `test_especificacao_invalida_nao_vira_proposta[...7...]` |
| no `except`, tirar a linha `motivo_reparo = "sem_especificacao"` | `test_falha_do_llm_deixa_a_deteccao_sem_reparo` |
| `_raciocinio`: só `padrao` | `test_converte_cada_estrategia_no_formato_do_motor` |

- [ ] **Step 4: Medir e commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l     # 13
git add limpeza2/e4_especificador.py tests/test_e4_especificador.py
git commit -m "e4_especificador: estrategia de catalogo fechado, dominio calculado e nao pedido

Mutacoes executadas: as seis da tarefa 5 do plano da parte 2.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 6: `e6_codificador.codificar`

**Files:**
- Create: `limpeza2/e6_codificador.py` (só a parte do primeiro tempo; `escrever` vem na tarefa 8)
- Test: `tests/test_e6_codificador.py`

**Interfaces:**
- Consumes: `portao.materializar`, `portao.testar_fumaca`, `portao.CodigoRejeitado`, `provedor`, `motor.detectar`, `limites.exemplos_do_guia`.
- Produces:
  - `e6_codificador.codificar(propostas, entrada) -> (codificadas: list[Reparo], funcoes: dict[str, callable])`. Para cada `normalizar` aprovada pelo portão: `parametros["funcao"] = "corrigir_<n>"` e `proposta.codigo` recebe o texto. A rejeitada duas vezes fica fora de `codificadas`, com `metricas["motivo_reparo"] = "codigo_rejeitado"` e `metricas["detalhe_reparo"]` com a mensagem do portão.
  - `e6_codificador.INSTRUCAO`.

- [ ] **Step 1: Testes**

Crie `tests/test_e6_codificador.py`:

```python
"""O codificador: funcao escalar pelo portao, uma nova tentativa, e o limpador escrito."""
import pandas as pd

from limpeza2 import e6_codificador
from limpeza2.tipos import Candidata, Reparo
from tests.apoio import monta_entrada

BOM = "def corrigir(valor):\n    return valor.replace(' oz', '')"
RUIM = "def corrigir(valor):\n    import os\n    return valor"


def oncas():
    return pd.DataFrame({"onca": ["12", "12 oz", "16", "16 oz", "16"]})


def proposta(estrategia="normalizar", parametros=None):
    c = Candidata(coluna="onca", tipo="dominio", parametros={"valores": ["12", "16"]}, raciocinio="r")
    return Reparo(candidata=c, estrategia=estrategia,
                  parametros=parametros if parametros is not None else {"transformacao": "tirar ' oz'"},
                  raciocinio="r")


def test_funcao_aprovada_ganha_nome_unico_e_codigo(roteiro):
    roteiro(lambda instrucao, conteudo: {"codigo": BOM})
    primeira, segunda = proposta(), proposta()
    codificadas, funcoes = e6_codificador.codificar([primeira, segunda], monta_entrada(oncas()))
    assert codificadas == [primeira, segunda]
    assert [p.parametros["funcao"] for p in codificadas] == ["corrigir_1", "corrigir_2"]
    assert funcoes["corrigir_1"]("12 oz") == "12"
    assert primeira.codigo == BOM


def test_rejeitada_tenta_de_novo_com_a_mensagem_do_portao(roteiro):
    respostas = [{"codigo": RUIM}, {"codigo": BOM}]
    api = roteiro(lambda instrucao, conteudo: respostas.pop(0))
    codificadas, funcoes = e6_codificador.codificar([proposta()], monta_entrada(oncas()))
    assert len(codificadas) == 1 and "corrigir_1" in funcoes
    assert "A tentativa anterior foi rejeitada: import proibido" in api.pedidos[1][1]


def test_rejeitada_duas_vezes_cai(roteiro):
    api = roteiro(lambda instrucao, conteudo: {"codigo": RUIM})
    p = proposta()
    codificadas, funcoes = e6_codificador.codificar([p], monta_entrada(oncas()))
    assert (codificadas, funcoes) == ([], {})
    assert p.candidata.metricas["motivo_reparo"] == "codigo_rejeitado"
    assert "import proibido" in p.candidata.metricas["detalhe_reparo"]
    assert len(api.pedidos) == 2


def test_funcao_que_lanca_com_valor_real_e_rejeitada(roteiro):
    lanca = "def corrigir(valor):\n    return valor[10]"
    roteiro(lambda instrucao, conteudo: {"codigo": lanca})
    codificadas, _ = e6_codificador.codificar([proposta()], monta_entrada(oncas()))
    assert codificadas == []


def test_estrategia_sem_codigo_passa_sem_chamar_o_llm(roteiro):
    api = roteiro(lambda instrucao, conteudo: {"codigo": BOM})
    p = proposta("esvaziar", {})
    assert e6_codificador.codificar([p], monta_entrada(oncas())) == ([p], {})
    assert api.pedidos == []
```

Run: `.venv/Scripts/python -m pytest tests/test_e6_codificador.py -v`
Expected: FAIL com `ImportError`.

- [ ] **Step 2: Implementar o primeiro tempo de `limpeza2/e6_codificador.py`**

```python
"""Etapa 6: agente codificador -> escreve os artefatos de saida."""
from limpeza2 import config, portao, provedor
from limpeza2.limites import exemplos_do_guia
from limpeza2.motor import detectar

INSTRUCAO = """Voce e o agente codificador de uma ferramenta de limpeza de dados.
Traduza a transformacao pedida numa funcao Python pura, exatamente com esta assinatura:

def corrigir(valor):
    ...
    return novo_valor

Regras: recebe e devolve str; sem import (o modulo re ja esta disponivel); sem arquivo, rede,
eval, exec, getattr nem nomes com __; sem .format (use f-string ou concatenacao).
Se a transformacao nao se aplica ao valor, devolva o valor sem mudanca.
Os exemplos sujo -> limpo do guia sao corretos: a funcao tem de reproduzi-los.
Responda em JSON com o campo "codigo", que contem so a definicao da funcao."""
ESQUEMA = {"type": "object", "additionalProperties": False, "required": ["codigo"],
           "properties": {"codigo": {"type": "string"}}}


def codificar(propostas, entrada):
    """Escreve uma corrigir(valor) por proposta normalizar; devolve (codificadas, funcoes)."""
    codificadas, funcoes = [], {}
    for proposta in propostas:
        if proposta.estrategia == "normalizar":
            funcao = _funcao(proposta, entrada)
            if funcao is None:
                proposta.candidata.metricas["motivo_reparo"] = "codigo_rejeitado"
                continue
            nome = f"corrigir_{len(funcoes) + 1}"
            funcoes[nome] = funcao
            proposta.parametros["funcao"] = nome
        codificadas.append(proposta)
    return codificadas, funcoes


def _funcao(proposta, entrada):
    """Pede o codigo e o passa no portao; uma nova tentativa com a mensagem do portao."""
    c = proposta.candidata
    mascara = detectar(entrada.sujo, c.coluna, c.tipo, c.parametros, config.DOMINANCIA_MODA).fillna(False)
    exemplos = exemplos_do_guia(entrada, c.coluna)
    amostras = sorted(set(entrada.sujo.loc[mascara, c.coluna]))[: config.VALORES_NO_PROMPT]
    conteudo = "\n".join([
        f"coluna: {c.coluna}", f"transformacao: {proposta.parametros['transformacao']}",
        f"valores a corrigir: {amostras}",
        *[f"exemplo do guia: {s!r} -> {limpo!r}" for s, limpo in exemplos],
    ])
    for _ in range(2):
        try:
            resposta = provedor.cliente().pedir_json(
                "codificador", f"{c.coluna}/{c.tipo}", INSTRUCAO, conteudo, ESQUEMA)
            codigo = str(resposta.get("codigo"))
            funcao = portao.materializar(codigo)
            portao.testar_fumaca(funcao, amostras + [s for s, _ in exemplos])
        except provedor.FalhaDoLLM:
            # Degradacao nomeada: a regra fica sem reparo; o motivo esta no registro.
            return None
        except portao.CodigoRejeitado as erro:
            c.metricas["detalhe_reparo"] = str(erro)
            conteudo += f"\n\nA tentativa anterior foi rejeitada: {erro}\ncodigo rejeitado:\n{codigo}"
            continue
        proposta.codigo = codigo
        return funcao
    return None
```

Run: `.venv/Scripts/python -m pytest`
Expected: tudo passa.

- [ ] **Step 3: Prova por mutação**

| Mutação em `e6_codificador.py` | Teste que tem de falhar |
|---|---|
| `range(2)` vira `range(1)` | `test_rejeitada_tenta_de_novo_com_a_mensagem_do_portao` |
| não acrescentar a mensagem do portão ao `conteudo` | `test_rejeitada_tenta_de_novo_com_a_mensagem_do_portao` |
| tirar a chamada a `portao.testar_fumaca` | `test_funcao_que_lanca_com_valor_real_e_rejeitada` |
| `nome = "corrigir_1"` fixo | `test_funcao_aprovada_ganha_nome_unico_e_codigo` |
| acrescentar à `codificadas` também a proposta rejeitada | `test_rejeitada_duas_vezes_cai` |

- [ ] **Step 4: Medir e commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l     # 14
git add limpeza2/e6_codificador.py tests/test_e6_codificador.py
git commit -m "e6_codificador.codificar: funcao escalar pelo portao, uma nova tentativa com a mensagem

Mutacoes executadas: as cinco da tarefa 6 do plano da parte 2.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 7: `e5_residual.py`

**Files:**
- Create: `limpeza2/e5_residual.py`
- Test: `tests/test_e5_residual.py`

**Interfaces:**
- Consumes: `motor.aplicar_regras`, `tipos.regras_literais`, `tipos.Residual`, `provedor` (inclusive `anotar`), `limites.exemplos_do_guia`.
- Produces:
  - `e5_residual.resolver(deteccoes, reparos, funcoes, entrada) -> list[Residual]` (ainda **não** crivado: a espinha chama `crivar_residual`).
  - `e5_residual.lotes_por_entidade(sujo, flags, sujeito) -> list[list[int]]`.
  - `e5_residual.consolidar(respostas) -> list[Residual]`, com `respostas: {(coluna, sujo): {(limpo, justificativa), ...}}`.
  - `e5_residual.INSTRUCAO` e `e5_residual.INSTRUCAO_SUJEITO`.
  - Notas no registro: `("residual", "coluna_sujeito", "escolha", "<coluna>: <raciocinio>")` e `("residual", "lote <n>", "sem_lote", "<k> linhas")`.

- [ ] **Step 1: Testes**

Crie `tests/test_e5_residual.py`:

```python
"""O residual: lotes por entidade deterministicos, consolidacao, teto de lotes."""
import pandas as pd

from limpeza2 import config, e5_residual, provedor
from limpeza2.tipos import Candidata, Perfil
from tests.apoio import CORTADA, monta_entrada


def tabela():
    return pd.DataFrame({
        # B aparece antes de A: a ordem da primeira linha difere da alfabetica.
        "cervejaria": ["B", "A", "B", "C", "A", "B"],
        "estado": ["MA", "TX", "XX", "CA", "YY", "MA"],
    })


def flags_em(df, celulas):
    flags = pd.DataFrame(False, index=df.index, columns=df.columns)
    for linha, coluna in celulas:
        flags.at[linha, coluna] = True
    return flags


def test_lotes_juntam_a_entidade_inteira_na_ordem_da_primeira_linha():
    df = tabela()
    flags = flags_em(df, [(2, "estado"), (4, "estado")])
    assert e5_residual.lotes_por_entidade(df, flags, "cervejaria") == [[0, 2, 5, 1, 4]]


def test_lote_cheio_abre_outro(monkeypatch):
    monkeypatch.setattr(config, "LINHAS_POR_LOTE", 3)
    df = tabela()
    flags = flags_em(df, [(2, "estado"), (4, "estado")])
    assert e5_residual.lotes_por_entidade(df, flags, "cervejaria") == [[0, 2, 5], [1, 4]]


def test_entidade_maior_que_o_lote_guarda_as_linhas_com_flag(monkeypatch):
    monkeypatch.setattr(config, "LINHAS_POR_LOTE", 2)
    df = tabela()
    flags = flags_em(df, [(5, "estado")])
    assert e5_residual.lotes_por_entidade(df, flags, "cervejaria") == [[0, 5]]


def test_sem_sujeito_os_lotes_seguem_a_ordem_das_linhas():
    df = tabela()
    flags = flags_em(df, [(4, "estado"), (2, "estado")])
    assert e5_residual.lotes_por_entidade(df, flags, None) == [[2, 4]]


def test_consolidar_junta_iguais_e_derruba_divergentes():
    respostas = {
        ("estado", "XX"): {("MA", "a cervejaria A e de MA")},
        ("estado", "YY"): {("TX", "j1"), ("CA", "j2")},
    }
    [r] = e5_residual.consolidar(respostas)
    assert r.mapa == {"XX": "MA"}
    assert r.justificativas == {"XX": "a cervejaria A e de MA"}
    assert r.caidas == {"YY": "conflitante: ['CA', 'TX']"}


def entrada_com_deteccao():
    df = tabela()
    entrada = monta_entrada(df)
    entrada.perfil = Perfil(colunas={}, pares={}, candidatas_sujeito=["cervejaria"])
    deteccao = Candidata(coluna="estado", tipo="dominio",
                         parametros={"valores": ["MA", "TX", "CA"]}, raciocinio="r")
    return entrada, [deteccao]


def responder(sujeito, correcoes):
    def responde(instrucao, conteudo):
        if instrucao == e5_residual.INSTRUCAO_SUJEITO:
            return {"coluna": sujeito, "raciocinio": "nomeia a cervejaria"}
        return {"correcoes": correcoes}
    return responde


def test_resolver_ignora_null_igual_e_valor_nao_pedido(roteiro):
    roteiro(responder("cervejaria", [
        {"coluna": "estado", "sujo": "XX", "limpo": "MA", "justificativa": "j"},
        {"coluna": "estado", "sujo": "YY", "limpo": None, "justificativa": "j"},
        {"coluna": "estado", "sujo": "MA", "limpo": "TX", "justificativa": "j"},
        {"coluna": "estado", "sujo": "YY", "limpo": "YY", "justificativa": "j"},
    ]))
    entrada, deteccoes = entrada_com_deteccao()
    [r] = e5_residual.resolver(deteccoes, [], {}, entrada)
    assert r.mapa == {"XX": "MA"}
    nota = next(n for n in provedor.cliente().registro if n["unidade"] == "coluna_sujeito")
    assert nota["detalhe"] == "cervejaria: nomeia a cervejaria"


def test_sem_flag_nao_chama_o_llm(roteiro):
    api = roteiro(responder("cervejaria", []))
    entrada, _ = entrada_com_deteccao()
    assert e5_residual.resolver([], [], {}, entrada) == []
    assert api.pedidos == []


def test_lote_alem_do_teto_vira_sem_lote(roteiro, monkeypatch):
    monkeypatch.setattr(config, "MAX_LOTES_RESIDUAL", 1)
    monkeypatch.setattr(config, "LINHAS_POR_LOTE", 3)
    roteiro(responder("cervejaria", []))
    entrada, deteccoes = entrada_com_deteccao()
    e5_residual.resolver(deteccoes, [], {}, entrada)
    status = [(n["unidade"], n["status"]) for n in provedor.cliente().registro]
    assert ("lote 1", "ok") in status and ("lote 2", "sem_lote") in status


def test_falha_no_lote_so_perde_o_lote(roteiro):
    def responde(instrucao, conteudo):
        if instrucao == e5_residual.INSTRUCAO_SUJEITO:
            return {"coluna": None, "raciocinio": "nenhuma"}
        return CORTADA
    roteiro(responde)
    entrada, deteccoes = entrada_com_deteccao()
    assert e5_residual.resolver(deteccoes, [], {}, entrada) == []
```

Run: `.venv/Scripts/python -m pytest tests/test_e5_residual.py -v`
Expected: FAIL com `ImportError`.

- [ ] **Step 2: Implementar `limpeza2/e5_residual.py`**

```python
"""Etapa 5: rodada residual por entidade -> dicionario congelado no limpador."""
from limpeza2 import config, provedor
from limpeza2.limites import exemplos_do_guia
from limpeza2.motor import aplicar_regras
from limpeza2.tipos import Residual, regras_literais

INSTRUCAO_SUJEITO = """Voce ajuda uma ferramenta de limpeza de dados a agrupar linhas por entidade.
Recebe as colunas da tabela, algumas linhas e as colunas candidatas a identificar a entidade
(a coisa que cada linha descreve: uma cervejaria, uma estacao, um hospital).
Escolha a candidata que NOMEIA a entidade, ou null se nenhuma nomeia.
"raciocinio": uma frase. Responda em JSON."""

INSTRUCAO = """Voce corrige valores que as regras de uma ferramenta de limpeza de dados marcaram
como errados e nao souberam corrigir.
Recebe linhas da mesma entidade, como contexto, e a lista de valores suspeitos, cada um com a coluna.
Linhas da mesma entidade costumam repetir informacao: use essa redundancia.
Para cada valor suspeito, devolva o valor correto em "limpo", ou null se nao tiver certeza ou se o
valor ja estiver certo. Os exemplos sujo -> limpo do guia sao corretos e mostram o formato esperado.
"justificativa": uma frase. Responda em JSON."""

_CORRECAO = {"type": "object", "additionalProperties": False,
             "required": ["coluna", "sujo", "limpo", "justificativa"],
             "properties": {"coluna": {"type": "string"}, "sujo": {"type": "string"},
                            "limpo": {"type": ["string", "null"]}, "justificativa": {"type": "string"}}}
ESQUEMA = {"type": "object", "additionalProperties": False, "required": ["correcoes"],
           "properties": {"correcoes": {"type": "array", "items": _CORRECAO}}}


def resolver(deteccoes, reparos, funcoes, entrada):
    """Pergunta pelos valores marcados que nenhum reparo corrigiu; um Residual por coluna."""
    regras = regras_literais(deteccoes, reparos)
    _, flags, _ = aplicar_regras(entrada.sujo, regras, {}, funcoes, config.DOMINANCIA_MODA)
    if not flags.to_numpy().any():
        return []
    respostas = {}
    for numero, lote in enumerate(lotes_por_entidade(entrada.sujo, flags, _sujeito(entrada)), 1):
        if numero > config.MAX_LOTES_RESIDUAL:
            provedor.cliente().anotar("residual", f"lote {numero}", "sem_lote", f"{len(lote)} linhas")
            continue
        pedidos = {(coluna, entrada.sujo.at[linha, coluna])
                   for linha in lote for coluna in entrada.sujo.columns if flags.at[linha, coluna]}
        try:
            resposta = provedor.cliente().pedir_json(
                "residual", f"lote {numero}", INSTRUCAO, _conteudo(entrada, lote, pedidos), ESQUEMA)
        except provedor.FalhaDoLLM:
            # Degradacao nomeada: as celulas do lote ficam como flag.
            continue
        for item in resposta.get("correcoes") or []:
            chave = (item.get("coluna"), item.get("sujo")) if isinstance(item, dict) else None
            limpo = item.get("limpo") if chave in pedidos else None
            if isinstance(limpo, str) and limpo != chave[1]:
                respostas.setdefault(chave, set()).add((limpo, str(item.get("justificativa") or "")))
    return consolidar(respostas)


def lotes_por_entidade(sujo, flags, sujeito):
    """Lotes de ate LINHAS_POR_LOTE linhas, cada entidade inteira, na ordem da primeira linha."""
    marcadas = flags.any(axis=1)
    if sujeito is None:
        grupos = [[linha] for linha in sujo.index[marcadas]]
    else:
        afetadas = sujo[sujo[sujeito].isin(sujo.loc[marcadas, sujeito])]
        # Quando a entidade nao cabe num lote, a linha com flag vem antes do contexto.
        grupos = [sorted(sorted(g.index, key=lambda i: not marcadas[i])[: config.LINHAS_POR_LOTE])
                  for _, g in afetadas.groupby(sujeito, sort=False)]
    lotes = []
    for grupo in grupos:
        if lotes and len(lotes[-1]) + len(grupo) <= config.LINHAS_POR_LOTE:
            lotes[-1] += grupo
        else:
            lotes.append(list(grupo))
    return lotes


def consolidar(respostas):
    """Um Residual por coluna; respostas divergentes para o mesmo valor saem como conflitante."""
    residuais = {}
    for (coluna, sujo), opcoes in sorted(respostas.items()):
        residual = residuais.setdefault(coluna, Residual(coluna=coluna, mapa={}, justificativas={}))
        limpos = sorted({limpo for limpo, _ in opcoes})
        if len(limpos) > 1:
            residual.caidas[sujo] = f"conflitante: {limpos}"
            continue
        residual.mapa[sujo] = limpos[0]
        residual.justificativas[sujo] = min(j for _, j in opcoes)
    return list(residuais.values())


def _sujeito(entrada):
    """A coluna que nomeia a entidade, escolhida pelo LLM entre as mineradas, ou None."""
    candidatas = entrada.perfil.candidatas_sujeito
    if not candidatas:
        return None
    esquema = {"type": "object", "additionalProperties": False, "required": ["coluna", "raciocinio"],
               "properties": {"coluna": {"type": ["string", "null"], "enum": [*candidatas, None]},
                              "raciocinio": {"type": "string"}}}
    conteudo = (f"colunas: {list(entrada.sujo.columns)}\ncandidatas: {candidatas}\n"
                f"linhas:\n{entrada.sujo.head(10).to_csv()}")
    try:
        resposta = provedor.cliente().pedir_json(
            "residual", "coluna_sujeito", INSTRUCAO_SUJEITO, conteudo, esquema)
    except provedor.FalhaDoLLM:
        # Degradacao nomeada: sem sujeito, os lotes seguem a ordem das linhas.
        return None
    coluna = resposta.get("coluna") if resposta.get("coluna") in candidatas else None
    provedor.cliente().anotar("residual", "coluna_sujeito", "escolha",
                              f"{coluna}: {resposta.get('raciocinio', '')}")
    return coluna


def _conteudo(entrada, lote, pedidos):
    """Os valores suspeitos, os exemplos do guia e as linhas do lote como contexto."""
    linhas = [f"suspeito: coluna {c!r}, valor {v!r}" for c, v in sorted(pedidos)]
    for coluna in sorted({c for c, _ in pedidos}):
        linhas += [f"exemplo do guia em {coluna}: {s!r} -> {limpo!r}"
                   for s, limpo in exemplos_do_guia(entrada, coluna)]
    return "\n".join(linhas) + "\nlinhas da entidade:\n" + entrada.sujo.loc[lote].to_csv()
```

Run: `.venv/Scripts/python -m pytest`
Expected: tudo passa.

- [ ] **Step 3: Prova por mutação**

| Mutação em `e5_residual.py` | Teste que tem de falhar |
|---|---|
| `groupby(sujeito, sort=False)` vira `groupby(sujeito)` | `test_lotes_juntam_a_entidade_inteira_na_ordem_da_primeira_linha` |
| `<=` vira `<` na junção de lotes | `test_lote_cheio_abre_outro` |
| tirar o `sorted(..., key=lambda i: not marcadas[i])` interno | `test_entidade_maior_que_o_lote_guarda_as_linhas_com_flag` |
| `consolidar`: tirar o `if len(limpos) > 1` | `test_consolidar_junta_iguais_e_derruba_divergentes` |
| `resolver`: `limpo != chave[1]` vira `True` | `test_resolver_ignora_null_igual_e_valor_nao_pedido` |
| `resolver`: `chave in pedidos` vira `chave is not None` | `test_resolver_ignora_null_igual_e_valor_nao_pedido` |
| `resolver`: tirar o `if not flags.to_numpy().any()` | `test_sem_flag_nao_chama_o_llm` |
| `numero > config.MAX_LOTES_RESIDUAL` vira `False` | `test_lote_alem_do_teto_vira_sem_lote` |

- [ ] **Step 4: Medir e commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l     # 15
git add limpeza2/e5_residual.py tests/test_e5_residual.py
git commit -m "e5_residual: lotes por entidade deterministicos, consolidacao por valor, teto de lotes

Mutacoes executadas: as oito da tarefa 7 do plano da parte 2.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 8: `e6_codificador.escrever` e o aviso de truncamento no `medir.py`

**Files:**
- Modify: `limpeza2/e6_codificador.py` (segundo tempo)
- Modify: `medir.py` (`avaliar` devolve `truncada` e `degradadas`; `main` avisa)
- Test: `tests/test_e6_codificador.py`, `tests/test_medir.py`

**Interfaces:**
- Consumes: `tipos.regras_literais`, `provedor.cliente()` (`registro`, `chamadas`), `config`.
- Produces:
  - `e6_codificador.escrever(deteccoes, reparos, residual, todas, entrada, destino) -> Path` do limpador. Grava `destino/limpador_<destino.name>.py` e `destino/raciocinio_<destino.name>.md`, importa o limpador e roda `aplicar` sobre o sujo (falha **levanta**).
  - `e6_codificador.MOTOR`, `INICIO`, `FIM`, `renomear(codigo, nome) -> str`.
  - O limpador expõe `aplicar(df) -> (df, flags)`, `aplicar_detalhado(df) -> (df, flags, fontes)`, `GERACAO_TRUNCADA`, `UNIDADES_DEGRADADAS_POR_TETO`, `REGRAS`, `RESIDUAL`, `FUNCOES`, `DOMINANCIA` e `main()`.
  - `medir.avaliar(...)` devolve também `"truncada": bool` e `"degradadas": int`.

- [ ] **Step 1: Testes de `escrever`**

Acrescente a `tests/test_e6_codificador.py` (e `import pytest`, `from limpeza2 import provedor`, `from limpeza2.tipos import Residual` aos imports):

```python
def gerar(tmp_path, roteiro, nome="beers_teste", codigo=BOM, residual=()):
    """Escreve um limpador com uma deteccao de dominio reparada por uma funcao."""
    roteiro(lambda instrucao, conteudo: {})
    entrada = monta_entrada(oncas())
    p = proposta(parametros={"transformacao": "tirar ' oz'", "funcao": "corrigir_1"})
    p.codigo = codigo
    destino = tmp_path / nome
    destino.mkdir(parents=True, exist_ok=True)
    caminho = e6_codificador.escrever([p.candidata], [p], list(residual), [p.candidata], entrada, destino)
    return caminho, entrada


def test_bloco_embutido_e_motor_byte_a_byte(tmp_path, roteiro):
    caminho, _ = gerar(tmp_path, roteiro)
    texto = caminho.read_bytes()
    inicio = (e6_codificador.INICIO + "\n").encode()
    bloco = texto.split(inicio, 1)[1].split(e6_codificador.FIM.encode(), 1)[0]
    assert bloco == e6_codificador.MOTOR.read_bytes()


def test_mesma_entrada_mesmo_texto(tmp_path, roteiro):
    a, _ = gerar(tmp_path / "a", roteiro)
    b, _ = gerar(tmp_path / "b", roteiro)
    assert a.read_bytes() == b.read_bytes()


def test_limpador_aplica_regras_e_residual(tmp_path, roteiro):
    residual = [Residual(coluna="onca", mapa={"16 oz": "16"}, justificativas={"16 oz": "j"})]
    caminho, entrada = gerar(tmp_path, roteiro, residual=residual)
    modulo = carregar(caminho)
    corrigido, flags = modulo.aplicar(entrada.sujo)
    assert list(corrigido["onca"]) == ["12", "12", "16", "16", "16"]
    assert not flags.any(axis=None)
    assert modulo.FUNCOES["corrigir_1"]("12 oz") == "12"
    assert modulo.GERACAO_TRUNCADA is False


def test_teto_atingido_fica_marcado_no_artefato(tmp_path, roteiro):
    roteiro(lambda instrucao, conteudo: {})
    provedor.cliente().anotar("detector", "onca", "teto")
    entrada = monta_entrada(oncas())
    destino = tmp_path / "beers_teto"
    destino.mkdir()
    caminho = e6_codificador.escrever([], [], [], [], entrada, destino)
    modulo = carregar(caminho)
    assert (modulo.GERACAO_TRUNCADA, modulo.UNIDADES_DEGRADADAS_POR_TETO) == (True, 1)


def test_raciocinio_lista_a_reprovada(tmp_path, roteiro):
    reprovada = Candidata(coluna="onca", tipo="faixa", parametros={"minimo": 0, "maximo": 1},
                          raciocinio="chute")
    reprovada.metricas = {"motivo": "marca_demais", "marcadas": 5}
    roteiro(lambda instrucao, conteudo: {})
    destino = tmp_path / "beers_md"
    destino.mkdir()
    e6_codificador.escrever([], [], [], [reprovada], monta_entrada(oncas()), destino)
    md = (destino / "raciocinio_beers_md.md").read_text(encoding="utf-8")
    assert "### faixa: marca_demais" in md
    assert "- marcadas: 5" in md


def test_funcao_quebrada_derruba_a_fumaca_final(tmp_path, roteiro):
    with pytest.raises(NameError):
        gerar(tmp_path, roteiro, codigo="def corrigir(valor):\n    return valor + desconhecida")


def test_renomear_troca_so_o_nome_da_funcao():
    assert e6_codificador.renomear(BOM, "corrigir_7").startswith("def corrigir_7(valor):")


def carregar(caminho):
    import importlib.util
    spec = importlib.util.spec_from_file_location("limpador_teste", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo
```

Run: `.venv/Scripts/python -m pytest tests/test_e6_codificador.py -v`
Expected: os testes novos falham com `AttributeError: module 'limpeza2.e6_codificador' has no attribute 'escrever'`.

- [ ] **Step 2: Implementar `escrever`**

Em `limpeza2/e6_codificador.py`, troque os imports por:

```python
import ast
import importlib.util
import pprint
from pathlib import Path

from limpeza2 import config, portao, provedor
from limpeza2.limites import exemplos_do_guia
from limpeza2.motor import detectar
from limpeza2.tipos import regras_literais

MOTOR = Path(__file__).with_name("motor.py")
INICIO = "# --- motor.py, copia byte a byte: inicio ---"
FIM = "# --- motor.py: fim ---"
```

e acrescente ao fim do arquivo:

```python
RODAPE = '''

def aplicar_detalhado(df):
    """Aplica as regras congeladas; devolve (df corrigido, flags, fontes)."""
    return aplicar_regras(df, REGRAS, RESIDUAL, FUNCOES, DOMINANCIA)


def aplicar(df):
    """Aplica as regras congeladas; devolve (df corrigido, flags)."""
    corrigido, flags, _ = aplicar_detalhado(df)
    return corrigido, flags


def main():
    ap = argparse.ArgumentParser(description="Aplica este limpador a um CSV")
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--flags", help="CSV booleano das celulas marcadas e nao reparadas")
    args = ap.parse_args()
    df = pd.read_csv(args.entrada, dtype=str, keep_default_na=False, na_values=[])
    corrigido, flags = aplicar(df)
    corrigido.to_csv(args.saida, index=False)
    if args.flags:
        flags.to_csv(args.flags, index=False)


if __name__ == "__main__":
    main()
'''


def escrever(deteccoes, reparos, residual, todas, entrada, destino):
    """Grava o limpador e o raciocinio, roda a fumaca final e devolve o caminho do limpador."""
    destino = Path(destino)
    registro = provedor.cliente().registro
    caminho = destino / f"limpador_{destino.name}.py"
    texto = _limpador(deteccoes, reparos, residual, entrada, registro, destino.name)
    # newline="" grava o motor com os bytes que ele tem no disco.
    caminho.write_text(texto, encoding="utf-8", newline="")
    (destino / f"raciocinio_{destino.name}.md").write_text(
        _raciocinio(todas, reparos, residual, entrada, registro, destino.name), encoding="utf-8")
    # Falha aqui e bug do codificador: levanta, perto da causa.
    spec = importlib.util.spec_from_file_location("limpador_gerado", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    modulo.aplicar(entrada.sujo.copy())
    return caminho


def renomear(codigo, nome):
    """O codigo da funcao com outro nome, reescrito pela AST."""
    arvore = ast.parse(codigo)
    arvore.body[0].name = nome
    return ast.unparse(arvore)


def _limpador(deteccoes, reparos, residual, entrada, registro, nome):
    """O texto do limpador: cabecalho, motor lido do disco, literais e funcoes renomeadas."""
    teto = sum(n["status"] == "teto" for n in registro)
    funcoes = [(r.parametros["funcao"], r.codigo) for r in reparos if r.estrategia == "normalizar"]
    motor = MOTOR.read_text(encoding="utf-8", newline="")
    return "\n".join([
        _cabecalho(entrada, nome),
        "import argparse",
        "import re",
        "",
        "# o motor traz o proprio import de pandas",
        f"{INICIO}\n{motor}{FIM}",
        "",
        f"GERACAO_TRUNCADA = {teto > 0}",
        f"UNIDADES_DEGRADADAS_POR_TETO = {teto}",
        f"DOMINANCIA = {config.DOMINANCIA_MODA!r}",
        f"REGRAS = {pprint.pformat(regras_literais(deteccoes, reparos), width=100)}",
        f"RESIDUAL = {pprint.pformat({r.coluna: r.mapa for r in residual if r.mapa}, width=100)}",
        *[f"\n\n{renomear(codigo, funcao)}" for funcao, codigo in funcoes],
        "",
        f"FUNCOES = {{{', '.join(f'{f!r}: {f}' for f, _ in funcoes)}}}",
        RODAPE,
    ])


def _cabecalho(entrada, nome):
    """A docstring do limpador: origem, modelo, braco, aviso do portao e as memorias congeladas."""
    braco = ("sem guia" if entrada.guia_linhas.empty else
             f"guia de {len(entrada.guia_linhas)} linhas e {len(entrada.guia_pares)} pares")
    return (f'"""Limpador gerado pela POC 2 de limpeza de dados: {nome}.\n\n'
            f"Modelo {config.MODELO} ({config.PROVEDOR}), {provedor.cliente().chamadas} chamadas; {braco}.\n\n"
            "AVISO: este arquivo roda SEM o portao AST que validou as funcoes corrigir_* na geracao.\n"
            "Revise antes de usar em producao.\n\n"
            "Memoria congelada: RESIDUAL e o dominio de vizinho_no_dominio valem para valores\n"
            'ja vistos na tabela de geracao; nao cobrem valor inedito.\n"""')


def _raciocinio(todas, reparos, residual, entrada, registro, nome):
    """O Markdown com cada regra proposta, aprovada ou nao, e o porque."""
    reparo_de = {id(r.candidata): r for r in reparos}
    celulas = len(entrada.guia_linhas) * len(entrada.sujo.columns)
    nao_ok = [n for n in registro if n["status"] != "ok"]
    linhas = [f"# Raciocinio do limpador {nome}", "",
              f"- modelo: {config.MODELO} ({config.PROVEDOR}), raciocinio {config.ESFORCO_RACIOCINIO}",
              f"- supervisao: {celulas} celulas do guia + {len(entrada.guia_pares)} pares",
              f"- chamadas: {provedor.cliente().chamadas}; tokens: {sum(n['tokens'] for n in registro)}",
              f"- unidades sem regra pelo teto de chamadas: {sum(n['status'] == 'teto' for n in registro)}"]
    for coluna in entrada.sujo.columns:
        linhas += ["", f"## {coluna}"]
        for c in (c for c in todas if c.coluna == coluna):
            linhas += ["", f"### {c.tipo}: {c.metricas.get('motivo', 'nao avaliada')}", "",
                       f"- parametros: `{c.parametros}`", f"- raciocinio: {c.raciocinio}"]
            linhas += [f"- {chave}: {valor}" for chave, valor in c.metricas.items()]
            r = reparo_de.get(id(c))
            if r is not None:
                linhas += [f"- reparo: {r.estrategia}", f"- raciocinio do reparo: {r.raciocinio}"]
                if r.codigo:
                    linhas += ["", "```python", renomear(r.codigo, r.parametros["funcao"]), "```"]
        for res in (r for r in residual if r.coluna == coluna):
            linhas += ["", "### residual"]
            linhas += [f"- `{s}` -> `{v}`: {res.justificativas.get(s, '')}" for s, v in sorted(res.mapa.items())]
            linhas += [f"- caiu `{s}`: {motivo}" for s, motivo in sorted(res.caidas.items())]
        linhas += [f"- registro: {n['etapa']} {n['unidade']}: {n['status']} {n['detalhe']}"
                   for n in nao_ok if n["unidade"].split("/")[0] == coluna]
    linhas += ["", "## Outras anotacoes do registro", ""]
    linhas += [f"- {n['etapa']} {n['unidade']}: {n['status']} {n['detalhe']}"
               for n in nao_ok if n["unidade"].split("/")[0] not in entrada.sujo.columns]
    return "\n".join(linhas) + "\n"
```

Run: `.venv/Scripts/python -m pytest tests/test_e6_codificador.py -v`
Expected: tudo passa.

- [ ] **Step 3: Teste do truncamento no `medir.py`**

Acrescente a `tests/test_medir.py` (com `import sys` e `from medir import main` se ainda não houver):

```python
def test_limpador_truncado_e_avisado(tmp_path, monkeypatch, capsys):
    sujo = tmp_path / "sujo.csv"
    sujo.write_text("a\nx\n", encoding="utf-8")
    limpador = tmp_path / "limpador_truncado.py"
    limpador.write_text(
        "GERACAO_TRUNCADA = True\nUNIDADES_DEGRADADAS_POR_TETO = 3\n"
        "def aplicar(df):\n    return df.copy(), df != df\n", encoding="utf-8")
    r = avaliar(limpador, sujo, sujo)
    assert (r["truncada"], r["degradadas"]) == (True, 3)
    monkeypatch.setattr(sys, "argv", ["medir", "--limpador", str(limpador),
                                      "--sujo", str(sujo), "--limpo", str(sujo)])
    main()
    assert "AVISO: geracao TRUNCADA" in capsys.readouterr().out


def test_limpador_da_poc_1_nao_e_truncado():
    r = avaliar(FIXTURES / "limpador_beers_congelado.py",
                FIXTURES / "beers_dirty_300.csv", FIXTURES / "beers_clean_300.csv")
    assert r["truncada"] is False
```

Run: `.venv/Scripts/python -m pytest tests/test_medir.py -v`
Expected: os dois novos FAIL com `KeyError: 'truncada'`.

- [ ] **Step 4: Implementar no `medir.py`**

Em `avaliar`, dentro do `with warnings.catch_warnings():`, depois de `fontes = None` do `else`, acrescente (no mesmo nível do `if hasattr`):

```python
        truncada = bool(getattr(modulo, "GERACAO_TRUNCADA", False))
        degradadas = int(getattr(modulo, "UNIDADES_DEGRADADAS_POR_TETO", 0))
```

No dicionário devolvido por `avaliar`, acrescente `"truncada": truncada, "degradadas": degradadas,`. Em `main`, logo depois do `print(f"holdout: ...")`, acrescente:

```python
    if r["truncada"]:
        print(f"AVISO: geracao TRUNCADA pelo teto de chamadas ({r['degradadas']} unidade(s) sem regra); "
              "estes numeros nao sao de uma geracao completa\n")
```

Run: `.venv/Scripts/python -m pytest`
Expected: tudo passa.

- [ ] **Step 5: Prova por mutação**

| Mutação | Teste que tem de falhar |
|---|---|
| tirar o `newline=""` do `caminho.write_text` (no Windows o `\n` vira `\r\n` e o bloco deixa de ser igual) | `test_bloco_embutido_e_motor_byte_a_byte` |
| `pprint.pformat(...)` vira `repr(set(...))` no `RESIDUAL` | `test_mesma_entrada_mesmo_texto` (ou `test_limpador_aplica_regras_e_residual`) |
| `GERACAO_TRUNCADA = {teto > 0}` vira `= False` | `test_teto_atingido_fica_marcado_no_artefato` |
| tirar `modulo.aplicar(entrada.sujo.copy())` | `test_funcao_quebrada_derruba_a_fumaca_final` |
| no `_raciocinio`, iterar `reparo_de` em vez de `todas` | `test_raciocinio_lista_a_reprovada` |
| no `medir.py`, tirar o `print` do aviso | `test_limpador_truncado_e_avisado` |

- [ ] **Step 6: Medir e commitar**

```bash
git ls-files "*.py" ":!tests/" | xargs wc -l | sort -n | tail -4   # e6_codificador.py <= 200
```

Se `e6_codificador.py` passar de 200 linhas, simplifique nesta ordem (spec §6): (1) a tabela genérica de `metricas` já está aplicada; (2) troque a montagem do `.md` linha a linha por um template de string; (3) se ainda não couber, **pare e reabra a conversa com o usuário**. Não corte a fumaça final nem teste algum.

```bash
git add limpeza2/e6_codificador.py medir.py tests/test_e6_codificador.py tests/test_medir.py
git commit -m "e6_codificador.escrever: motor byte a byte, literais deterministicos, fumaca final

O medir.py avisa quando a geracao foi truncada pelo teto de chamadas.
Mutacoes executadas: as seis da tarefa 8 do plano da parte 2.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 9: `espinha.py`, o vazamento em tempo de execução e a ponta a ponta

**Files:**
- Create: `limpeza2/espinha.py`
- Test: `tests/test_espinha.py` (novo), `tests/test_vazamento.py` (um teste)

**Interfaces:**
- Consumes: tudo o que veio antes, com as assinaturas acima.
- Produces:
  - `espinha.gerar_limpador(caminho_sujo, caminho_guia, destino) -> Path` do limpador.
  - CLI: `.venv/Scripts/python -m limpeza2.espinha --sujo <csv> [--guia <pasta>] --nome <dataset>` grava em `saida/<nome>_<AAAA-MM-DD_HHMM>/`.

- [ ] **Step 1: Testes de ponta a ponta**

Crie `tests/test_espinha.py`:

```python
"""A espinha de ponta a ponta, com o duble no lugar do LLM."""
from pathlib import Path

from limpeza2 import e2_detector, e4_especificador, e5_residual, e6_codificador
from limpeza2.espinha import gerar_limpador
from medir import avaliar, linhas_do_guia

RAIZ = Path(__file__).resolve().parent.parent
SUJO = RAIZ / "tests" / "fixtures" / "beers_dirty_300.csv"
LIMPO = RAIZ / "tests" / "fixtures" / "beers_clean_300.csv"
GUIA = RAIZ / "dados" / "guia" / "beers"

CODIGO_ONCA = r'''def corrigir(valor):
    m = re.match(r'\s*(\d+)(\.\d+)?', valor)
    if m is None:
        return valor
    decimal = m.group(2) or ''
    if decimal.strip('0') == '.':
        decimal = ''
    return m.group(1) + decimal'''


def campo(conteudo, nome):
    return next(l.split(": ", 1)[1] for l in conteudo.splitlines() if l.startswith(f"{nome}: "))


def responder_beers(instrucao, conteudo):
    """Um LLM de mentira, deterministico, que conhece so a coluna ounces."""
    if instrucao == e2_detector.INSTRUCAO:
        return {"regras": []}
    if instrucao == e4_especificador.INSTRUCAO:
        estrategia = "normalizar" if campo(conteudo, "coluna") == "ounces" else "esvaziar"
        return {"estrategia": estrategia, "transformacao": "manter so o numero, sem .0",
                "determinantes": None, "distancia": None, "mapa": None,
                "raciocinio": {"padrao": "p", "analise": "a", "acao": "t"}}
    if instrucao == e6_codificador.INSTRUCAO:
        return {"codigo": CODIGO_ONCA}
    if instrucao == e5_residual.INSTRUCAO_SUJEITO:
        return {"coluna": None, "raciocinio": "nenhuma nomeia"}
    if instrucao == e5_residual.INSTRUCAO:
        return {"correcoes": []}
    raise AssertionError("instrucao desconhecida")


def test_gera_limpador_que_o_medir_mede(tmp_path, roteiro):
    roteiro(responder_beers)
    destino = tmp_path / "beers_teste"
    caminho = gerar_limpador(SUJO, GUIA, destino)
    assert caminho == destino / "limpador_beers_teste.py"
    assert (destino / "raciocinio_beers_teste.md").exists()
    assert (destino / "respostas.jsonl").read_text(encoding="utf-8").count("\n") > 0
    fora = linhas_do_guia(GUIA / "guia_linhas.csv", GUIA / "guia_pares.csv")
    r = avaliar(caminho, SUJO, LIMPO, holdout=fora)
    assert r["fontes"].get("conformidade/normalizar", 0) > 0
    assert r["colunas"]["ounces"]["precisao"] == 1.0
    assert r["truncada"] is False


def test_mesma_geracao_mesmo_limpador(tmp_path, roteiro):
    roteiro(responder_beers)
    a = gerar_limpador(SUJO, GUIA, tmp_path / "a" / "beers_teste")
    b = gerar_limpador(SUJO, GUIA, tmp_path / "b" / "beers_teste")
    assert a.read_bytes() == b.read_bytes()


def test_braco_sem_guia_gera_limpador(tmp_path, roteiro):
    roteiro(responder_beers)
    caminho = gerar_limpador(SUJO, None, tmp_path / "beers_sem_guia")
    assert "sem guia" in caminho.read_text(encoding="utf-8")
```

Run: `.venv/Scripts/python -m pytest tests/test_espinha.py -v`
Expected: FAIL com `ImportError` (sem `limpeza2.espinha`).

- [ ] **Step 2: Implementar `limpeza2/espinha.py`**

```python
"""A ordem das etapas, e nada mais."""
import argparse
from datetime import datetime

from limpeza2 import (
    config, conformidade, e1_perfil, e2_detector, e3_crivo, e4_especificador,
    e5_residual, e6_codificador, provedor,
)


def gerar_limpador(caminho_sujo, caminho_guia, destino):
    """Etapas 1 a 6 em ordem: a unica sequencia do projeto."""
    provedor.iniciar(destino)
    entrada = e1_perfil.perfilar(caminho_sujo, caminho_guia)
    conformes = conformidade.candidatas_de_conformidade(entrada)
    schema = e3_crivo.crivar_deteccao(conformes, entrada)
    candidatas = e2_detector.propor(entrada, schema, conformes)
    deteccoes = e3_crivo.crivar_deteccao(schema + candidatas, entrada)
    propostas = e4_especificador.especificar(deteccoes, entrada)
    codificadas, funcoes = e6_codificador.codificar(propostas, entrada)
    reparos = e3_crivo.crivar_reparo(codificadas, entrada, funcoes)
    sugestoes = e5_residual.resolver(deteccoes, reparos, funcoes, entrada)
    residual = e3_crivo.crivar_residual(sugestoes, entrada)
    return e6_codificador.escrever(
        deteccoes, reparos, residual, conformes + candidatas, entrada, destino
    )


def main():
    ap = argparse.ArgumentParser(description="Gera o limpador de um CSV sujo")
    ap.add_argument("--sujo", required=True)
    ap.add_argument("--guia", help="pasta com guia_linhas.csv e guia_pares.csv; sem ela, braco sem guia")
    ap.add_argument("--nome", required=True, help="nome do dataset, usado no nome dos arquivos")
    args = ap.parse_args()
    destino = config.SAIDA / f"{args.nome}_{datetime.now():%Y-%m-%d_%H%M}"
    print(f"limpador: {gerar_limpador(args.sujo, args.guia, destino)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run: `.venv/Scripts/python -m pytest tests/test_espinha.py -v`
Expected: 3 passed. Se `test_gera_limpador_que_o_medir_mede` falhar na precisão de `ounces`, abra o `.md` em `tmp_path` e veja o `motivo_reparo` da conformidade de `ounces`: o dublê é que precisa reproduzir os exemplos do guia, não o código de produção.

- [ ] **Step 3: Vazamento em tempo de execução**

Acrescente a `tests/test_vazamento.py`:

```python
def test_geracao_so_abre_o_sujo_o_guia_e_o_motor(tmp_path, roteiro, monkeypatch):
    import builtins
    import io

    import pandas as pd

    from limpeza2 import e6_codificador
    from limpeza2.espinha import gerar_limpador

    raiz = PACOTE.parent
    sujo = raiz / "tests" / "fixtures" / "beers_dirty_300.csv"
    guia = raiz / "dados" / "guia" / "beers"
    destino = tmp_path / "beers_vazamento"
    roteiro(lambda instrucao, conteudo: {})
    abertos = []
    ler_csv, abrir = pd.read_csv, io.open

    def espia_csv(caminho, *args, **kwargs):
        abertos.append(Path(caminho).resolve())
        return ler_csv(caminho, *args, **kwargs)

    def espia_open(arquivo, *args, **kwargs):
        if isinstance(arquivo, (str, Path)):
            abertos.append(Path(arquivo).resolve())
        return abrir(arquivo, *args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", espia_csv)
    monkeypatch.setattr(io, "open", espia_open)
    monkeypatch.setattr(builtins, "open", espia_open)
    gerar_limpador(sujo, guia, destino)

    permitidos = {sujo.resolve(), (guia / "guia_linhas.csv").resolve(),
                  (guia / "guia_pares.csv").resolve(), e6_codificador.MOTOR.resolve()}
    assert abertos, "nada foi aberto: a espia nao estaria espiando"
    intrusos = [p for p in abertos if p not in permitidos and destino.resolve() not in p.parents]
    assert not intrusos, f"a geracao abriu {intrusos}: so o sujo, o guia e o motor podem ser lidos"
```

Run: `.venv/Scripts/python -m pytest tests/test_vazamento.py -v`
Expected: tudo passa.

- [ ] **Step 4: Prova por mutação**

| Mutação | Teste que tem de falhar |
|---|---|
| em `espinha.py`, `crivar_deteccao(schema + candidatas, ...)` vira `crivar_deteccao(candidatas, ...)` | `test_gera_limpador_que_o_medir_mede` (a conformidade some do limpador) |
| em `espinha.py`, `crivar_reparo(codificadas, entrada, funcoes)` vira `crivar_reparo(codificadas, entrada, {})` | `test_gera_limpador_que_o_medir_mede` |
| em `e1_perfil._ler_guia`, ler também `pasta.parent.parent.parent / "tests" / "fixtures" / "beers_clean_300.csv"` com `pd.read_csv` e descartar | `test_geracao_so_abre_o_sujo_o_guia_e_o_motor` |
| em `e6_codificador._limpador`, acrescentar `datetime.now()` ao cabeçalho | `test_mesma_geracao_mesmo_limpador` |

- [ ] **Step 5: Medir e commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l                              # 16
git ls-files "*.py" ":!tests/" | xargs wc -l | tail -1               # <= 1800
git ls-files "*.py" ":!tests/" | xargs wc -l | sort -n | tail -4     # maior <= 200
.venv/Scripts/python -m pytest
git add limpeza2/espinha.py tests/test_espinha.py tests/test_vazamento.py
git commit -m "espinha: a sequencia unica, com vazamento vigiado em execucao e ponta a ponta

Mutacoes executadas: as quatro da tarefa 9 do plano da parte 2.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 10: Documentos

**Files:**
- Modify: `docs/DECISOES.md`, `docs/REGRAS_DO_LIMPADOR.md` (§7), `CLAUDE.md` (§9), `docs/CONTINUACAO.md`

**Interfaces:** nenhuma de código. Esta tarefa não acrescenta `.py`.

- [ ] **Step 1: `docs/DECISOES.md`**

Em `## Provedor desconhecido falha alto {#provedor}`, troque a linha "**Provedor desta POC.** OpenAI, modelo `gpt-5.6-luna`, nome e chave no `.env`." por:

```markdown
**Provedor desta POC.** OpenAI, modelo `gpt-6-luna` com `reasoning_effort="none"`,
nome e chave no `.env`. Escolhido em 12/10/2026 por ser o da faixa barata na
página oficial de comparação da OpenAI nessa data; o `gpt-5.6-luna`, escolhido no
design, já não aparecia nela e custa o dobro. Raciocínio em `none` porque só assim
o modelo aceita `temperature` e não gasta tokens ocultos que podem cortar a
resposta. O terceiro valor de `PROVEDOR`, `gravado`, reproduz um run a partir do
`respostas.jsonl`.

**Ressalva de método, obrigatória ao reportar.** A POC 1 rodou com `gpt-4o-mini` e
é somente leitura. Toda comparação com o placar dela muda método e modelo ao mesmo
tempo; a diferença não se atribui só ao método.
```

Acrescente ao fim do arquivo:

```markdown
---

## Roteamento do detector pela conformidade aprovada {#roteamento-do-detector}

**Decisão.** Na coluna cuja conformidade foi **aprovada pelo crivo**, o detector
não recebe o tipo `formato`; nas outras, recebe o catálogo inteiro. `dependencia`
só entra onde a coluna é lado determinado de algum par minerado.

**Por quê.** A conformidade responde "o valor tem a forma certa?" a partir de dado
certificado, e um `formato` do LLM faria a mesma pergunta com resposta pior; sem o
portão da união, ele só somaria falso positivo. `dominio`, `faixa` e
`ausente_disfarcado` perguntam outra coisa (`Freedonia` tem forma de país, `9999`
conforma a `9`, `0` também) e ficam. O critério é a aprovação, e não ter schema: a
conformidade de `Project_Name` é reprovada (`perde_par_do_guia`), e com "ter
schema" a coluna ficaria sem regra de forma nenhuma. A abstenção da conformidade
vai ao prompt como frase (aprovada, reprovada com motivo, vácua) e orienta sem
restringir.

---

## Reprodutível dadas as respostas {#determinismo-da-geracao}

**Decisão.** `temperature=0` e `seed` fixa quando o provedor aceita, e cada
resposta crua gravada em `respostas.jsonl`. `PROVEDOR=gravado` refaz a geração a
partir dele.

**Por quê.** A geração por LLM não é reprodutível bit a bit, nem com temperatura
zero. O invariante do `CLAUDE.md` §8 trava o **artefato congelado** e a geração a
partir das respostas congeladas; diferença entre dois runs pagos não é regressão.

---

## Falha de API tem nome {#falha-de-api}

**Decisão.** O provedor converte o que a API devolve em `FalhaDoLLM` com um de
cinco motivos: `rede` (tentativas do SDK esgotadas), `cortada`
(`finish_reason == "length"`, o `LengthFinishReasonError` que quebrou o
`Eco_Status` na POC 1), `recusada`, `json_invalido` e `teto` (`TETO_CHAMADAS`
atingido). Cada agente tem um `except FalhaDoLLM`, e a unidade fica sem regra.
Autenticação e modelo inexistente **não** viram `FalhaDoLLM`: derrubam o run.

**Por quê.** Degradar coluna por coluna gastaria 60 chamadas para descobrir uma
chave errada. Um run truncado pelo teto carrega a marca no próprio limpador
(`GERACAO_TRUNCADA`), no `.md` e na saída do `medir.py`.

---

## `reparada` significa "o valor mudou" {#reparada-e-mudanca}

**Decisão.** Em toda estratégia, `reparar` só marca `reparada` onde o valor mudou.

**Por quê.** Antes, `dicionario` com `{v: v}` e `vizinho_no_dominio` que devolvia o
próprio valor contavam como reparo sem mudar nada, e uma regra assim passaria pelo
`nao_repara` do crivo. Mudança de comportamento num caso de borda, feita junto com
a simplificação do `reparar` na parte 2.
```

Em `## O residual é congelado como dicionário {#residual-congelado}`, acrescente ao fim da seção:

```markdown
**O veto por valor certificado não tem exceção no dicionário.** Na detecção,
`dependencia` pode marcar valor certificado, porque o erro está no contexto da
linha (49 das 54 células erradas de `State` carregam valor certificado). No
dicionário não pode, porque a chave não carrega contexto: na tabela de origem,
dois `HH` marcados que pedem correções diferentes dão `conflitante`, mas numa
tabela nova todo `HH` marcado viraria `MA`. Custo: o residual perde o erro
contextual que tinha correção única na tabela de origem; esse fica para a
`moda_condicionada`.

**No braço sem guia, o dicionário passa sem filtro.** As três condições de
`crivar_residual` dependem do guia. É parte do que o braço mede: o residual sem
supervisão. O que limita o alcance é estrutural: o dicionário só age em célula que
uma detecção aprovada marcou.

**O domínio de `vizinho_no_dominio` também é memória.** Calculado na tabela de
geração e congelado como literal, vale para valores já vistos e não cobre valor
inédito.
```

Em `## Portão AST {#portao-ast}`, acrescente ao fim da seção:

```markdown
**O limpador entregue importa o `re` inteiro.** O portão dá ao LLM um proxy de `re`
com as funções permitidas e as flags; o limpador, que roda sem portão por desenho,
faz `import re`. Não é inconsistência: o portão protege a geração, e o cabeçalho
do limpador avisa que ele roda sem portão.
```

Em `## Conformidade de schema {#conformidade-de-schema}`, acrescente ao fim da seção:

```markdown
**O corte fica em um terço, com custo conhecido.** `brewery-name` passa a ter
schema (6 padrões) e a conformidade marca 31 células com precisão 0,000 na
detecção. Um corte de um quarto a excluiria, mas seria o primeiro limiar do
projeto escolhido olhando a resposta, e contaminaria a defesa de `TETO_MARCACAO`,
`DET_MINIMO` e da margem do teto. A métrica é de reparo: marcação que ninguém
reescreve vira flag e não entra na precisão. No primeiro run mede-se o destino
das 31, pela decomposição por fonte. **Ideia registrada, não implementada:** o
que distingue `brewery-name` de `ounces` é a forma dos padrões (`Aa Aa Aa` contra
`9`); schema com espaço ou muitas alternâncias de classe é texto livre, e isso se
observa sem gabarito.
```

- [ ] **Step 2: `docs/REGRAS_DO_LIMPADOR.md` §7**

Na seção `### A limitação, dita com clareza`, acrescente ao fim:

```markdown
O dicionário não é a única memória. O **domínio** da estratégia
`vizinho_no_dominio` — os valores da coluna que aparecem duas ou mais vezes sem
marca, mais os que o guia certifica — também é calculado na tabela de geração e
congelado no limpador. Numa tabela nova, um valor válido que nunca apareceu na de
geração não está nele.

No **braço sem guia**, o dicionário entra no limpador sem filtro nenhum: as três
condições que derrubam uma entrada dependem do guia. Os números desse braço medem,
entre outras coisas, o residual sem supervisão.
```

- [ ] **Step 3: `CLAUDE.md` §9**

Substitua o bloco de código da espinha por:

```python
def gerar_limpador(caminho_sujo, caminho_guia, destino):
    """Etapas 1 a 6 em ordem: a unica sequencia do projeto."""
    provedor.iniciar(destino)
    entrada = e1_perfil.perfilar(caminho_sujo, caminho_guia)
    conformes = conformidade.candidatas_de_conformidade(entrada)
    schema = e3_crivo.crivar_deteccao(conformes, entrada)
    candidatas = e2_detector.propor(entrada, schema, conformes)
    deteccoes = e3_crivo.crivar_deteccao(schema + candidatas, entrada)
    propostas = e4_especificador.especificar(deteccoes, entrada)
    codificadas, funcoes = e6_codificador.codificar(propostas, entrada)
    reparos = e3_crivo.crivar_reparo(codificadas, entrada, funcoes)
    sugestoes = e5_residual.resolver(deteccoes, reparos, funcoes, entrada)
    residual = e3_crivo.crivar_residual(sugestoes, entrada)
    return e6_codificador.escrever(
        deteccoes, reparos, residual, conformes + candidatas, entrada, destino
    )
```

Troque o parágrafo seguinte ("O crivo aparece duas vezes porque...") por:

```markdown
O crivo aparece quatro vezes: sobre a conformidade, para o detector saber onde ela
já cobre a forma; sobre todas as detecções; sobre os reparos; e sobre o dicionário
residual. O codificador aparece duas: escreve as funções `corrigir` antes do crivo
do reparo, que precisa delas, e monta os arquivos no fim. A validação não está na
espinha: é a outra fase, `medir.medir(...)`. Detalhe na spec da parte 2.
```

Na seção "Tipos que viajam", troque a linha de `Entrada` e a de `Residual` por:

```markdown
`Entrada` (sujo, guia_linhas, guia_pares, perfil) ·
`Candidata` (coluna, tipo, parametros, raciocinio, metricas) ·
`Reparo` (candidata, estrategia, parametros, raciocinio, codigo) ·
`Residual` (coluna, mapa, justificativas, caidas) ·
`regras_literais(deteccoes, reparos)`, a forma em que as regras viajam até o limpador.
```

Na árvore de módulos, troque a linha de `espinha.py` por
`  espinha.py            # a ordem das etapas, e nada mais (e o CLI de geracao)`
e, na linha de `motor.py`, troque o comentário por
`# UNICA implementacao de aplicacao de regra (inclui padrao e aplicar_regras)`.

- [ ] **Step 4: `docs/CONTINUACAO.md`**

Substitua as seções 1 e 7 para descrever o estado novo: 16 arquivos, as linhas
medidas no Step 5 da tarefa 9, a contagem de testes da última execução da suíte,
"a parte 2 está implementada com dublê; nenhuma chamada de API foi feita", e a
seção 7 passa a ser a tarefa 12 deste plano (o run pago em degraus) mais a
medição nas linhas nunca vistas, que fica **fora deste plano** (exige preparar a
fatia de 700 e de 2.110 linhas a partir do arquivo completo, renomeando
`beer_name`/`brewery_name` para a grafia com hífen, e isso lê o CSV limpo: tem de
morar fora de `limpeza2/`). Use os números reais das medições, não estimativas.

- [ ] **Step 5: Commitar**

```bash
git add docs/DECISOES.md docs/REGRAS_DO_LIMPADOR.md CLAUDE.md docs/CONTINUACAO.md
git commit -m "Documentos da parte 2: decisoes, memorias congeladas, espinha e estado

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 11: Revisão da parte 2 antes do run

**Files:** nenhum novo.

- [ ] **Step 1: Suíte e teto**

```bash
.venv/Scripts/python -m pytest
git ls-files "*.py" ":!tests/" | wc -l                              # 16
git ls-files "*.py" ":!tests/" | xargs wc -l | tail -1               # <= 1800
git ls-files "*.py" ":!tests/" | xargs wc -l | sort -n | tail -4     # maior <= 200
```

- [ ] **Step 2: Frase por arquivo**

Para cada um dos 16 arquivos, leia a docstring do módulo e confira que ela cabe numa frase sem "e" que diz o que o arquivo faz. Anote os que não cabem e reporte; não fracione sem aprovação.

- [ ] **Step 3: Revisão de código**

Use `superpowers:requesting-code-review` sobre o diff `main...parte-2-agentes`. Corrija o que for defeito; leve ao usuário o que for desenho.

---

## Task 12: O primeiro run pago, em degraus

**Cada degrau é anunciado ao usuário com o número de chamadas e só roda com o "sim" dele.** Nenhum degrau começa sozinho.

**Files:**
- Create (no degrau 2, se o limpador prestar): `tests/fixtures/limpador_beers_poc2.py`, `tests/fixtures/respostas_beers_poc2.jsonl`, `tests/test_invariante.py`

- [ ] **Step 1: O usuário cria o `.env`**

Peça ao usuário que copie `.env.exemplo` para `.env` e cole a chave. Não leia nem imprima a chave.

- [ ] **Step 2: Degrau 1, a sonda (1 chamada). Anuncie e espere o "sim".**

```bash
.venv/Scripts/python - <<'EOF'
from limpeza2 import provedor
c = provedor.iniciar("saida/sonda")
esquema = {"type": "object", "additionalProperties": False, "required": ["ok"],
           "properties": {"ok": {"type": "boolean"}}}
print(c.pedir_json("sonda", "sonda", "Responda em JSON.", "Devolva ok = true.", esquema))
print(c.registro)
EOF
```

Expected: `{'ok': True}` e um registro com `tokens`. Se a API recusar `temperature`, `seed` ou `reasoning_effort` (erro 400 que derruba o run), ponha o parâmetro recusado como `None` em `config.py`, registre em `DECISOES.md#provedor` e repita. Se recusar `json_schema` estrito, ponha `SAIDA_ESTRITA = False`, registre e repita.

- [ ] **Step 3: Degrau 2, `beers` com guia (~40 chamadas, teto 80). Anuncie e espere o "sim".**

```bash
.venv/Scripts/python -m limpeza2.espinha --sujo tests/fixtures/beers_dirty_300.csv --guia dados/guia/beers --nome beers
.venv/Scripts/python medir.py --limpador saida/<pasta>/limpador_<pasta>.py --sujo tests/fixtures/beers_dirty_300.csv --limpo tests/fixtures/beers_clean_300.csv --guia dados/guia/beers
```

Reporte ao usuário, com precisão **ao lado** de recall: a tabela do `medir.py`, os acertos por fonte, as chamadas e os tokens, a marca de truncamento, e **o destino das 31 marcações da `brewery-name`** (quantas a decomposição mostra como reescritas e quantas viraram flag). Compare com o placar da POC 1 (24,4% de recall) **com a ressalva de que modelo e método mudaram juntos**.

- [ ] **Step 4: Congelar o invariante, se o usuário disser que o limpador presta**

```bash
cp saida/<pasta>/limpador_<pasta>.py tests/fixtures/limpador_beers_poc2.py
cp saida/<pasta>/respostas.jsonl tests/fixtures/respostas_beers_poc2.jsonl
```

Crie `tests/test_invariante.py`. Os números do primeiro teste são os que o `medir.py` imprimiu no Step 3, copiados exatamente; o nome da pasta do segundo teste é o `<pasta>` do run:

```python
"""Invariante: os numeros do limpador congelado e a geracao a partir das respostas congeladas."""
from pathlib import Path

from limpeza2 import config
from limpeza2.espinha import gerar_limpador
from medir import avaliar, linhas_do_guia

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
GUIA = RAIZ / "dados" / "guia" / "beers"
SUJO = FIXTURES / "beers_dirty_300.csv"


def test_numeros_do_limpador_congelado():
    fora = linhas_do_guia(GUIA / "guia_linhas.csv", GUIA / "guia_pares.csv")
    r = avaliar(FIXTURES / "limpador_beers_poc2.py", SUJO, FIXTURES / "beers_clean_300.csv", holdout=fora)
    t = r["total"]
    # Copiados do medir.py no run de <data>; mudar e bug, ver CLAUDE.md secao 8.
    assert (t["erros"], t["mudancas"], t["tp"], t["flags"]) == (ERROS, MUDANCAS, TP, FLAGS)


def test_geracao_a_partir_das_respostas_reproduz_o_limpador(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROVEDOR", "gravado")
    monkeypatch.setattr(config, "RESPOSTAS_GRAVADAS", str(FIXTURES / "respostas_beers_poc2.jsonl"))
    caminho = gerar_limpador(SUJO, GUIA, tmp_path / "<pasta>")
    assert caminho.read_bytes() == (FIXTURES / "limpador_beers_poc2.py").read_bytes()
```

Substitua `ERROS, MUDANCAS, TP, FLAGS` pelos quatro inteiros da linha TOTAL do `medir.py`, e `<data>` e `<pasta>` pelos do run. Prova por mutação: troque um dos quatro inteiros e veja o primeiro teste falhar; mude uma linha do `INSTRUCAO` do detector e veja o segundo falhar com `KeyError` (a resposta não foi gravada para aquele prompt). Reverta e commite:

```bash
git add tests/fixtures/limpador_beers_poc2.py tests/fixtures/respostas_beers_poc2.jsonl tests/test_invariante.py
git commit -m "Invariante: limpador do beers congelado e reproduzivel a partir das respostas

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Degrau 3, `environment` com guia e os dois braços sem guia (~120 chamadas). Anuncie e espere o "sim".**

```bash
.venv/Scripts/python -m limpeza2.espinha --sujo tests/fixtures/environment_dirty_300.csv --guia dados/guia/environment --nome environment
.venv/Scripts/python -m limpeza2.espinha --sujo tests/fixtures/beers_dirty_300.csv --nome beers_sem_guia
.venv/Scripts/python -m limpeza2.espinha --sujo tests/fixtures/environment_dirty_300.csv --nome environment_sem_guia
```

Meça cada um com o `medir.py` (os braços sem guia **sem** `--guia`, então sem holdout — diga isso ao reportar). Reporte os quatro braços lado a lado, com precisão ao lado de recall, o orçamento de supervisão de cada um e a ressalva do modelo.

---

## O que este plano NÃO entrega

- **A medição nas linhas nunca vistas** (700 do `environment`, 2.110 do `beers`): exige montar as fatias a partir do arquivo completo, lendo o CSV limpo, e isso tem de morar fora de `limpeza2/`. Fica registrado no `CONTINUACAO.md` como próximo passo.
- **Generalização entre datasets** (`hospital`, `flights`, `rayyan`).
- **O discriminador de schema pela forma dos padrões**, registrado como ideia no `DECISOES.md`.

## Auto-revisão deste plano

- **Cobertura da spec:** §1 → tarefa 0; §2 (espinha) → tarefa 9; §3.1 → tarefa 3; §3.2 → tarefa 4; §3.3 → tarefa 5; §3.4 → tarefa 6; §3.5 → prompts como constantes nas tarefas 4 a 7; §4 → tarefas 1 e 2; §5 → tarefas 2 e 7; §6 → tarefa 8; §7 → tarefa 12; §8 → tarefa 10 e degrau 2; §9 → testes de cada tarefa e invariante na 12; §10 → medição em toda tarefa; §11 → a ordem das tarefas; §12 → a regra de parada da tarefa 8 e os degraus da 12.
- **Contagem de testes:** os números esperados até a tarefa 3 são exatos; a partir da 4, "tudo passa" — conte e registre o número no commit.
- **Assinaturas conferidas entre tarefas:** `propor(entrada, schema, conformes)`, `codificar -> (codificadas, funcoes)`, `crivar_residual(residuais, entrada)`, `aplicar_regras(df, regras, residual, funcoes, dominancia)`, `regras_literais(deteccoes, reparos)`, `Cliente.anotar(etapa, unidade, status, detalhe)`.
