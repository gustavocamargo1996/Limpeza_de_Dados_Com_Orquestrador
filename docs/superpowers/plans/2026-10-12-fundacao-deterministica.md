# Fundação determinística — Plano de implementação (parte 1 de 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir e verificar toda a metade da POC que não usa LLM — guia, métrica, portão, motor de regras, perfil e crivo — de modo que a parte 2 só precise acoplar os três agentes.

**Architecture:** Oito tarefas, nenhuma gastando API. A métrica é ancorada no placar da POC 1, que reproduz exatamente. O motor de aplicação de regra nasce como fonte única, e o crivo o consome. A parte 2 (`docs/superpowers/plans/`, a escrever quando esta ficar verde) acopla detector, especificador, residual, codificador e espinha.

**Tech Stack:** Python 3.12, pandas, pytest, uv. Sem sklearn: a razão de determinação é pandas puro.

**Spec:** [`docs/superpowers/specs/2026-10-11-geracao-de-limpador-design.md`](../specs/2026-10-11-geracao-de-limpador-design.md). Regras em linguagem de usuário: [`docs/REGRAS_DO_LIMPADOR.md`](../../REGRAS_DO_LIMPADOR.md). Decisões com âncoras: [`docs/DECISOES.md`](../../DECISOES.md).

## Global Constraints

Valores copiados literalmente do `CLAUDE.md` e do spec. Valem em toda tarefa.

- **Idioma:** português do Brasil em identificadores, docstrings, comentários, logs, documentos, commits e respostas. Exceções: nomes de bibliotecas (`pd.Series`, `random_state`) e colunas dos datasets.
- **Sem acento em identificadores e em strings de log.** O stdout do Windows abre em cp1252. Documentos usam acentuação normal.
- **Docstring de 1 linha.** Não cabendo em uma linha, o raciocínio vai para `docs/DECISOES.md` e o código guarda a âncora.
- **Comentário inline: no máximo 2 linhas**, descrevendo a mecânica. Proibido comentar histórico, medição, comparação com outros sistemas ou planos.
- **Exceção só com degradação nomeada.** Nenhum `try` genérico.
- **Teto de tamanho:** 13 arquivos `.py` fora de `tests/`, e **15 no limite, só com necessidade demonstrada**; 1.400 linhas no total; 200 linhas no maior arquivo. Todo arquivo cabe numa frase que diz o que ele faz; se a frase tiver "e", o arquivo faz duas coisas. **Nunca fracione para caber no teto de linhas.**
- **Medir antes de todo commit que acrescenta código:** `git ls-files "*.py" ":!tests/" | wc -l` e `git ls-files "*.py" ":!tests/" | xargs wc -l | tail -1`.
- **Carga de CSV sempre literal:** `pd.read_csv(p, dtype=str, keep_default_na=False, na_values=[])`.
- **Nenhum teste gasta API.**
- **Todo teste novo vem com prova por mutação:** quebre o código de propósito, veja o teste falhar, reverta. O plano traz a mutação exata de cada teste; registre no commit que ela foi executada.
- **O CSV limpo só pode ser aberto por `preparar_guia.py` e `medir.py`**, ambos fora do pacote `limpeza2/`.
- **Python:** `.venv` criado com uv, que não instala `pip` dentro. Instale com `uv pip install -r requirements.txt`. Rode com `.venv/Scripts/python`.
- **Datasets:** `C:\Users\gusta\projects\Limpeza_de_Dados\ZeroDC\datasets`. **`C:\Users\gusta\projects\Limpeza_de_Dados\POC_Limpeza_de_Dados` é somente leitura.**

## Estrutura de arquivos desta parte

| Arquivo | Responsabilidade (uma frase) | Tarefa |
|---|---|---|
| `requirements.txt` | as dependências | 1 |
| `pyproject.toml` | configuração do pytest | 1 |
| `limpeza2/tipos.py` | o que viaja entre etapas | 1 |
| `limpeza2/config.py` | caminhos, limiares, semente, modelo | 1 |
| `tests/test_vazamento.py` | a geração nunca alcança o CSV limpo | 1 |
| `preparar_guia.py` | sorteia o guia com semente fixa | 2 |
| `medir.py` | executa o limpador gerado e mede | 3 |
| `limpeza2/portao.py` | valida o Python gerado antes de deixá-lo rodar | 4 |
| `limpeza2/motor.py` | única implementação de aplicação de regra | 5 e 6 |
| `limpeza2/e1_perfil.py` | perfila a tabela suja, lida como texto literal | 7 |
| `limpeza2/e3_crivo.py` | reprova a regra candidata que não se sustenta | 8 |

Fora desta parte, na parte 2: `provedor.py`, `e2_detector.py`, `e4_especificador.py`, `e5_residual.py`, `e6_codificador.py`, `espinha.py`.

---

## Task 1: Esqueleto, tipos, config e o teste de vazamento

**Files:**
- Create: `requirements.txt`, `pyproject.toml`, `.env.exemplo`
- Create: `limpeza2/__init__.py`, `limpeza2/tipos.py`, `limpeza2/config.py`
- Test: `tests/test_vazamento.py`

**Interfaces:**
- Consumes: nada.
- Produces: `limpeza2.tipos.{Perfil, Entrada, Candidata, Reparo, Residual}`; `limpeza2.config.{DATASETS, GUIA, SAIDA, LER_CSV, SEMENTE, LINHAS_GUIA, PARES_POR_COLUNA, TETO_MARCACAO, DOMINANCIA_MODA, TETO_AMBIGUIDADE, DET_MINIMO, GRUPOS_MINIMOS, VARIANTES_POR_TIPO, PROVEDOR, MODELO}`.

- [ ] **Step 1: Criar o ambiente**

```bash
cd "c:/Users/gusta/projects/Limpeza_de_Dados/POC_Limpeza_de_Dados_2"
uv venv
printf '%s\n' 'pandas>=2.2' 'openai>=1.40' 'python-dotenv>=1.0' 'pytest>=8.0' > requirements.txt
uv pip install -r requirements.txt
```

- [ ] **Step 2: Configurar o pytest**

Criar `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
pythonpath = ["."]
```

`pythonpath = ["."]` não é opcional: sem ele, o modo de import padrão do pytest insere `tests/` no `sys.path` e nenhum `from limpeza2...`, `from preparar_guia...` ou `from medir...` resolve. Exige pytest ≥ 7, e o `requirements.txt` pede ≥ 8.

Se em algum momento o `uv` reclamar da falta de um `[project]` no `pyproject.toml`, mova esta configuração para um `pytest.ini` com a seção `[pytest]` e as mesmas três chaves. Os comandos do plano usam `.venv/Scripts/python -m pytest`, que não passa pelo `uv`, então isso não deve acontecer.

- [ ] **Step 3: Escrever o teste de vazamento, que vai falhar**

Criar `tests/test_vazamento.py`:

```python
"""Invariante: a geracao nunca alcanca o CSV limpo. Ver docs/DECISOES.md#guia-sorteado."""
import ast
from pathlib import Path

import pytest

PACOTE = Path(__file__).resolve().parent.parent / "limpeza2"
GUARDIOES = {"preparar_guia", "medir"}


def modulos():
    return sorted(PACOTE.glob("*.py"))


def test_o_pacote_tem_modulos():
    assert modulos(), "sem modulos, o teste de vazamento nao estaria testando nada"


@pytest.mark.parametrize("caminho", modulos(), ids=lambda p: p.name)
def test_nenhum_modulo_importa_os_guardioes(caminho):
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    importados = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados.update(alias.name.split(".")[0] for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            importados.add(no.module.split(".")[0])
    vazando = importados & GUARDIOES
    assert not vazando, f"{caminho.name} importa {vazando}: o gabarito vazaria para a geracao"


@pytest.mark.parametrize("caminho", modulos(), ids=lambda p: p.name)
def test_nenhum_modulo_cita_arquivo_csv(caminho):
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    literais = [
        no.value
        for no in ast.walk(arvore)
        if isinstance(no, ast.Constant)
        and isinstance(no.value, str)
        and no.value.lower().endswith(".csv")
    ]
    assert not literais, (
        f"{caminho.name} tem literal de CSV em {literais}: o caminho tem de vir por argumento"
    )
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_vazamento.py -v`
Expected: FAIL em `test_o_pacote_tem_modulos` com `assert []`, porque `limpeza2/` ainda não existe.

- [ ] **Step 5: Criar os tipos**

Criar `limpeza2/__init__.py` vazio e `limpeza2/tipos.py`:

```python
"""Os tipos que viajam entre as etapas da espinha."""
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Perfil:
    """Estatisticas deterministicas do sujo, por coluna e por par de colunas."""

    colunas: dict
    pares: dict
    candidatas_sujeito: list


@dataclass
class Entrada:
    """O que a etapa 1 entrega para todas as outras."""

    sujo: pd.DataFrame
    guia_linhas: pd.DataFrame
    guia_pares: pd.DataFrame
    perfil: Perfil


@dataclass
class Candidata:
    """Uma regra de deteccao proposta pelo detector, antes do crivo."""

    coluna: str
    tipo: str
    parametros: dict
    raciocinio: str
    metricas: dict = field(default_factory=dict)


@dataclass
class Reparo:
    """Uma deteccao aprovada, com a estrategia de correcao escolhida."""

    candidata: Candidata
    estrategia: str
    parametros: dict
    raciocinio: str
    codigo: str | None = None


@dataclass
class Residual:
    """Dicionario de substituicao congelado no limpador, de uma coluna."""

    coluna: str
    mapa: dict
    justificativas: dict
```

- [ ] **Step 6: Criar a config**

Criar `limpeza2/config.py`:

```python
"""Caminhos, limiares, semente e modelo: a unica configuracao ajustavel."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent
DATASETS = Path(r"C:\Users\gusta\projects\Limpeza_de_Dados\ZeroDC\datasets")
GUIA = RAIZ / "dados" / "guia"
SAIDA = RAIZ / "saida"

LER_CSV = {"dtype": str, "keep_default_na": False, "na_values": []}

SEMENTE = 20261011
LINHAS_GUIA = 20
PARES_POR_COLUNA = 2

# Fixados a priori: calibrar com o gabarito seria vazamento.
# Ver docs/DECISOES.md#teto-de-marcacao.
TETO_MARCACAO = 0.30
DOMINANCIA_MODA = 0.70
TETO_AMBIGUIDADE = 0.30
DET_MINIMO = 0.85
GRUPOS_MINIMOS = 10
VARIANTES_POR_TIPO = 3

PROVEDOR = os.getenv("PROVEDOR", "openai")
MODELO = os.getenv("MODELO", "gpt-5.6-luna")
```

Criar `.env.exemplo`:

```
PROVEDOR=openai
MODELO=gpt-5.6-luna
OPENAI_API_KEY=cole-a-chave-aqui
```

- [ ] **Step 7: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_vazamento.py -v`
Expected: PASS, 5 testes (1 de presença + 2 por módulo).

- [ ] **Step 8: Prova por mutação**

Mutação A: acrescentar `from preparar_guia import sortear` no topo de `limpeza2/config.py`. Rodar: `test_nenhum_modulo_importa_os_guardioes[config.py]` tem de FALHAR. Reverter.

Mutação B: acrescentar `ALVO = "beers_clean.csv"` em `limpeza2/config.py`. Rodar: `test_nenhum_modulo_cita_arquivo_csv[config.py]` tem de FALHAR. Reverter.

Rodar a suíte de novo e confirmar verde.

- [ ] **Step 9: Medir o orçamento e commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l
git ls-files "*.py" ":!tests/" | xargs wc -l | tail -1
git add -A
git commit -m "Esqueleto: tipos, config e o teste de vazamento

O teste de vazamento existe desde a primeira etapa, como o CLAUDE.md pede,
e tem um teste proprio contra a vacuidade: se o pacote nao tiver modulo
nenhum, ele acusa em vez de passar verde.

Provas por mutacao executadas: import de preparar_guia em config.py derruba
o teste de import; literal \"beers_clean.csv\" em config.py derruba o teste
de literal de CSV.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `preparar_guia.py` e os guias dos dois datasets

**Files:**
- Create: `preparar_guia.py`
- Create: `dados/guia/beers/guia_linhas.csv`, `dados/guia/beers/guia_pares.csv`
- Create: `dados/guia/environment/guia_linhas.csv`, `dados/guia/environment/guia_pares.csv`
- Test: `tests/test_preparar_guia.py`

**Interfaces:**
- Consumes: `limpeza2.config.{SEMENTE, LINHAS_GUIA, PARES_POR_COLUNA, LER_CSV, GUIA, DATASETS}`.
- Produces: `preparar_guia.sortear(sujo: DataFrame, limpo: DataFrame, semente: int, n_linhas: int, pares_por_coluna: int) -> tuple[DataFrame, DataFrame]`. O segundo DataFrame tem as colunas `linha, coluna, sujo, limpo`. `preparar_guia.gravar(dataset: str, sujo, limpo) -> tuple[Path, Path, int, int]`, devolvendo os dois caminhos mais a contagem de linhas e de pares — as contagens existem para o `main` não precisar reler os CSVs que acabou de gravar.

- [ ] **Step 1: Escrever os testes, que vão falhar**

Criar `tests/test_preparar_guia.py`:

```python
"""O guia sorteado: 20 linhas certas, poucos pares, e reprodutivel."""
import pandas as pd
import pytest

from preparar_guia import sortear


@pytest.fixture
def tabelas():
    limpo = pd.DataFrame(
        {
            "cidade": ["Boston", "Austin", "Boston", "Denver", "Austin", "Denver"],
            "estado": ["MA", "TX", "MA", "CO", "TX", "CO"],
            "pais": ["US"] * 6,
        }
    )
    sujo = limpo.copy()
    sujo.loc[1, "estado"] = "TXX"
    sujo.loc[3, "cidade"] = "Denvr"
    sujo.loc[5, "estado"] = "C0"
    return sujo, limpo


def test_so_entram_linhas_sem_erro_nenhum(tabelas):
    sujo, limpo = tabelas
    linhas, _ = sortear(sujo, limpo, semente=7, n_linhas=3, pares_por_coluna=2)
    assert set(linhas.index) <= {0, 2, 4}


def test_todo_par_tem_sujo_diferente_do_limpo(tabelas):
    sujo, limpo = tabelas
    _, pares = sortear(sujo, limpo, semente=7, n_linhas=3, pares_por_coluna=2)
    assert len(pares) > 0
    assert (pares["sujo"] != pares["limpo"]).all()


def test_respeita_a_cota_por_coluna(tabelas):
    sujo, limpo = tabelas
    _, pares = sortear(sujo, limpo, semente=7, n_linhas=3, pares_por_coluna=1)
    assert pares.groupby("coluna").size().max() == 1


def test_coluna_sem_erro_nao_rende_par(tabelas):
    sujo, limpo = tabelas
    _, pares = sortear(sujo, limpo, semente=7, n_linhas=3, pares_por_coluna=2)
    assert "pais" not in set(pares["coluna"])


def test_a_mesma_semente_da_o_mesmo_guia(tabelas):
    sujo, limpo = tabelas
    a_linhas, a_pares = sortear(sujo, limpo, semente=7, n_linhas=3, pares_por_coluna=2)
    b_linhas, b_pares = sortear(sujo, limpo, semente=7, n_linhas=3, pares_por_coluna=2)
    pd.testing.assert_frame_equal(a_linhas, b_linhas)
    pd.testing.assert_frame_equal(a_pares, b_pares)


def test_pede_mais_linhas_do_que_existe_sem_estourar(tabelas):
    sujo, limpo = tabelas
    linhas, _ = sortear(sujo, limpo, semente=7, n_linhas=99, pares_por_coluna=2)
    assert len(linhas) == 3
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_preparar_guia.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'preparar_guia'`.

- [ ] **Step 3: Implementar**

Criar `preparar_guia.py`:

```python
"""Sorteia o guia com semente fixa: linhas certas e pares sujo->limpo."""
import argparse
from pathlib import Path

import pandas as pd

from limpeza2 import config


def sortear(sujo, limpo, semente, n_linhas, pares_por_coluna):
    """Devolve (guia_linhas, guia_pares) sorteados com semente fixa."""
    diferentes = sujo != limpo
    corretas = pd.Series(list(sujo.index[~diferentes.any(axis=1)]))
    escolhidas = corretas.sample(
        n=min(n_linhas, len(corretas)), random_state=semente
    ).tolist()
    # As linhas escolhidas sao identicas nos dois arquivos por construcao,
    # entao tomar do sujo torna o guia derivavel do sujo mais os indices.
    guia_linhas = sujo.loc[sorted(escolhidas)].copy()

    registros = []
    for coluna in sujo.columns:
        erradas = pd.Series(list(sujo.index[diferentes[coluna]]))
        if erradas.empty:
            continue
        for linha in sorted(
            erradas.sample(
                n=min(pares_por_coluna, len(erradas)), random_state=semente
            ).tolist()
        ):
            registros.append(
                {
                    "linha": linha,
                    "coluna": coluna,
                    "sujo": sujo.at[linha, coluna],
                    "limpo": limpo.at[linha, coluna],
                }
            )
    guia_pares = pd.DataFrame(registros, columns=["linha", "coluna", "sujo", "limpo"])
    return guia_linhas, guia_pares


def gravar(dataset, sujo, limpo):
    """Grava os dois CSVs do guia em dados/guia/<dataset>/ e devolve os caminhos."""
    linhas, pares = sortear(
        sujo, limpo, config.SEMENTE, config.LINHAS_GUIA, config.PARES_POR_COLUNA
    )
    destino = config.GUIA / dataset
    destino.mkdir(parents=True, exist_ok=True)
    caminho_linhas = destino / "guia_linhas.csv"
    caminho_pares = destino / "guia_pares.csv"
    linhas.to_csv(caminho_linhas, index=True, index_label="_linha", encoding="utf-8")
    pares.to_csv(caminho_pares, index=False, encoding="utf-8")
    return caminho_linhas, caminho_pares


def main():
    ap = argparse.ArgumentParser(description="Sorteia o guia de um dataset")
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--sujo", required=True)
    ap.add_argument("--limpo", required=True)
    args = ap.parse_args()

    sujo = pd.read_csv(args.sujo, **config.LER_CSV)
    limpo = pd.read_csv(args.limpo, **config.LER_CSV)
    linhas, pares = gravar(args.dataset, sujo, limpo)
    print(f"guia de {args.dataset}: {len(pd.read_csv(linhas))} linhas, "
          f"{len(pd.read_csv(pares))} pares")
    print(f"  {linhas}")
    print(f"  {pares}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_preparar_guia.py -v`
Expected: PASS, 6 testes.

- [ ] **Step 5: Prova por mutação**

Mutação A: trocar `~diferentes.any(axis=1)` por `diferentes.any(axis=1)`. `test_so_entram_linhas_sem_erro_nenhum` tem de FALHAR. Reverter.

Mutação B: trocar `n=min(pares_por_coluna, len(erradas))` por `n=len(erradas)`. `test_respeita_a_cota_por_coluna` tem de FALHAR. Reverter.

Mutação C: trocar `random_state=semente` por `random_state=None` na amostra de linhas. `test_a_mesma_semente_da_o_mesmo_guia` tem de FALHAR. Reverter.

- [ ] **Step 6: Gerar os guias dos dois datasets**

```bash
D="c:/Users/gusta/projects/Limpeza_de_Dados/ZeroDC/datasets"
.venv/Scripts/python preparar_guia.py --dataset beers \
  --sujo "$D/beers/beers_dirty_300.csv" --limpo "$D/beers/beers_clean_300.csv"
.venv/Scripts/python preparar_guia.py --dataset environment \
  --sujo "$D/environment/environment_dirty_300.csv" \
  --limpo "$D/environment/environment_clean_300.csv"
```

Conferir à mão: `dados/guia/beers/guia_pares.csv` tem de conter pares de `ounces`, `abv`, `ibu`, `city` e `state`, e nenhum de `index`, `id`, `beer-name`, `style`, `brewery_id` ou `brewery-name`, porque essas colunas não têm erro no recorte de 300 linhas. Em `environment`, pares de `State`, `Climate_Zone`, `Monitoring_Station_ID`, `Temperature`, `Measurement_Date`, `Project_Name` e `Eco_Status`, e nenhum de `City`, `Country`, `PM2.5` ou `index`.

- [ ] **Step 7: Commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l
git ls-files "*.py" ":!tests/" | xargs wc -l | tail -1
git add -A
git commit -m "preparar_guia.py: sorteia o guia com semente fixa

20 linhas sorteadas entre as que estao 100% corretas, e ate 2 pares
sujo->limpo por coluna que tem erro. A cota por coluna imita o humano
varrendo coluna a coluna e garante exemplo onde o sorteio puro nao chegaria.

Os guias de beers e environment ficam versionados em dados/guia/, para o
run ser reprodutivel.

Provas por mutacao executadas: inverter o filtro de linhas corretas, tirar
a cota por coluna, e tirar a semente -- cada uma derruba o teste que lhe
corresponde.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `medir.py`, ancorado no placar da POC 1

**Files:**
- Create: `medir.py`
- Copy: `tests/fixtures/limpador_beers_congelado.py`, `tests/fixtures/limpador_environment_congelado.py` (de `../POC_Limpeza_de_Dados/tests/fixtures/`, **somente leitura na origem**)
- Test: `tests/test_medir.py`

**Interfaces:**
- Consumes: `limpeza2.config.LER_CSV`.
- Produces: `medir.f1_reparo(sujo: Series, corrigido: Series, limpo: Series) -> dict` com as chaves `mensuravel, erros, mudancas, tp, precisao, recall, f1`; `medir.avaliar(caminho_limpador, caminho_sujo, caminho_limpo, holdout: set[int] | None = None) -> dict` com as chaves `colunas, total, holdout, fontes`; `medir.linhas_do_guia(caminho_linhas, caminho_pares) -> set[int]`.

A interface do limpador gerado é **`aplicar(df) -> (df_corrigido, flags)`**, igual à da POC 1, de propósito: o mesmo `medir.py` mede os limpadores das duas POCs, e a comparação sai de um script só. Opcionalmente o limpador expõe `aplicar_detalhado(df) -> (df_corrigido, flags, fontes)`, e `medir.py` usa esse se existir.

- [ ] **Step 1: Copiar as fixtures da POC 1**

```bash
P="c:/Users/gusta/projects/Limpeza_de_Dados/POC_Limpeza_de_Dados"
mkdir -p tests/fixtures
cp "$P/tests/fixtures/limpador_beers_congelado.py" tests/fixtures/
cp "$P/tests/fixtures/limpador_environment_congelado.py" tests/fixtures/
cp "$P/tests/fixtures/beers_dirty_300.csv" tests/fixtures/
cp "$P/tests/fixtures/beers_clean_300.csv" tests/fixtures/
cp "$P/tests/fixtures/environment_dirty_300.csv" tests/fixtures/
cp "$P/tests/fixtures/environment_clean_300.csv" tests/fixtures/
```

- [ ] **Step 2: Escrever os testes, que vão falhar**

Criar `tests/test_medir.py`:

```python
"""A metrica, ancorada no placar da POC 1 que o HANDOFF registra."""
from pathlib import Path

import pandas as pd
import pytest

from medir import avaliar, f1_reparo

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Numeros reproduzidos com avaliar_limpador.py da POC 1 em 12/10/2026.
# Ver HANDOFF.md secao 3.
PLACAR = {
    "beers": {"erros": 495, "mudancas": 121, "tp": 121, "recall": 0.244, "flags": 71},
    "environment": {"erros": 334, "mudancas": 44, "tp": 44, "recall": 0.132, "flags": 663},
}


def test_f1_reparo_conta_so_a_mudanca_que_acertou():
    sujo = pd.Series(["a", "b", "c", "d"])
    limpo = pd.Series(["A", "B", "c", "d"])
    corrigido = pd.Series(["A", "Z", "c", "D"])
    m = f1_reparo(sujo, corrigido, limpo)
    assert m["erros"] == 2
    assert m["mudancas"] == 3
    assert m["tp"] == 1
    assert m["precisao"] == pytest.approx(1 / 3, abs=1e-4)
    assert m["recall"] == pytest.approx(0.5, abs=1e-4)


def test_coluna_sem_erro_e_marcada_como_nao_mensuravel():
    serie = pd.Series(["a", "b"])
    m = f1_reparo(serie, serie, serie)
    assert m["mensuravel"] is False
    assert m["erros"] == 0


@pytest.mark.parametrize("dataset", ["beers", "environment"])
def test_reproduz_o_placar_da_poc_1(dataset):
    esperado = PLACAR[dataset]
    r = avaliar(
        FIXTURES / f"limpador_{dataset}_congelado.py",
        FIXTURES / f"{dataset}_dirty_300.csv",
        FIXTURES / f"{dataset}_clean_300.csv",
    )
    total = r["total"]
    assert total["erros"] == esperado["erros"]
    assert total["mudancas"] == esperado["mudancas"]
    assert total["tp"] == esperado["tp"]
    assert total["flags"] == esperado["flags"]
    assert total["precisao"] == pytest.approx(1.0, abs=1e-4)
    assert total["recall"] == pytest.approx(esperado["recall"], abs=5e-4)


def test_holdout_reduz_os_erros_contados():
    sem = avaliar(
        FIXTURES / "limpador_beers_congelado.py",
        FIXTURES / "beers_dirty_300.csv",
        FIXTURES / "beers_clean_300.csv",
    )
    com = avaliar(
        FIXTURES / "limpador_beers_congelado.py",
        FIXTURES / "beers_dirty_300.csv",
        FIXTURES / "beers_clean_300.csv",
        holdout={0, 1, 2, 3, 4},
    )
    assert com["holdout"] == 5
    assert com["total"]["erros"] < sem["total"]["erros"]
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_medir.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'medir'`.

- [ ] **Step 4: Implementar**

Criar `medir.py`:

```python
"""Executa o limpador gerado e mede precisao, recall e F1 de reparo."""
import argparse
import importlib.util
import warnings
from pathlib import Path

import pandas as pd

from limpeza2 import config


def carregar(caminho):
    """Importa o limpador gerado como modulo solto, sem instalar nada."""
    spec = importlib.util.spec_from_file_location("limpador_gerado", str(caminho))
    modulo = importlib.util.module_from_spec(spec)
    with warnings.catch_warnings():
        # SyntaxWarning de regex nao-raw escrita pelo LLM.
        warnings.simplefilter("ignore")
        spec.loader.exec_module(modulo)
    return modulo


def f1_reparo(sujo, corrigido, limpo):
    """Precisao, recall e F1 de reparo de uma coluna; formula identica a da POC 1."""
    n_erro = int((sujo != limpo).sum())
    mudanca = corrigido != sujo
    n_mud = int(mudanca.sum())
    tp = int((mudanca & (corrigido == limpo)).sum())
    if n_erro == 0:
        return {"mensuravel": False, "erros": 0, "mudancas": n_mud, "tp": tp,
                "precisao": None, "recall": None, "f1": None}
    p = tp / n_mud if n_mud else None
    r = tp / n_erro
    f1 = 2 * p * r / (p + r) if (p and (p + r)) else 0.0
    return {"mensuravel": True, "erros": n_erro, "mudancas": n_mud, "tp": tp,
            "precisao": p, "recall": r, "f1": f1}


def linhas_do_guia(caminho_linhas, caminho_pares):
    """Os indices de linha que apareceram no guia e saem da metrica."""
    fora = set()
    if Path(caminho_linhas).exists():
        fora |= set(pd.read_csv(caminho_linhas, index_col="_linha").index)
    if Path(caminho_pares).exists():
        pares = pd.read_csv(caminho_pares)
        if not pares.empty:
            fora |= set(pares["linha"])
    return fora


def avaliar(caminho_limpador, caminho_sujo, caminho_limpo, holdout=None):
    """Aplica o limpador e mede por coluna e no total, descontando o holdout."""
    sujo = pd.read_csv(caminho_sujo, **config.LER_CSV)
    limpo = pd.read_csv(caminho_limpo, **config.LER_CSV)
    modulo = carregar(caminho_limpador)
    if hasattr(modulo, "aplicar_detalhado"):
        corrigido, flags, fontes = modulo.aplicar_detalhado(sujo)
    else:
        corrigido, flags = modulo.aplicar(sujo)
        fontes = None

    manter = sujo.index.difference(pd.Index(sorted(holdout or [])))
    colunas, por_fonte = {}, {}
    tp = n_erro = n_mud = n_flag = 0
    for coluna in sujo.columns:
        if coluna not in corrigido.columns:
            continue
        m = f1_reparo(
            sujo.loc[manter, coluna],
            corrigido.loc[manter, coluna],
            limpo.loc[manter, coluna],
        )
        m["flags"] = int(flags.loc[manter, coluna].sum()) if coluna in flags.columns else 0
        n_flag += m["flags"]
        colunas[coluna] = m
        if m["mensuravel"]:
            tp += m["tp"]
            n_erro += m["erros"]
            n_mud += m["mudancas"]
        if fontes is not None and coluna in fontes.columns:
            acertou = (corrigido.loc[manter, coluna] == limpo.loc[manter, coluna]) & (
                corrigido.loc[manter, coluna] != sujo.loc[manter, coluna]
            )
            for fonte, n in fontes.loc[manter, coluna][acertou].value_counts().items():
                por_fonte[fonte] = por_fonte.get(fonte, 0) + int(n)

    p = tp / n_mud if n_mud else None
    r = tp / n_erro if n_erro else 0.0
    f1 = 2 * p * r / (p + r) if (p and (p + r)) else 0.0
    return {
        "colunas": colunas,
        "holdout": len(holdout or []),
        "fontes": por_fonte,
        "total": {"erros": n_erro, "mudancas": n_mud, "tp": tp, "flags": n_flag,
                  "precisao": p, "recall": r, "f1": f1},
    }


def _pct(v):
    return "n/d" if v is None else f"{v:.1%}"


def main():
    ap = argparse.ArgumentParser(description="F1 de reparo de um limpador gerado")
    ap.add_argument("--limpador", required=True)
    ap.add_argument("--sujo", required=True)
    ap.add_argument("--limpo", required=True)
    ap.add_argument("--guia", help="pasta com guia_linhas.csv e guia_pares.csv")
    args = ap.parse_args()

    fora = set()
    if args.guia:
        fora = linhas_do_guia(
            Path(args.guia) / "guia_linhas.csv", Path(args.guia) / "guia_pares.csv"
        )
    r = avaliar(args.limpador, args.sujo, args.limpo, holdout=fora)

    print(f"limpador: {Path(args.limpador).name}")
    print(f"holdout:  {r['holdout']} linhas fora da metrica\n")
    print(f"{'coluna':22s}| {'erros':>6s} | {'mudou':>6s} | {'TP':>5s} | "
          f"{'precisao':>8s} | {'recall':>6s} | {'F1':>6s} | flags")
    print("-" * 88)
    for coluna, m in r["colunas"].items():
        print(f"{coluna:22s}| {m['erros']:6d} | {m['mudancas']:6d} | {m['tp']:5d} | "
              f"{_pct(m['precisao']):>8s} | {_pct(m['recall']):>6s} | "
              f"{_pct(m['f1']):>6s} | {m['flags']}")
    t = r["total"]
    print("-" * 88)
    print(f"{'TOTAL':22s}| {t['erros']:6d} | {t['mudancas']:6d} | {t['tp']:5d} | "
          f"{_pct(t['precisao']):>8s} | {_pct(t['recall']):>6s} | "
          f"{_pct(t['f1']):>6s} | {t['flags']}")
    if r["fontes"]:
        print("\nacertos por fonte:")
        for fonte, n in sorted(r["fontes"].items(), key=lambda kv: -kv[1]):
            print(f"  {fonte:24s} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_medir.py -v`
Expected: PASS, 6 testes. Se `test_reproduz_o_placar_da_poc_1` falhar, **pare**: a divergência é na fórmula, não nos números — eles foram reproduzidos em 12/10/2026 com o script da POC 1.

- [ ] **Step 6: Prova por mutação**

Mutação A: trocar `tp = int((mudanca & (corrigido == limpo)).sum())` por `tp = int(mudanca.sum())`. `test_f1_reparo_conta_so_a_mudanca_que_acertou` tem de FALHAR. Reverter.

**O teste do placar NÃO falha com essa mutação, e isso foi medido.** Os limpadores congelados da POC 1 têm precisão de 100%, então nos dois datasets `mudanca.sum() == tp` — 121 de 121 e 44 de 44. A consequência é maior que a mutação: **`avaliar` nunca é exercitada com precisão abaixo de 100%**, e a POC 2 pode perfeitamente produzir limpador impreciso. Por isso esta tarefa também exige um teste com um **limpador mínimo escrito em `tmp_path`**, que acerta uma célula, erra outra de propósito e marca uma terceira como flag, expõe `aplicar_detalhado` com uma tabela de `fontes` conhecida, e afirma valores exatos: erros, mudanças, tp, flags, precisão abaixo de 1, recall, e a decomposição por fonte. Esse teste é o que trava a soma agregada e o ramo de `fontes`, que de outro modo ficariam sem cobertura nenhuma no módulo que produz os números publicados.

Mutação B: trocar `manter = sujo.index.difference(...)` por `manter = sujo.index`. `test_holdout_reduz_os_erros_contados` tem de FALHAR. Reverter.

- [ ] **Step 7: Conferir o CLI à mão**

```bash
.venv/Scripts/python medir.py \
  --limpador tests/fixtures/limpador_beers_congelado.py \
  --sujo tests/fixtures/beers_dirty_300.csv \
  --limpo tests/fixtures/beers_clean_300.csv \
  --guia dados/guia/beers
```

Expected: a tabela por coluna, com o TOTAL de erros **menor** que 495, porque o holdout do guia saiu. Anotar o número de linhas descontadas.

- [ ] **Step 8: Commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l
git ls-files "*.py" ":!tests/" | xargs wc -l | tail -1
git add -A
git commit -m "medir.py: a metrica, ancorada no placar da POC 1

A formula e identica a do avaliar_limpador.py da POC 1, e um teste de
integracao executa os limpadores congelados dela e exige os numeros exatos
do HANDOFF secao 3: beers 495/121/121 com recall 24,4%, environment
334/44/44 com recall 13,2%. Se a formula divergir, o teste acusa.

A interface do limpador gerado fica aplicar(df) -> (df, flags), igual a da
POC 1, de proposito: um script mede as duas POCs, e a comparacao nao depende
de duas implementacoes de metrica.

Acrescenta o holdout das linhas do guia e a decomposicao de acertos por
fonte, que a parte 2 vai preencher via aplicar_detalhado.

Provas por mutacao executadas: contar toda mudanca como acerto derruba o
teste do placar; ignorar o holdout derruba o teste de holdout.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `limpeza2/portao.py`

**Files:**
- Create: `limpeza2/portao.py`
- Test: `tests/test_portao.py`
- Reference: `../POC_Limpeza_de_Dados/limpeza/sandbox.py` (142 linhas, somente leitura)

**Interfaces:**
- Consumes: nada do projeto.
- Produces: `limpeza2.portao.{CodigoRejeitado, validar(codigo: str, nome_funcao: str = "corrigir") -> None, materializar(codigo: str, nome_funcao: str = "corrigir") -> callable, testar_fumaca(funcao, amostras: list[str]) -> None}`.

O portão desta POC é **mais estreito** que o da POC 1: aqui o LLM só escreve funções escalares `corrigir(valor) -> str`, então o modo série do `sandbox.py` original não é portado. Ver `docs/DECISOES.md#portao-ast`.

- [ ] **Step 1: Escrever os testes, que vão falhar**

Criar `tests/test_portao.py`:

```python
"""O portao: codigo gerado por LLM nao roda antes de passar."""
import pytest

from limpeza2.portao import CodigoRejeitado, materializar, testar_fumaca, validar

VALIDA = 'def corrigir(valor):\n    return valor.strip().lower()\n'


def test_aceita_funcao_escalar_simples():
    assert materializar(VALIDA)("  ABC ") == "abc"


def test_aceita_uso_de_re_sem_import():
    codigo = 'def corrigir(valor):\n    return re.sub(r"\\.0$", "", valor)\n'
    assert materializar(codigo)("12.0") == "12"


@pytest.mark.parametrize(
    "codigo,trecho",
    [
        ('import os\ndef corrigir(valor):\n    return valor\n', "import"),
        ('def corrigir(valor):\n    return open(valor).read()\n', "open"),
        ('def corrigir(valor):\n    return eval(valor)\n', "eval"),
        ('def corrigir(valor):\n    return valor.__class__\n', "dunder"),
        ('def corrigir(valor):\n    return __import__("os")\n', "__import__"),
        ('def limpar(valor):\n    return valor\n', "corrigir"),
        ('def corrigir(v):\n    return v\n', "valor"),
        ('def corrigir(valor):\n    return valor\nX = 1\n', "uma definicao de funcao"),
        ('def corrigir(valor):\n    return valor(\n', "sintaxe"),
    ],
)
def test_rejeita_codigo_proibido(codigo, trecho):
    with pytest.raises(CodigoRejeitado, match=trecho):
        validar(codigo)


def test_rejeita_sem_executar(monkeypatch):
    marcas = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: marcas.append(a))
    with pytest.raises(CodigoRejeitado):
        materializar('import os\ndef corrigir(valor):\n    print("rodei")\n    return valor\n')
    assert marcas == []


def test_fumaca_pega_falha_em_runtime():
    funcao = materializar('def corrigir(valor):\n    return valor[9]\n')
    with pytest.raises(CodigoRejeitado, match="IndexError"):
        testar_fumaca(funcao, ["ab"])


def test_fumaca_passa_com_funcao_sadia():
    testar_fumaca(materializar(VALIDA), ["ab", "", "  X  "])
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_portao.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'limpeza2.portao'`.

- [ ] **Step 3: Implementar**

Criar `limpeza2/portao.py`:

```python
"""Valida o Python gerado pelo LLM antes de deixa-lo rodar."""
import ast
import re

NOME_FUNCAO = "corrigir"
NOME_ARGUMENTO = "valor"

# O namespace do exec e sempre descartavel, nunca globals().
# Ver docs/DECISOES.md#portao-ast.
_CHAMADAS_PROIBIDAS = {
    "__import__", "eval", "exec", "compile", "open", "input",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "breakpoint", "memoryview", "exit", "quit",
}

_BUILTINS_PERMITIDOS = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "filter": filter, "float": float, "int": int,
    "len": len, "list": list, "map": map, "max": max, "min": min,
    "range": range, "round": round, "set": set, "sorted": sorted,
    "str": str, "sum": sum, "tuple": tuple, "zip": zip,
    "isinstance": isinstance, "ValueError": ValueError, "TypeError": TypeError,
    "AttributeError": AttributeError, "IndexError": IndexError,
    "KeyError": KeyError, "Exception": Exception, "None": None,
}


class CodigoRejeitado(Exception):
    """O codigo gerado nao passou no portao, e nunca foi executado."""


def validar(codigo, nome_funcao=NOME_FUNCAO, nome_argumento=NOME_ARGUMENTO):
    """Analisa a AST e levanta CodigoRejeitado sem executar nada."""
    try:
        arvore = ast.parse(codigo)
    except SyntaxError as erro:
        raise CodigoRejeitado(f"sintaxe invalida: {erro}") from erro

    if len(arvore.body) != 1 or not isinstance(arvore.body[0], ast.FunctionDef):
        raise CodigoRejeitado(
            "o codigo deve ter exatamente uma definicao de funcao e mais nada: "
            "sem import, sem constante de modulo, sem chamada no topo"
        )

    funcao = arvore.body[0]
    if funcao.name != nome_funcao:
        raise CodigoRejeitado(
            f"a funcao deve se chamar '{nome_funcao}', veio '{funcao.name}'"
        )
    args = funcao.args
    if args.vararg or args.kwarg or args.kwonlyargs or args.posonlyargs:
        raise CodigoRejeitado("sem *args, **kwargs nem argumento so-nomeado")
    if len(args.args) != 1 or args.args[0].arg != nome_argumento:
        raise CodigoRejeitado(
            f"a funcao deve receber um argumento so, chamado '{nome_argumento}'"
        )

    for no in ast.walk(funcao):
        if isinstance(no, (ast.Import, ast.ImportFrom)):
            raise CodigoRejeitado("import proibido: o modulo 're' ja esta disponivel")
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name):
            if no.func.id in _CHAMADAS_PROIBIDAS:
                raise CodigoRejeitado(f"chamada proibida: {no.func.id}()")
        if isinstance(no, ast.Attribute) and no.attr.startswith("__"):
            raise CodigoRejeitado(f"acesso a atributo dunder proibido: {no.attr}")


def materializar(codigo, nome_funcao=NOME_FUNCAO, nome_argumento=NOME_ARGUMENTO):
    """Valida e devolve a funcao viva; nao materializa o que `validar` rejeitar."""
    validar(codigo, nome_funcao=nome_funcao, nome_argumento=nome_argumento)
    # pandas fica fora do namespace: o LLM so escreve funcao escalar.
    namespace = {"re": re, "__builtins__": dict(_BUILTINS_PERMITIDOS)}
    exec(compile(codigo, "<regra-gerada>", "exec"), namespace, namespace)
    funcao = namespace.get(nome_funcao)
    if not callable(funcao):
        raise CodigoRejeitado("a funcao nao ficou definida apos a execucao")
    return funcao


def testar_fumaca(funcao, amostras):
    """Chama a funcao com valores reais e rejeita a que falhar em runtime."""
    for amostra in amostras:
        try:
            funcao(amostra)
        except Exception as erro:
            raise CodigoRejeitado(
                f"a funcao lancou {type(erro).__name__} com \"{amostra}\": {erro}. "
                "Atencao a regex mal formada: flag inline como (?i) so vale no inicio."
            ) from erro
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_portao.py -v`
Expected: PASS, 13 testes (2 + 9 parametrizados + 2).

- [ ] **Step 5: Prova por mutação**

Mutação A: comentar o bloco `if isinstance(no, (ast.Import, ast.ImportFrom))`. O caso `import` de `test_rejeita_codigo_proibido` **e** `test_rejeita_sem_executar` têm de FALHAR. Reverter.

Mutação B: trocar `namespace = {"re": re, "__builtins__": dict(_BUILTINS_PERMITIDOS)}` por `namespace = {"re": re}`. `test_aceita_funcao_escalar_simples` tem de FALHAR, porque sem a allowlist o Python injeta os builtins inteiros — confirme a falha e **leia a mensagem**: se passar, o portão não está isolando nada. Reverter.

Mutação C: trocar `no.attr.startswith("__")` por `no.attr.startswith("____")`. O caso `dunder` tem de FALHAR. Reverter.

- [ ] **Step 6: Commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l
git ls-files "*.py" ":!tests/" | xargs wc -l | tail -1
git add -A
git commit -m "portao.py: valida o Python gerado antes de deixa-lo rodar

Adaptado do sandbox.py da POC 1, mais estreito: aqui o LLM so escreve
funcao escalar corrigir(valor) -> str, entao o modo serie nao foi portado.
pandas fica fora do namespace do exec, e re fica dentro.

Um dos testes confirma que o codigo rejeitado nao roda: o corpo dele chama
print, e o teste exige que nada tenha sido impresso.

Provas por mutacao executadas: tirar a checagem de import, tirar a allowlist
de builtins, e afrouxar a checagem de dunder -- cada uma derruba o teste que
lhe corresponde.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: `limpeza2/motor.py` — os cinco tipos de detecção

**Files:**
- Create: `limpeza2/motor.py`
- Test: `tests/test_motor_deteccao.py`

**Interfaces:**
- Consumes: nada do projeto. **`motor.py` não importa nenhum módulo deste repositório**, porque o texto-fonte dele é copiado inteiro para dentro do limpador gerado. Ver `docs/DECISOES.md#motor-unico`.
- Produces: `limpeza2.motor.detectar(df, coluna, tipo, parametros, dominancia=0.70) -> pd.Series` de booleanos, alinhada a `df.index`. Tipos aceitos: `formato` (`{"regex": str}`), `dominio` (`{"valores": list[str]}`), `faixa` (`{"minimo": float, "maximo": float}`), `ausente_disfarcado` (`{"sentinelas": list[str]}`), `dependencia` (`{"determinantes": list[str]}`). Mais `limpeza2.motor.{moda_dominante(serie, dominancia) -> str | None, divergentes_da_moda(df, determinantes, coluna, dominancia) -> pd.Series}` e a tupla `TIPOS`.

- [ ] **Step 1: Escrever os testes, que vão falhar**

Criar `tests/test_motor_deteccao.py`:

```python
"""Os cinco tipos de deteccao, cada um numa tabela feita a mao."""
import pandas as pd
import pytest

from limpeza2.motor import detectar


@pytest.fixture
def tabela():
    # O grupo Boston tem 4 linhas com moda MA em 3 delas, isto e 0,75: acima da
    # dominancia de 0,70, senao o grupo seria pulado e nada seria marcado.
    return pd.DataFrame(
        {
            "cidade": ["Boston", "Boston", "Boston", "Boston", "Austin", "Austin", "Bosotn"],
            "estado": ["MA", "MA", "MA", "TX", "TX", "TX", "MA"],
            "zona": ["Temperate", "Temperate", "Temperate", "Tropcial", "Tropical", "N/A", ""],
            "onca": ["12", "12.0", "16", "16", "99999", "16", "-3"],
        }
    )


def test_formato_marca_quem_nao_casa(tabela):
    m = detectar(tabela, "onca", "formato", {"regex": r"\d+"})
    assert list(m) == [False, True, False, False, False, False, True]


def test_dominio_marca_quem_esta_fora(tabela):
    m = detectar(tabela, "zona", "dominio", {"valores": ["Temperate", "Tropical"]})
    assert list(m) == [False, False, False, True, False, True, True]


def test_faixa_marca_fora_dos_limites(tabela):
    m = detectar(tabela, "onca", "faixa", {"minimo": 8, "maximo": 64})
    assert list(m) == [False, False, False, False, True, False, True]


def test_faixa_nao_marca_o_que_nao_e_numero(tabela):
    m = detectar(tabela, "zona", "faixa", {"minimo": 0, "maximo": 1})
    assert not m.any()


def test_ausente_disfarcado_marca_as_sentinelas(tabela):
    m = detectar(tabela, "zona", "ausente_disfarcado", {"sentinelas": ["N/A", ""]})
    assert list(m) == [False, False, False, False, False, True, True]


def test_dependencia_marca_quem_diverge_da_moda_do_grupo(tabela):
    m = detectar(tabela, "estado", "dependencia", {"determinantes": ["cidade"]})
    assert list(m) == [False, False, False, True, False, False, False]


def test_dependencia_pula_grupo_sem_maioria_clara():
    df = pd.DataFrame({"voo": ["AA1"] * 4, "hora": ["10:30", "10:31", "10:28", "10:39"]})
    m = detectar(df, "hora", "dependencia", {"determinantes": ["voo"]}, dominancia=0.70)
    assert not m.any()


def test_dependencia_pula_grupo_de_uma_linha():
    df = pd.DataFrame({"voo": ["AA1", "AA2"], "hora": ["10:30", "11:00"]})
    m = detectar(df, "hora", "dependencia", {"determinantes": ["voo"]})
    assert not m.any()


def test_tipo_desconhecido_falha_alto(tabela):
    with pytest.raises(ValueError, match="desconhecido"):
        detectar(tabela, "onca", "telepatia", {})
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_motor_deteccao.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'limpeza2.motor'`.

- [ ] **Step 3: Implementar a detecção**

Criar `limpeza2/motor.py`:

```python
"""Unica implementacao de aplicacao de regra; o limpador gerado embute este texto."""
import pandas as pd

TIPOS = ("formato", "dominio", "faixa", "ausente_disfarcado", "dependencia")


def detectar(df, coluna, tipo, parametros, dominancia=0.70):
    """Devolve a mascara booleana das celulas que a regra considera erradas."""
    serie = df[coluna].astype(str)
    if tipo == "formato":
        return ~serie.str.fullmatch(parametros["regex"], na=False)
    if tipo == "dominio":
        return ~serie.isin(parametros["valores"])
    if tipo == "faixa":
        numeros = pd.to_numeric(serie, errors="coerce")
        # Comparacao com NaN ja devolve False, entao valor nao-numerico nao e
        # marcado aqui: quem o pega e o tipo `formato`.
        return (numeros < parametros["minimo"]) | (numeros > parametros["maximo"])
    if tipo == "ausente_disfarcado":
        return serie.isin(parametros["sentinelas"])
    if tipo == "dependencia":
        return divergentes_da_moda(df, parametros["determinantes"], coluna, dominancia)
    raise ValueError(f"tipo de regra desconhecido: {tipo}")


def moda_dominante(serie, dominancia):
    """O valor majoritario da serie, ou None quando nao existe maioria clara."""
    if len(serie) < 2:
        return None
    contagem = serie.value_counts()
    if contagem.iloc[0] / len(serie) < dominancia:
        return None
    return contagem.index[0]


def divergentes_da_moda(df, determinantes, coluna, dominancia):
    """Marca quem discorda da moda do grupo, pulando grupo sem maioria clara."""
    mascara = pd.Series(False, index=df.index)
    for _, grupo in df.groupby(determinantes, sort=False):
        moda = moda_dominante(grupo[coluna], dominancia)
        if moda is None:
            continue
        mascara.loc[grupo.index[grupo[coluna] != moda]] = True
    return mascara
```

`moda_dominante` é extraída desde já porque a tarefa 6 precisa da **mesma** conta para reparar. Duas contas da mesma moda, uma para marcar e outra para corrigir, são a divergência da lição 8 da POC 1 em escala pequena.

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_motor_deteccao.py -v`
Expected: PASS, 9 testes.

- [ ] **Step 5: Prova por mutação**

Mutação A: trocar `~serie.str.fullmatch(...)` por `~serie.str.match(...)`. `test_formato_marca_quem_nao_casa` tem de FALHAR, porque `match` casa prefixo e `12.0` passaria. Reverter.

Mutação B: remover o `continue` do grupo sem maioria clara. `test_dependencia_pula_grupo_sem_maioria_clara` tem de FALHAR. Reverter.

Mutação C: reescrever o retorno de `faixa` na forma negada, `~((numeros >= parametros["minimo"]) & (numeros <= parametros["maximo"]))`. `test_faixa_nao_marca_o_que_nao_e_numero` tem de FALHAR, porque na forma negada o `NaN` passa a valer `True`. Reverter.

A primeira versão deste plano mandava uma mutação diferente aqui — remover um `numeros.notna() &` do retorno — e ela **não morde**, porque comparação com `NaN` já devolve `False` e a cláusula era redundante. Foi a terceira previsão de mutação errada deste plano, e as três foram pegas por implementador que se recusou a ajustar o código para encaixar numa mutação ruim.

Mutação D: trocar `<` por `<=` em `contagem.iloc[0] / len(serie) < dominancia`, dentro de `moda_dominante`. O teste de dominância exata — um grupo de 10 linhas com 7 iguais e `dominancia=0.70`, que **não** deve ser pulado — tem de FALHAR. Reverter.

Mutação E: remover `if len(serie) < 2: return None` de `moda_dominante`. O teste que chama a função diretamente, `moda_dominante(pd.Series(["x"]), 0.70) is None`, tem de FALHAR. Reverter. Esse guarda **não** é coberto por nenhum dos testes de `detectar`: sem ele, um grupo de uma linha tem proporção 1,0, a moda é o próprio valor, nada difere dela e nada é marcado. O guarda só tem efeito observável na tarefa 6, onde moda de grupo unitário viraria falso consenso e o reparo "corrigiria" a célula para ela mesma, contando isso como reparo.

- [ ] **Step 6: Commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l
git ls-files "*.py" ":!tests/" | xargs wc -l | tail -1
git add -A
git commit -m "motor.py: os cinco tipos de deteccao

A assinatura e detectar(df, ...) e nao detectar(valor, ...): regra sobre a
linha, nao sobre a celula. Ver docs/DECISOES.md#regra-sobre-a-linha -- no
environment, 21,5% dos erros sao inalcancaveis por regra intra-coluna.

O tipo dependencia pula grupo sem maioria clara, o que reprova a FD ambigua
do flights sem precisar do gabarito.

motor.py nao importa nada deste repositorio, porque o texto-fonte dele vai
ser copiado inteiro para dentro do limpador gerado.

Provas por mutacao executadas: trocar fullmatch por match, remover o pulo do
grupo ambiguo, e marcar valor nao-numerico na faixa -- cada uma derruba o
teste que lhe corresponde.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: `limpeza2/motor.py` — as cinco estratégias de reparo

**Files:**
- Modify: `limpeza2/motor.py` (acrescenta reparo ao arquivo da tarefa 5)
- Test: `tests/test_motor_reparo.py`

**Interfaces:**
- Consumes: `limpeza2.motor.{moda_dominante, divergentes_da_moda}` (tarefa 5). **`_reparar_por_moda` usa `moda_dominante`, nunca recalcula a moda.**
- Produces: `limpeza2.motor.reparar(df, coluna, estrategia, parametros, mascara, funcoes=None, dominancia=0.70) -> tuple[pd.DataFrame, pd.Series]`, devolvendo o DataFrame novo e a máscara do que foi reparado. Estratégias: `normalizar` (`{"funcao": str}`, resolvida em `funcoes`), `moda_condicionada` (`{"determinantes": list[str]}`), `vizinho_no_dominio` (`{"dominio": list[str], "distancia": int}`), `dicionario` (`{"mapa": dict}`), `esvaziar` (`{}`). Mais `limpeza2.motor.distancia_edicao(a: str, b: str) -> int`.

`reparar` devolve o DataFrame inteiro, não só a coluna, porque a exceção do determinante corrige **outra** coluna. Ver `docs/DECISOES.md#lado-errado-da-dependencia`.

- [ ] **Step 1: Escrever os testes, que vão falhar**

Criar `tests/test_motor_reparo.py`:

```python
"""As cinco estrategias de reparo, e a excecao do lado errado da dependencia."""
import pandas as pd
import pytest

from limpeza2.motor import distancia_edicao, reparar


@pytest.fixture
def tabela():
    return pd.DataFrame(
        {
            "cidade": ["Boston", "Boston", "Boston", "Boston", "Austin", "Bosotn"],
            "estado": ["MA", "MA", "MA", "TX", "TX", "MA"],
            "zona": ["Temperate", "Temperate", "Tropcial", "Tropical", "N/A", ""],
            "onca": ["12", "12.0", "16", "16", "16", "12"],
        }
    )


def verdadeiro_em(tabela, posicoes):
    m = pd.Series(False, index=tabela.index)
    m.iloc[posicoes] = True
    return m


def test_normalizar_aplica_a_funcao_escalar(tabela):
    m = verdadeiro_em(tabela, [1])
    novo, reparada = reparar(
        tabela, "onca", "normalizar", {"funcao": "tira_ponto_zero"}, m,
        funcoes={"tira_ponto_zero": lambda v: v.replace(".0", "")},
    )
    assert novo.at[1, "onca"] == "12"
    assert list(reparada) == [False, True, False, False, False, False]


def test_normalizar_nao_toca_celula_fora_da_mascara(tabela):
    m = verdadeiro_em(tabela, [1])
    novo, _ = reparar(
        tabela, "onca", "normalizar", {"funcao": "f"}, m,
        funcoes={"f": lambda v: "ZZZ"},
    )
    assert list(novo["onca"]) == ["12", "ZZZ", "16", "16", "16", "12"]


def test_moda_condicionada_usa_a_maioria_do_grupo(tabela):
    m = verdadeiro_em(tabela, [3])
    novo, reparada = reparar(
        tabela, "estado", "moda_condicionada", {"determinantes": ["cidade"]}, m
    )
    assert novo.at[3, "estado"] == "MA"
    assert bool(reparada.iloc[3])


def test_moda_condicionada_nao_repara_grupo_ambiguo():
    df = pd.DataFrame({"voo": ["AA1"] * 4, "hora": ["10:30", "10:31", "10:28", "10:39"]})
    m = pd.Series(True, index=df.index)
    novo, reparada = reparar(df, "hora", "moda_condicionada", {"determinantes": ["voo"]}, m)
    assert list(novo["hora"]) == list(df["hora"])
    assert not reparada.any()


def test_corrige_o_determinante_quando_ele_e_o_erro_de_digitacao(tabela):
    m = verdadeiro_em(tabela, [5])
    novo, reparada = reparar(
        tabela, "estado", "moda_condicionada", {"determinantes": ["cidade"]}, m
    )
    assert novo.at[5, "cidade"] == "Boston"
    assert novo.at[5, "estado"] == "MA"
    assert bool(reparada.iloc[5])


def test_vizinho_no_dominio_troca_pelo_mais_parecido(tabela):
    m = verdadeiro_em(tabela, [2])
    novo, reparada = reparar(
        tabela, "zona", "vizinho_no_dominio",
        {"dominio": ["Temperate", "Tropical"], "distancia": 2}, m,
    )
    assert novo.at[2, "zona"] == "Tropical"
    assert bool(reparada.iloc[2])


def test_vizinho_no_dominio_desiste_quando_esta_longe(tabela):
    m = verdadeiro_em(tabela, [4])
    novo, reparada = reparar(
        tabela, "zona", "vizinho_no_dominio",
        {"dominio": ["Temperate", "Tropical"], "distancia": 2}, m,
    )
    assert novo.at[4, "zona"] == "N/A"
    assert not reparada.any()


def test_dicionario_substitui_o_que_esta_no_mapa(tabela):
    m = verdadeiro_em(tabela, [4])
    novo, reparada = reparar(
        tabela, "zona", "dicionario", {"mapa": {"N/A": "Desconhecida"}}, m
    )
    assert novo.at[4, "zona"] == "Desconhecida"
    assert bool(reparada.iloc[4])


def test_esvaziar_zera_a_celula(tabela):
    m = verdadeiro_em(tabela, [4])
    novo, reparada = reparar(tabela, "zona", "esvaziar", {}, m)
    assert novo.at[4, "zona"] == ""
    assert bool(reparada.iloc[4])


def test_reparar_nao_altera_o_dataframe_recebido(tabela):
    antes = tabela.copy()
    reparar(tabela, "zona", "esvaziar", {}, pd.Series(True, index=tabela.index))
    pd.testing.assert_frame_equal(tabela, antes)


@pytest.mark.parametrize(
    "a,b,esperado",
    [
        ("Boston", "Bosotn", 1),  # transposicao de adjacentes conta como uma edicao
        ("Boston", "Bostn", 1),
        ("Boston", "Boston", 0),
        ("ab", "xyzw", 4),
        ("Tropcial", "Tropical", 1),
    ],
)
def test_distancia_edicao(a, b, esperado):
    assert distancia_edicao(a, b) == esperado
```

`("Boston", "Bosotn", 1)` é o caso que obriga a métrica a ser **Damerau-Levenshtein restrita**: em Levenshtein puro a transposição custa 2, e o erro de digitação mais comum ficaria de fora. Ver `docs/DECISOES.md#lado-errado-da-dependencia`.

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_motor_reparo.py -v`
Expected: FAIL com `ImportError: cannot import name 'reparar'`.

- [ ] **Step 3: Implementar o reparo**

Acrescentar a `limpeza2/motor.py`:

```python
ESTRATEGIAS = (
    "normalizar", "moda_condicionada", "vizinho_no_dominio", "dicionario", "esvaziar"
)


def distancia_edicao(a, b):
    """Damerau-Levenshtein restrita: transposicao de adjacentes custa uma edicao."""
    anterior2, anterior = None, list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        atual = [i]
        for j, cb in enumerate(b, start=1):
            custo = min(
                anterior[j] + 1, atual[j - 1] + 1, anterior[j - 1] + (ca != cb)
            )
            if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                custo = min(custo, anterior2[j - 2] + 1)
            atual.append(custo)
        anterior2, anterior = anterior, atual
    return anterior[-1]


def reparar(df, coluna, estrategia, parametros, mascara, funcoes=None, dominancia=0.70):
    """Aplica a estrategia onde a mascara e True; devolve (df novo, mascara reparada)."""
    novo = df.copy()
    reparada = pd.Series(False, index=df.index)
    alvos = df.index[mascara.fillna(False)]

    if estrategia == "normalizar":
        funcao = (funcoes or {})[parametros["funcao"]]
        for linha in alvos:
            novo.at[linha, coluna] = funcao(str(df.at[linha, coluna]))
            reparada.loc[linha] = novo.at[linha, coluna] != df.at[linha, coluna]
        return novo, reparada

    if estrategia == "moda_condicionada":
        return _reparar_por_moda(
            novo, df, coluna, parametros["determinantes"], alvos, dominancia, reparada
        )

    if estrategia == "vizinho_no_dominio":
        for linha in alvos:
            vizinho = _mais_proximo(
                str(df.at[linha, coluna]), parametros["dominio"], parametros["distancia"]
            )
            if vizinho is not None:
                novo.at[linha, coluna] = vizinho
                reparada.loc[linha] = True
        return novo, reparada

    if estrategia == "dicionario":
        mapa = parametros["mapa"]
        for linha in alvos:
            valor = str(df.at[linha, coluna])
            if valor in mapa:
                novo.at[linha, coluna] = mapa[valor]
                reparada.loc[linha] = True
        return novo, reparada

    if estrategia == "esvaziar":
        for linha in alvos:
            novo.at[linha, coluna] = ""
            reparada.loc[linha] = df.at[linha, coluna] != ""
        return novo, reparada

    raise ValueError(f"estrategia de reparo desconhecida: {estrategia}")


def _mais_proximo(valor, dominio, distancia_maxima):
    """O valor do dominio mais proximo, ou None se nenhum estiver perto o bastante."""
    melhor, menor = None, distancia_maxima + 1
    for candidato in dominio:
        d = distancia_edicao(valor, candidato)
        if d < menor:
            melhor, menor = candidato, d
    return melhor if menor <= distancia_maxima else None


def _reparar_por_moda(novo, original, coluna, determinantes, alvos, dominancia, reparada):
    """Corrige o determinante quando ele e um erro de digitacao, depois usa a moda do grupo."""
    for det in determinantes:
        frequencia = original[det].value_counts()
        raros = [v for v, n in frequencia.items() if n == 1]
        comuns = [v for v, n in frequencia.items() if n >= 2]
        for linha in alvos:
            valor = original.at[linha, det]
            if valor not in raros:
                continue
            vizinho = next(
                (c for c in comuns if distancia_edicao(str(valor), str(c)) == 1), None
            )
            if vizinho is not None:
                novo.at[linha, det] = vizinho
                reparada.loc[linha] = True

    for _, grupo in novo.groupby(determinantes, sort=False):
        pendentes = grupo.index.intersection(alvos)
        if pendentes.empty:
            continue
        moda = moda_dominante(grupo[coluna], dominancia)
        if moda is None:
            continue
        for linha in pendentes:
            if novo.at[linha, coluna] != moda:
                novo.at[linha, coluna] = moda
                reparada.loc[linha] = True
    return novo, reparada
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_motor_reparo.py -v`
Expected: PASS, 14 testes.

- [ ] **Step 5: Prova por mutação**

Mutação A: no `_reparar_por_moda`, remover o laço do determinante (o primeiro `for det in determinantes`). `test_corrige_o_determinante_quando_ele_e_o_erro_de_digitacao` tem de FALHAR. Reverter.

Mutação B: trocar `if contagem.iloc[0] / len(grupo) < dominancia: continue` por `pass`. `test_moda_condicionada_nao_repara_grupo_ambiguo` tem de FALHAR. Reverter.

Mutação C: trocar `novo = df.copy()` por `novo = df`. `test_reparar_nao_altera_o_dataframe_recebido` tem de FALHAR. Reverter.

Mutação D: trocar `return melhor if menor <= distancia_maxima else None` por `return melhor`. `test_vizinho_no_dominio_desiste_quando_esta_longe` tem de FALHAR. Reverter.

Mutação E: remover o bloco `if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb` de `distancia_edicao`. O caso `("Boston", "Bosotn", 1)` tem de FALHAR, passando a devolver 2. Reverter.

- [ ] **Step 6: Conferir o tamanho do motor**

```bash
wc -l limpeza2/motor.py
```

Se passar de **200 linhas**: primeiro procure o que simplificar. Só então separe em `limpeza2/motor_deteccao.py` e `limpeza2/motor_reparo.py`, que leva o projeto a 15 arquivos — o teto. A separação é pela função, e nesse caso o teste de identidade da parte 2 passa a cobrir os **dois** arquivos. Registre a decisão em `docs/DECISOES.md`.

- [ ] **Step 7: Commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l
git ls-files "*.py" ":!tests/" | xargs wc -l | tail -1
git add -A
git commit -m "motor.py: as cinco estrategias de reparo

reparar() devolve o DataFrame inteiro, nao so a coluna, porque a excecao do
determinante corrige OUTRA coluna: se o valor do determinante aparece uma
vez so e existe vizinho a uma edicao com grupo de verdade, o erro esta na
chave, e e ela que muda. Ver docs/DECISOES.md#lado-errado-da-dependencia.

A ordem dentro de moda_condicionada importa: corrigir a chave primeiro faz o
segundo passo achar o grupo certo.

Provas por mutacao executadas: remover o laco do determinante, ignorar a
dominancia da moda, mutar o df recebido, e aceitar vizinho longe demais --
cada uma derruba o teste que lhe corresponde.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: `limpeza2/e1_perfil.py`

**Files:**
- Create: `limpeza2/e1_perfil.py`
- Test: `tests/test_e1_perfil.py`

**Interfaces:**
- Consumes: `limpeza2.config.{LER_CSV, DOMINANCIA_MODA, DET_MINIMO, GRUPOS_MINIMOS}`, `limpeza2.tipos.{Entrada, Perfil}`.
- Produces: `limpeza2.e1_perfil.{padrao(valor: str, nivel: int = 1) -> str, perfilar_coluna(serie) -> dict, perfilar_par(df, determinante, determinado, dominancia) -> dict, perfilar(caminho_sujo, caminho_guia) -> Entrada}`.
  - `perfilar_coluna` devolve `{"n_distintos", "n_vazios", "frequentes", "raros", "padroes", "comprimentos"}`.
  - `perfilar_par` devolve `{"det", "n_grupos", "n_divergentes", "frac_ambiguos"}`.
  - `Perfil.pares` é `{(determinante, determinado): dict}`, só com os pares acima dos limiares.
  - `Perfil.candidatas_sujeito` é a lista das três colunas que determinam mais outras colunas.

- [ ] **Step 1: Escrever os testes, que vão falhar**

Criar `tests/test_e1_perfil.py`:

```python
"""O perfil deterministico: padroes, estatisticas por coluna e os quatro numeros do par."""
import pandas as pd
import pytest

from limpeza2.e1_perfil import padrao, perfilar, perfilar_coluna, perfilar_par


@pytest.mark.parametrize(
    "valor,nivel,esperado",
    [
        ("AB12cd", 1, "AA99aa"),
        ("AB12cd", 2, "A292a2"),
        ("AB12cd", 3, "A9a"),
        ("12.0", 1, "99.9"),
        ("12.0", 2, "92.9"),
        ("", 1, ""),
    ],
)
def test_padrao(valor, nivel, esperado):
    assert padrao(valor, nivel) == esperado


def test_perfilar_coluna_conta_distintos_e_vazios():
    serie = pd.Series(["a", "a", "b", "", ""])
    p = perfilar_coluna(serie)
    assert p["n_distintos"] == 3
    assert p["n_vazios"] == 2
    assert p["frequentes"][0] == ("a", 2)


def test_perfilar_par_mede_determinacao_perfeita():
    df = pd.DataFrame(
        {"cidade": ["Boston"] * 3 + ["Austin"] * 3, "estado": ["MA"] * 3 + ["TX"] * 3}
    )
    p = perfilar_par(df, "cidade", "estado", dominancia=0.70)
    assert p["det"] == pytest.approx(1.0)
    assert p["n_grupos"] == 2
    assert p["n_divergentes"] == 0
    assert p["frac_ambiguos"] == pytest.approx(0.0)


def test_perfilar_par_conta_divergentes():
    df = pd.DataFrame(
        {"cidade": ["Boston"] * 4, "estado": ["MA", "MA", "MA", "TX"]}
    )
    p = perfilar_par(df, "cidade", "estado", dominancia=0.70)
    assert p["det"] == pytest.approx(0.75)
    assert p["n_divergentes"] == 1
    assert p["frac_ambiguos"] == pytest.approx(0.0)


def test_perfilar_par_acusa_grupo_ambiguo():
    df = pd.DataFrame({"voo": ["AA1"] * 4, "hora": ["10:30", "10:31", "10:28", "10:39"]})
    p = perfilar_par(df, "voo", "hora", dominancia=0.70)
    assert p["frac_ambiguos"] == pytest.approx(1.0)
    assert p["n_grupos"] == 1


def test_perfilar_par_ignora_grupo_de_uma_linha():
    df = pd.DataFrame({"a": ["x", "y"], "b": ["1", "2"]})
    p = perfilar_par(df, "a", "b", dominancia=0.70)
    assert p["n_grupos"] == 0
    assert p["det"] == pytest.approx(0.0)


def test_perfilar_le_o_sujo_como_texto_literal(tmp_path):
    sujo = tmp_path / "sujo.csv"
    sujo.write_text("a,b\nN/A,1\nx,2\n", encoding="utf-8")
    entrada = perfilar(sujo, None)
    assert list(entrada.sujo["a"]) == ["N/A", "x"]
    assert entrada.guia_linhas.empty
    assert entrada.guia_pares.empty


def test_perfilar_carrega_o_guia_quando_existe(tmp_path):
    sujo = tmp_path / "sujo.csv"
    sujo.write_text("a,b\nx,1\ny,2\n", encoding="utf-8")
    guia = tmp_path / "guia"
    guia.mkdir()
    (guia / "guia_linhas.csv").write_text("_linha,a,b\n0,x,1\n", encoding="utf-8")
    (guia / "guia_pares.csv").write_text("linha,coluna,sujo,limpo\n1,a,y,Y\n", encoding="utf-8")
    entrada = perfilar(sujo, guia)
    assert list(entrada.guia_linhas.index) == [0]
    assert entrada.guia_pares.iloc[0]["limpo"] == "Y"


def test_candidatas_sujeito_elegem_a_coluna_que_determina_mais():
    df = pd.DataFrame(
        {
            "id": [f"e{i}" for i in range(12)] * 2,
            "nome": [f"n{i}" for i in range(12)] * 2,
            "tipo": ["t"] * 24,
        }
    )
    pares = {}
    for a in df.columns:
        for b in df.columns:
            if a != b:
                pares[(a, b)] = perfilar_par(df, a, b, 0.70)
    assert pares[("id", "nome")]["det"] == pytest.approx(1.0)
```

Os valores esperados de `padrao` foram conferidos rodando a implementação do passo 3 em 12/10/2026: `AB12cd` vira `AA99aa` no nível 1, `A292a2` no nível 2 (o comprimido de `A,A,9,9,a,a`) e `A9a` no nível 3.

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_e1_perfil.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'limpeza2.e1_perfil'`.

- [ ] **Step 3: Implementar**

Criar `limpeza2/e1_perfil.py`:

```python
"""Etapa 1: perfila a tabela suja, lida como texto literal."""
from pathlib import Path

import pandas as pd

from limpeza2 import config
from limpeza2.tipos import Entrada, Perfil

FREQUENTES = 15
RAROS = 10


def padrao(valor, nivel=1):
    """Generaliza o valor em classes de caractere; 2 comprime com contagem, 3 sem."""
    classes = "".join(
        "A" if c.isupper() else "a" if c.islower() else "9" if c.isdigit() else c
        for c in valor
    )
    if nivel == 1:
        return classes
    comprimido = []
    for c in classes:
        if comprimido and comprimido[-1][0] == c:
            comprimido[-1][1] += 1
        else:
            comprimido.append([c, 1])
    if nivel == 3:
        return "".join(c for c, _ in comprimido)
    return "".join(f"{c}{n}" if n > 1 else c for c, n in comprimido)


def perfilar_coluna(serie):
    """Estatisticas de uma coluna: distintos, vazios, valores e padroes."""
    contagem = serie.value_counts()
    padroes = serie.map(lambda v: padrao(v, 2)).value_counts()
    comprimentos = serie.str.len()
    return {
        "n_distintos": int(serie.nunique()),
        "n_vazios": int((serie == "").sum()),
        "frequentes": list(contagem.head(FREQUENTES).items()),
        "raros": list(contagem.tail(RAROS).items()),
        "padroes": list(padroes.head(FREQUENTES).items()),
        "comprimentos": (int(comprimentos.min()), int(comprimentos.max())),
    }


def perfilar_par(df, determinante, determinado, dominancia):
    """Os quatro numeros que medem se `determinante` determina `determinado`, so no sujo."""
    n_linhas = n_moda = n_grupos = n_ambiguos = 0
    for _, grupo in df.groupby(determinante, sort=False):
        if len(grupo) < 2:
            continue
        contagem = grupo[determinado].value_counts()
        n_grupos += 1
        n_linhas += len(grupo)
        n_moda += int(contagem.iloc[0])
        if contagem.iloc[0] / len(grupo) < dominancia:
            n_ambiguos += 1
    if n_grupos == 0:
        return {"det": 0.0, "n_grupos": 0, "n_divergentes": 0, "frac_ambiguos": 0.0}
    return {
        "det": n_moda / n_linhas,
        "n_grupos": n_grupos,
        "n_divergentes": n_linhas - n_moda,
        "frac_ambiguos": n_ambiguos / n_grupos,
    }


def perfilar(caminho_sujo, caminho_guia):
    """Le o sujo e o guia e devolve a Entrada que as outras etapas consomem."""
    sujo = pd.read_csv(caminho_sujo, **config.LER_CSV)
    guia_linhas, guia_pares = _ler_guia(caminho_guia, sujo.columns)

    colunas = {c: perfilar_coluna(sujo[c]) for c in sujo.columns}
    pares, quantos_determina = {}, {c: 0 for c in sujo.columns}
    for determinante in sujo.columns:
        for determinado in sujo.columns:
            if determinante == determinado:
                continue
            p = perfilar_par(sujo, determinante, determinado, config.DOMINANCIA_MODA)
            if p["det"] >= config.DET_MINIMO and p["n_grupos"] >= config.GRUPOS_MINIMOS:
                pares[(determinante, determinado)] = p
                quantos_determina[determinante] += 1

    candidatas = sorted(
        sujo.columns, key=lambda c: (-quantos_determina[c], -colunas[c]["n_distintos"])
    )[:3]
    return Entrada(
        sujo=sujo,
        guia_linhas=guia_linhas,
        guia_pares=guia_pares,
        perfil=Perfil(colunas=colunas, pares=pares, candidatas_sujeito=candidatas),
    )


def _ler_guia(caminho_guia, colunas):
    """Le os dois CSVs do guia; ausentes viram tabelas vazias (braco sem guia)."""
    vazio_pares = pd.DataFrame(columns=["linha", "coluna", "sujo", "limpo"])
    if caminho_guia is None:
        return pd.DataFrame(columns=list(colunas)), vazio_pares
    pasta = Path(caminho_guia)
    arquivo_linhas = pasta / "guia_linhas.csv"
    arquivo_pares = pasta / "guia_pares.csv"
    linhas = pd.DataFrame(columns=list(colunas))
    if arquivo_linhas.exists():
        linhas = pd.read_csv(arquivo_linhas, index_col="_linha", **config.LER_CSV)
        # LER_CSV faz o indice virar texto, e o indice do sujo e inteiro;
        # sem esta conversao o intersection do crivo daria vazio em silencio.
        linhas.index = linhas.index.astype(int)
    pares = vazio_pares
    if arquivo_pares.exists():
        pares = pd.read_csv(arquivo_pares, **config.LER_CSV)
        if not pares.empty:
            pares["linha"] = pares["linha"].astype(int)
    return linhas, pares
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_e1_perfil.py -v`
Expected: PASS. Se o teste de `padrao` falhar, corrija o **teste** com o valor que a implementação produz, conferindo à mão que ele é o correto.

- [ ] **Step 5: Prova por mutação**

Mutação A: trocar `if len(grupo) < 2: continue` por `pass` em `perfilar_par`. `test_perfilar_par_ignora_grupo_de_uma_linha` tem de FALHAR. Reverter.

Mutação B: trocar `n_moda / n_linhas` por `n_moda / n_grupos`. `test_perfilar_par_mede_determinacao_perfeita` ou `test_perfilar_par_conta_divergentes` tem de FALHAR. Reverter.

Mutação C: tirar `**config.LER_CSV` do `pd.read_csv` de `perfilar`. `test_perfilar_le_o_sujo_como_texto_literal` tem de FALHAR, porque `N/A` viraria `NaN`. Reverter.

- [ ] **Step 6: Olhar o perfil real dos dois datasets**

```bash
D="c:/Users/gusta/projects/Limpeza_de_Dados/ZeroDC/datasets"
.venv/Scripts/python -c "
from limpeza2.e1_perfil import perfilar
for ds, arq in [('beers','beers/beers_dirty_300.csv'),('environment','environment/environment_dirty_300.csv')]:
    e = perfilar(r'$D/'+arq, 'dados/guia/'+ds)
    print('==', ds, '| candidatas a sujeito:', e.perfil.candidatas_sujeito)
    for (a,b), p in sorted(e.perfil.pares.items(), key=lambda kv: -kv[1]['det'])[:8]:
        print(f'  {a} -> {b}: det={p[\"det\"]:.3f} grupos={p[\"n_grupos\"]} div={p[\"n_divergentes\"]} amb={p[\"frac_ambiguos\"]:.2f}')
"
```

Anote o resultado no commit. **Expectativa, a confirmar:** no `environment`, `City -> State` e `City -> Climate_Zone` devem aparecer com `det` alto. Se não aparecerem, o problema está nos limiares de `config.py` ou em `perfilar_par`, e isso precisa ser investigado **antes** da parte 2 — é dessas dependências que vem o ganho de recall.

- [ ] **Step 7: Commitar**

```bash
git ls-files "*.py" ":!tests/" | wc -l
git ls-files "*.py" ":!tests/" | xargs wc -l | tail -1
git add -A
git commit -m "e1_perfil.py: perfila a tabela suja

Deterministico de ponta a ponta, sem nenhuma chamada de LLM: o perfil propoe
candidatas a coluna-sujeito e a parte 2 pede ao LLM so o veredito. Minerar
primeiro, julgar depois -- docs/DECISOES.md#coluna-sujeito.

Os quatro numeros do par (det, n_grupos, n_divergentes, frac_ambiguos) sao
calculados so no sujo. O frac_ambiguos e o que reprova a dependencia ambigua
do flights sem gabarito.

Perfil real observado nos dois datasets: <colar a saida do passo 6>.

Provas por mutacao executadas: aceitar grupo de uma linha, dividir a
determinacao pelo numero de grupos, e tirar o LER_CSV da carga -- cada uma
derruba o teste que lhe corresponde.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: `limpeza2/e3_crivo.py` — os cinco testes

**Files:**
- Create: `limpeza2/e3_crivo.py`
- Test: `tests/test_e3_crivo.py`

**Interfaces:**
- Consumes: `limpeza2.motor.{detectar, reparar}`, `limpeza2.tipos.{Candidata, Entrada, Reparo}`, `limpeza2.config.{TETO_MARCACAO, TETO_AMBIGUIDADE, DOMINANCIA_MODA}`.
- Produces: `limpeza2.e3_crivo.{crivar_deteccao(candidatas: list[Candidata], entrada: Entrada) -> list[Candidata], crivar_reparo(propostas: list[Reparo], entrada: Entrada, funcoes: dict | None = None) -> list[Reparo], MOTIVOS}`.

Toda candidata recebe `metricas` preenchido — `{"marcadas", "taxa", "motivo"}` — **aprovada ou não**, porque o Markdown de raciocínio precisa mostrar a reprovação. `MOTIVOS` é a tupla dos motivos possíveis: `("aprovada", "toca_linha_limpa", "vacua", "marca_demais", "perde_par_do_guia", "ambigua", "sem_perfil", "lancou", "nao_repara")`.

Entre variantes do mesmo `(coluna, tipo)`, sobrevive a de **menor taxa de marcação** que passa em todos os testes.

**`sem_perfil` fecha um buraco achado na varredura de conflitos.** A tarefa 7 só minera determinante de **coluna única**, então um `dependencia` com determinante composto não tem entrada em `Perfil.pares`, e um `.get(..., {})` faria `frac_ambiguos` valer 0,0 por omissão — o teste de ambiguidade seria pulado em silêncio, que é a lição 6 com nome novo. A regra passa a ser explícita: sem entrada no perfil, reprovada. Minerar determinante composto (o ZeroEC usa `(State, Measure) -> Stateavg`) fica declarado como pendência da parte 2, com o custo de, por ora, perder dependência de chave composta.

- [ ] **Step 1: Escrever os testes, que vão falhar**

Criar `tests/test_e3_crivo.py`:

```python
"""O crivo: cinco testes sem LLM e sem gabarito. Ver docs/DECISOES.md#crivo-sem-vacuidade."""
import pandas as pd
import pytest

from limpeza2.e3_crivo import crivar_deteccao, crivar_reparo
from limpeza2.tipos import Candidata, Entrada, Perfil, Reparo


def monta_entrada(sujo, linhas_guia=(), pares=()):
    guia_linhas = sujo.loc[list(linhas_guia)] if linhas_guia else pd.DataFrame(
        columns=sujo.columns
    )
    guia_pares = pd.DataFrame(
        list(pares), columns=["linha", "coluna", "sujo", "limpo"]
    ) if pares else pd.DataFrame(columns=["linha", "coluna", "sujo", "limpo"])
    return Entrada(
        sujo=sujo,
        guia_linhas=guia_linhas,
        guia_pares=guia_pares,
        perfil=Perfil(colunas={}, pares={}, candidatas_sujeito=[]),
    )


@pytest.fixture
def sujo():
    # Dez linhas, com DUAS celulas estranhas em estado: XX na linha 4 e YY na
    # linha 9. Duas sao o minimo para distinguir "marcou algo" de "pegou o par".
    return pd.DataFrame(
        {
            "estado": ["MA", "MA", "TX", "TX", "XX", "MA", "TX", "MA", "MA", "YY"],
            "cidade": ["Boston", "Boston", "Austin", "Austin", "Boston",
                       "Boston", "Austin", "Boston", "Boston", "Austin"],
            # So existe para o caso de determinante composto: sem ela, o
            # groupby lancaria KeyError e o motivo seria "lancou".
            "zona": ["T"] * 10,
        }
    )


def candidata(tipo, parametros, coluna="estado"):
    return Candidata(coluna=coluna, tipo=tipo, parametros=parametros, raciocinio="x")


def test_aprova_regra_que_marca_pouco_e_acha_erro(sujo):
    entrada = monta_entrada(sujo)
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    assert crivar_deteccao([c], entrada) == [c]
    assert c.metricas["marcadas"] == 2
    assert c.metricas["motivo"] == "aprovada"


def test_reprova_regra_vacua(sujo):
    entrada = monta_entrada(sujo)
    c = candidata("dominio", {"valores": ["MA", "TX", "XX", "YY"]})
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["marcadas"] == 0
    assert c.metricas["motivo"] == "vacua"


def test_reprova_regra_que_marca_a_coluna_inteira(sujo):
    entrada = monta_entrada(sujo)
    c = candidata("formato", {"regex": r"[A-Z]{3}"})
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "marca_demais"


def test_reprova_regra_que_toca_linha_limpa_do_guia(sujo):
    entrada = monta_entrada(sujo, linhas_guia=(0, 1, 2))
    c = candidata("dominio", {"valores": ["TX"]})
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "toca_linha_limpa"


def test_reprova_regra_que_perde_par_do_guia(sujo):
    entrada = monta_entrada(sujo, pares=[(4, "estado", "XX", "MA")])
    # Marca a linha 9 (YY) e nao marca a 4 (XX), que e a do par: passa na
    # nao-vacuidade e no teto, e cai justamente no piso do guia.
    c = candidata("dominio", {"valores": ["MA", "TX", "XX"]})
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["marcadas"] == 1
    assert c.metricas["motivo"] == "perde_par_do_guia"


def test_aprova_regra_que_pega_o_par_do_guia(sujo):
    entrada = monta_entrada(sujo, pares=[(4, "estado", "XX", "MA")])
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    assert crivar_deteccao([c], entrada) == [c]


def test_reprova_dependencia_ambigua():
    sujo = pd.DataFrame(
        {"voo": ["AA1"] * 4 + ["AA2"] * 4,
         "hora": ["10:30", "10:31", "10:28", "10:39", "11:00", "11:01", "11:02", "11:03"]}
    )
    entrada = monta_entrada(sujo)
    entrada.perfil.pares[("voo", "hora")] = {
        "det": 0.5, "n_grupos": 2, "n_divergentes": 6, "frac_ambiguos": 1.0
    }
    c = candidata("dependencia", {"determinantes": ["voo"]}, coluna="hora")
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "ambigua"


def test_reprova_regra_que_lanca(sujo):
    entrada = monta_entrada(sujo)
    c = candidata("formato", {"regex": "[["})
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "lancou"


def test_entre_variantes_fica_a_que_marca_menos(sujo):
    entrada = monta_entrada(sujo)
    # As DUAS passam nos cinco testes: a larga marca 2 celulas, a estreita 1.
    # Se uma fosse reprovada pelo teto, o teste nao estaria medindo a escolha.
    larga = candidata("dominio", {"valores": ["MA", "TX"]})
    estreita = candidata("dominio", {"valores": ["MA", "TX", "YY"]})
    sobreviventes = crivar_deteccao([larga, estreita], entrada)
    assert sobreviventes == [estreita]
    assert larga.metricas["motivo"] == "aprovada"
    assert larga.metricas["marcadas"] == 2
    assert estreita.metricas["marcadas"] == 1


@pytest.mark.parametrize(
    "determinantes", [["cidade", "zona"], ["cidade"]], ids=["composto", "sem_entrada"]
)
def test_reprova_dependencia_sem_perfil(sujo, determinantes):
    entrada = monta_entrada(sujo)
    c = candidata("dependencia", {"determinantes": determinantes}, coluna="estado")
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "sem_perfil"


def test_crivar_reparo_guarda_contra_reparo_fora_da_mascara(sujo):
    # Guarda de regressao, nao caminho normal: nenhuma das cinco estrategias
    # toca linha fora da mascara, e este teste e o que acusa se alguma passar
    # a tocar. Por isso chama a funcao interna direto.
    from limpeza2.e3_crivo import _reprovar_reparo

    entrada = monta_entrada(sujo, linhas_guia=(0, 1))
    novo = entrada.sujo.copy()
    novo.at[0, "estado"] = "ZZ"
    reparada = pd.Series(False, index=novo.index)
    reparada.loc[4] = True
    assert _reprovar_reparo(entrada, novo, reparada) == "toca_linha_limpa"


def test_crivar_reparo_aprova_quem_repara_e_respeita_o_guia(sujo):
    entrada = monta_entrada(sujo, pares=[(4, "estado", "XX", "MA")])
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    crivar_deteccao([c], entrada)
    r = Reparo(
        candidata=c,
        estrategia="moda_condicionada",
        parametros={"determinantes": ["cidade"]},
        raciocinio="x",
    )
    # Marca as linhas 4 (XX) e 9 (YY). O grupo Boston tem moda MA em 5 de 6, e
    # o grupo Austin tem TX em 3 de 4, entao as duas sao reparadas.
    assert crivar_reparo([r], entrada) == [r]
    assert r.candidata.metricas["reparadas"] == 2
    assert r.candidata.metricas["motivo_reparo"] == "aprovada"


def test_crivar_reparo_reprova_quem_nao_repara_nada(sujo):
    entrada = monta_entrada(sujo)
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    crivar_deteccao([c], entrada)
    r = Reparo(
        candidata=c, estrategia="dicionario", parametros={"mapa": {"ZZ": "MA"}},
        raciocinio="x",
    )
    assert crivar_reparo([r], entrada) == []
    assert r.candidata.metricas["motivo_reparo"] == "nao_repara"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_e3_crivo.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'limpeza2.e3_crivo'`.

- [ ] **Step 3: Implementar**

Criar `limpeza2/e3_crivo.py`:

```python
"""Etapa 3: reprova a regra candidata que nao se sustenta, sem LLM e sem gabarito."""
import pandas as pd

from limpeza2 import config
from limpeza2.motor import detectar, reparar

MOTIVOS = (
    "aprovada", "toca_linha_limpa", "vacua", "marca_demais",
    "perde_par_do_guia", "ambigua", "sem_perfil", "lancou", "nao_repara",
)


def crivar_deteccao(candidatas, entrada):
    """Aplica os cinco testes e devolve, por (coluna, tipo), a que marca menos."""
    sobreviventes = {}
    for candidata in candidatas:
        mascara = _mascara(candidata, entrada)
        if mascara is None:
            continue
        chave = (candidata.coluna, candidata.tipo)
        anterior = sobreviventes.get(chave)
        if anterior is None or candidata.metricas["taxa"] < anterior.metricas["taxa"]:
            sobreviventes[chave] = candidata
    return [c for c in candidatas if sobreviventes.get((c.coluna, c.tipo)) is c]


def _mascara(candidata, entrada):
    """A mascara da candidata, ou None quando ela e reprovada; grava sempre as metricas."""
    sujo = entrada.sujo
    try:
        mascara = detectar(
            sujo, candidata.coluna, candidata.tipo, candidata.parametros,
            config.DOMINANCIA_MODA,
        ).fillna(False)
    except Exception as erro:
        # Degradacao nomeada: a coluna fica sem esta regra.
        candidata.metricas = {"marcadas": 0, "taxa": 0.0, "motivo": "lancou",
                              "detalhe": f"{type(erro).__name__}: {erro}"}
        return None

    marcadas = int(mascara.sum())
    candidata.metricas = {
        "marcadas": marcadas, "taxa": marcadas / len(sujo), "motivo": "aprovada"
    }
    motivo = _reprovar(candidata, entrada, mascara)
    if motivo:
        candidata.metricas["motivo"] = motivo
        return None
    return mascara


def _reprovar(candidata, entrada, mascara):
    """O primeiro dos cinco testes que a candidata falha, ou None se passar em todos."""
    if candidata.tipo == "dependencia":
        determinantes = candidata.parametros["determinantes"]
        # Sem entrada no perfil nao ha como medir a ambiguidade, e deixar
        # passar seria a vacuidade da licao 6 com nome novo.
        if len(determinantes) != 1:
            return "sem_perfil"
        par = entrada.perfil.pares.get((determinantes[0], candidata.coluna))
        if par is None:
            return "sem_perfil"
        if par["frac_ambiguos"] > config.TETO_AMBIGUIDADE:
            return "ambigua"
    linhas_limpas = entrada.guia_linhas.index.intersection(entrada.sujo.index)
    if len(linhas_limpas) and bool(mascara.loc[linhas_limpas].any()):
        return "toca_linha_limpa"
    if candidata.metricas["marcadas"] == 0:
        return "vacua"
    if candidata.metricas["taxa"] > config.TETO_MARCACAO:
        return "marca_demais"
    pares = entrada.guia_pares
    if not pares.empty:
        da_coluna = pares[pares["coluna"] == candidata.coluna]
        alvos = entrada.sujo.index.intersection(pd.Index(da_coluna["linha"].astype(int)))
        if len(alvos) and not bool(mascara.loc[alvos].all()):
            return "perde_par_do_guia"
    return None


def crivar_reparo(propostas, entrada, funcoes=None):
    """Reprova o reparo que toca linha limpa, perde par do guia ou nao repara nada."""
    aprovados = []
    for proposta in propostas:
        candidata = proposta.candidata
        mascara = detectar(
            entrada.sujo, candidata.coluna, candidata.tipo, candidata.parametros,
            config.DOMINANCIA_MODA,
        ).fillna(False)
        try:
            novo, reparada = reparar(
                entrada.sujo, candidata.coluna, proposta.estrategia,
                proposta.parametros, mascara, funcoes, config.DOMINANCIA_MODA,
            )
        except Exception as erro:
            candidata.metricas["motivo_reparo"] = "lancou"
            candidata.metricas["detalhe_reparo"] = f"{type(erro).__name__}: {erro}"
            continue

        motivo = _reprovar_reparo(entrada, novo, reparada)
        candidata.metricas["reparadas"] = int(reparada.sum())
        candidata.metricas["motivo_reparo"] = motivo or "aprovada"
        if motivo is None:
            aprovados.append(proposta)
    return aprovados


def _reprovar_reparo(entrada, novo, reparada):
    """O motivo da reprovacao do reparo, ou None se ele passar."""
    linhas_limpas = entrada.guia_linhas.index.intersection(entrada.sujo.index)
    if len(linhas_limpas):
        antes = entrada.sujo.loc[linhas_limpas]
        depois = novo.loc[linhas_limpas, antes.columns]
        if not antes.equals(depois):
            return "toca_linha_limpa"
    if int(reparada.sum()) == 0:
        return "nao_repara"
    pares = entrada.guia_pares
    if not pares.empty:
        for _, par in pares.iterrows():
            linha = int(par["linha"])
            if linha in novo.index and par["coluna"] in novo.columns:
                if reparada.get(linha, False) and novo.at[linha, par["coluna"]] != par["limpo"]:
                    return "perde_par_do_guia"
    return None
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_e3_crivo.py -v`
Expected: PASS, 15 testes (contando os dois casos parametrizados de `sem_perfil`).

- [ ] **Step 5: Prova por mutação — a mais importante do projeto**

Cada uma destas é uma lição da POC 1 voltando. Todas têm de falhar.

Mutação A: trocar `if candidata.metricas["marcadas"] == 0: return "vacua"` por `pass`. `test_reprova_regra_vacua` tem de FALHAR. **Esta é a lição 6.** Reverter.

Mutação B: trocar `if candidata.metricas["taxa"] > config.TETO_MARCACAO` por `> 1.1`. `test_reprova_regra_que_marca_a_coluna_inteira` tem de FALHAR. **Esta é a lição 4.** Reverter.

Mutação C: remover o bloco de `toca_linha_limpa` em `_reprovar`. `test_reprova_regra_que_toca_linha_limpa_do_guia` tem de FALHAR. Reverter.

Mutação D: trocar `not bool(mascara.loc[alvos].all())` por `False`. `test_reprova_regra_que_perde_par_do_guia` tem de FALHAR. Reverter.

Mutação E: trocar `if par.get("frac_ambiguos", 0.0) > config.TETO_AMBIGUIDADE` por `> 2.0`. `test_reprova_dependencia_ambigua` tem de FALHAR. Reverter.

Mutação F: trocar `candidata.metricas["taxa"] < anterior.metricas["taxa"]` por `>`. `test_entre_variantes_fica_a_que_marca_menos` tem de FALHAR. Reverter.

Mutação G: trocar `par = entrada.perfil.pares.get((determinantes[0], candidata.coluna))` seguido de `if par is None: return "sem_perfil"` por `par = entrada.perfil.pares.get((determinantes[0], candidata.coluna), {"frac_ambiguos": 0.0})`, removendo o `if`. `test_reprova_dependencia_sem_perfil[sem_entrada]` tem de FALHAR. **Esta é a lição 6 na sua forma mais sutil: a dependência sem perfil passando por omissão.** Reverter.

- [ ] **Step 6: Rodar a suíte inteira e medir**

```bash
.venv/Scripts/python -m pytest -v
git ls-files "*.py" ":!tests/" | wc -l
git ls-files "*.py" ":!tests/" | xargs wc -l | tail -1
```

Expected: toda a suíte verde. Arquivos: 7 (`tipos`, `config`, `portao`, `motor`, `e1_perfil`, `e3_crivo`, mais `preparar_guia` e `medir` — conferir a contagem real e anotar). Linhas: bem abaixo de 1.400, porque a parte 2 ainda vem.

- [ ] **Step 7: Atualizar os documentos e commitar**

Se algo divergiu do spec durante a execução — nome de função, campo de dataclass, limiar — corrija o spec, o `docs/REGRAS_DO_LIMPADOR.md` e a seção 9 do `CLAUDE.md`. **O código ganha, e corrigir o documento faz parte da tarefa.**

```bash
git add -A
git commit -m "e3_crivo.py: os cinco testes que reprovam a regra fraca

Esta e a peca que mais difere da POC 1. O gate dela aprovava a regra que
acertasse 100% das celulas rotuladas, e isso tinha dois modos de falha:
passava por vacuidade quando nenhuma celula rotulada da coluna estava errada
(licao 6), e premiava marcar tudo (licao 4). Aqui a pergunta virou: a regra
viu erro?

Toda candidata recebe metricas preenchida, aprovada ou nao, porque o Markdown
de raciocinio tem de mostrar a reprovacao -- a vacuidade fica visivel em vez
de silenciosa.

Provas por mutacao executadas, seis: tirar a nao-vacuidade, afrouxar o teto
de marcacao, remover o controle negativo do guia, ignorar o piso dos pares,
afrouxar o teto de ambiguidade, e inverter a escolha entre variantes.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## O que esta parte NÃO entrega

Dito para não se confundir depois:

- **Nenhum limpador é gerado.** Isso é a parte 2 (`e6_codificador.py`).
- **O teste de identidade do motor não existe ainda**, porque depende do codificador. Parte 2.
- **O teste de vazamento desta parte é estático**: checa import e literal de CSV. A verificação em tempo de execução — rodar a espinha com `pandas.read_csv` instrumentado e exigir que todo caminho aberto seja o sujo ou os CSVs do guia — é da parte 2, quando houver espinha. Até lá, **o invariante está parcialmente coberto**, e isso não deve ser descrito como pronto.
- **Nenhuma chamada de API foi feita**, e nenhuma é possível: `provedor.py` é da parte 2.

## Auto-revisão deste plano

**Cobertura do spec.** §5.1 árvore → tarefas 1 a 8 cobrem 7 dos 14 arquivos; os outros 7 estão nomeados como parte 2. §5.2 espinha → parte 2. §5.3 tipos → tarefa 1. §5.4 fonte única → tarefa 5 cria `motor.py` sem import do repositório; o teste de identidade é parte 2, e isso está declarado. §6 etapa 1 → tarefa 7. §6 etapa 3 → tarefa 8. §6 etapas 2, 4, 5, 6 → parte 2. §7 guia → tarefa 2. §8 medição → tarefa 3; a medição na fatia nunca vista é parte 2, quando existir limpador para medir. §9 portão → tarefa 4; `provedor.py` é parte 2. §10 testes → o teste de vazamento está na tarefa 1, o do portão na 4, o de identidade e o invariante são parte 2.

**Lacuna consciente:** o spec §8 pede a decomposição do recall por fonte. `medir.py` já a calcula, mas ela só produz número quando o limpador expõe `aplicar_detalhado`, o que é parte 2. A interface está fixada aqui para a parte 2 não ter de mexer em `medir.py`.

**Consistência de tipos.** `Candidata.metricas` é escrito pelo crivo (tarefa 8) e lido pelo codificador (parte 2) com as chaves `marcadas`, `taxa`, `motivo`, `reparadas`, `motivo_reparo`, `detalhe`, `detalhe_reparo`. `detectar` e `reparar` têm `dominancia` como último parâmetro posicional nos dois. `reparar` devolve `(DataFrame, Series)` e o crivo desempacota assim. `aplicar(df) -> (df, flags)` é a interface do limpador, igual à da POC 1, e `medir.py` tenta `aplicar_detalhado` antes.

**Valores conferidos, não estimados.** Os números que o plano afirma foram produzidos rodando o código em 12/10/2026, não calculados de cabeça: o placar da POC 1 (tarefa 3) saiu do `avaliar_limpador.py` dela; as listas esperadas dos cinco tipos de detecção (tarefa 5), os valores de `padrao` (tarefa 7) e as distâncias de edição (tarefa 6) saíram de um script de verificação. Se algum deles falhar na execução, a divergência está na implementação, não no número.

**Correção feita durante a auto-revisão, que vale registrar.** A primeira versão deste plano usava Levenshtein puro, em que a transposição `Bosotn` → `Boston` custa 2. Como a exceção do determinante exige distância exatamente 1, o erro de digitação mais comum ficaria de fora do método. A métrica passou a ser Damerau-Levenshtein restrita. O spec e o `docs/REGRAS_DO_LIMPADOR.md` foram corrigidos junto.
