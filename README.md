# Limpeza de dados com LLM: gerador de limpadores e orquestrador

Prova de conceito do mestrado de Gustavo Camargo (IME-USP), em parceria com o Centro de
Ciências de Dados da Fundação SEADE: um *framework* que usa LLMs para **gerar programas
de limpeza de dados** reexecutáveis, auditáveis e sem LLM na hora de rodar.

O repositório tem dois componentes, que funcionam separados:

| Componente | Pasta | O que faz |
|---|---|---|
| **Gerador de limpadores** | `limpeza2/` | recebe um CSV sujo e, opcionalmente, um **guia** (algumas linhas corrigidas por um humano) e escreve um **limpador**: um script Python autônomo, que corrige tabelas da mesma origem sem chamar LLM |
| **Orquestrador** | `orquestrador/` | interface web (Streamlit) em volta do gerador: ingestão, amostra-guia, acompanhamento da geração, relatórios, aprovação ou aperfeiçoamento do limpador, versionamento num *data lake* (SeaweedFS) e controle em SQLite |

O gerador roda sozinho, pela linha de comando. O orquestrador o chama em subprocesso.

---

## 1. Preparar o ambiente

### Requisitos

- **Windows ou Linux.** Os comandos deste README são do Windows (PowerShell); os do
  Linux estão na seção 1.1. **No macOS, o painel do orquestrador não acompanha a
  geração** (a verificação de processo vivo usa `/proc`); o resto segue os comandos do
  Linux.
- **Git.**
- **[uv](https://docs.astral.sh/uv/)**, que gerencia o Python e o ambiente virtual.
- **Python 3.14**, a única versão testada. O `uv` o baixa se faltar.
- **Uma chave da API da OpenAI**, ou um **Ollama** local (o caminho do Ollama existe, mas
  ainda não foi testado com o modelo real).
- **Só para o orquestrador:** o **SeaweedFS** (seção 3.1).

### Instalação

```powershell
git clone https://github.com/gustavocamargo1996/Limpeza_de_Dados_Com_Orquestrador.git
cd Limpeza_de_Dados_Com_Orquestrador
uv venv --python 3.14
uv pip install -r requirements.txt
```

O `uv` não instala `pip` dentro do ambiente. Instale pacotes sempre com
`uv pip install`, e rode o Python do ambiente com `.venv\Scripts\python`.

### Confira a instalação (sem gastar API)

```powershell
.venv\Scripts\python -m pytest
```

São cerca de 435 testes, e **nenhum chama a API**: os agentes de LLM são substituídos
por respostas gravadas. Leva de 3 a 7 minutos. Se tudo passar, o ambiente está pronto.

### Configure o provedor de LLM

Copie o exemplo e edite:

```powershell
copy .env.exemplo .env
```

| Variável | Valor |
|---|---|
| `PROVEDOR` | `openai`, `ollama`, `gravado` (reproduz um run gravado, sem API) ou `reaproveitar` (usado pelo orquestrador) |
| `MODELO` | o modelo, por exemplo `gpt-6-luna` |
| `OPENAI_API_KEY` | **a sua chave** |
| `OLLAMA_URL` | só com `PROVEDOR=ollama`, por exemplo `http://localhost:11434/v1` |
| `RESPOSTAS_GRAVADAS` | só com `PROVEDOR=gravado`: o `respostas.jsonl` a reproduzir |

O `.env` **nunca** vai para o git. Um `PROVEDOR` desconhecido falha de propósito, para
um erro de digitação não mandar dados para fora da rede.

**Custo e privacidade:** com `PROVEDOR=openai`, cada geração faz cerca de 30 chamadas
(no máximo 80) e **manda linhas da tabela para a OpenAI**. Use dados que você pode
enviar, ou o Ollama.

### 1.1 No Linux (e no macOS)

Duas diferenças em relação ao Windows:

- o Python do ambiente fica em **`.venv/bin/python`**, não em `.venv\Scripts\python`
  (no Linux não existe a pasta `Scripts`);
- variável de ambiente se define com **`export NOME=valor`**, não com
  `$env:NOME = "valor"`, e os caminhos usam `/`.

Os mesmos comandos das seções seguintes, na ordem em que aparecem:

```bash
# Instalação (uv: https://docs.astral.sh/uv/getting-started/installation/)
git clone https://github.com/gustavocamargo1996/Limpeza_de_Dados_Com_Orquestrador.git
cd Limpeza_de_Dados_Com_Orquestrador
uv venv --python 3.14
uv pip install -r requirements.txt

# Conferir a instalação (sem gastar API)
.venv/bin/python -m pytest

# Configurar o provedor de LLM (depois edite o .env)
cp .env.exemplo .env

# Gerar um limpador (seção 2)
.venv/bin/python -m limpeza2.espinha --sujo <arquivo.csv> --guia <pasta_do_guia> --nome <nome>

# Exemplo sem gastar API, reproduzindo o run gravado do beers
export PROVEDOR=gravado
export RESPOSTAS_GRAVADAS=tests/fixtures/respostas_beers_poc2.jsonl
.venv/bin/python -m limpeza2.espinha --sujo tests/fixtures/beers_dirty_300.csv --guia dados/guia/beers --nome beers
unset PROVEDOR RESPOSTAS_GRAVADAS   # volta a valer o que está no .env

# Usar o limpador gerado
.venv/bin/python saida/<pasta>/limpador_<...>.py entrada.csv saida.csv --flags flags.csv

# Medir contra o gabarito
.venv/bin/python medir.py --limpador saida/<pasta>/limpador_<...>.py --sujo tests/fixtures/beers_dirty_300.csv --limpo tests/fixtures/beers_clean_300.csv --guia dados/guia/beers

# Sortear um guia de benchmark
.venv/bin/python preparar_guia.py --dataset <nome> --sujo <sujo.csv> --limpo <limpo.csv> --linhas 20 --pares 2
```

O `export` vale só para o terminal aberto. Para o orquestrador (seção 3), o
`subir_seaweed.cmd` é só do Windows. No Linux, baixe o `weed` para Linux na mesma
página de releases e, da raiz do repositório, num terminal que fica aberto:

```bash
mkdir -p var/seaweed
weed server -dir=var/seaweed -ip=127.0.0.1 -s3 -s3.port=8333 -volume.port=9340
```

E noutro terminal:

```bash
.venv/bin/streamlit run orquestrador/app.py
```

---

## 2. O gerador de limpadores, isolado

### Gerar um limpador

```powershell
.venv\Scripts\python -m limpeza2.espinha --sujo <arquivo.csv> --guia <pasta_do_guia> --nome <nome>
```

- `--sujo`: o CSV a limpar. Ele é lido como texto literal (`N/A` continua `N/A`).
- `--guia`: **opcional**, uma pasta com até dois arquivos:
  - `guia_linhas.csv`: a coluna `_linha` (o índice da linha no CSV sujo, contando de 0,
    sem o cabeçalho) seguida de **todas** as colunas, com os valores **corretos**.
    Recomenda-se de 10 a 20 linhas;
  - `guia_pares.csv`: colunas `linha, coluna, sujo, limpo`, com erros apontados um a um.
  Sem guia, o gerador funciona, mas o recall cai muito (seção 4). O exemplo real está em
  `dados/guia/beers/`.
- `--nome`: o nome do dataset, usado nos arquivos.

A saída vai para `saida/<nome>_<AAAA-MM-DD_HHMM>/`:

| Arquivo | O que é |
|---|---|
| `limpador_<nome>_<carimbo>.py` | o **limpador**: um script autônomo, sem dependência deste repositório (só pandas) |
| `raciocinio_<nome>_<carimbo>.md` | cada regra proposta, aprovada ou não, com o motivo e as métricas |
| `respostas.jsonl` | todas as respostas do LLM; permite regenerar o mesmo limpador sem API |

**Exemplo sem gastar API**, reproduzindo o run gravado do `beers`:

```powershell
$env:PROVEDOR = "gravado"
$env:RESPOSTAS_GRAVADAS = "tests/fixtures/respostas_beers_poc2.jsonl"
.venv\Scripts\python -m limpeza2.espinha --sujo tests/fixtures/beers_dirty_300.csv --guia dados/guia/beers --nome beers
```

### Usar o limpador gerado

Pela linha de comando:

```powershell
.venv\Scripts\python saida\<pasta>\limpador_<...>.py entrada.csv saida.csv --flags flags.csv
```

`flags.csv` marca as células que o limpador apontou como erradas mas não soube corrigir.

Ou de dentro de outro programa Python:

```python
import importlib.util
import pandas as pd

spec = importlib.util.spec_from_file_location("limpador", "saida/<pasta>/limpador_<...>.py")
limpador = importlib.util.module_from_spec(spec)
spec.loader.exec_module(limpador)

df = pd.read_csv("entrada.csv", dtype=str, keep_default_na=False, na_values=[])
corrigido, flags, fontes = limpador.aplicar_detalhado(df)   # fontes: que regra escreveu cada célula
```

O limpador também expõe `REGRAS` (as regras aplicadas, em ordem), `RESIDUAL` (o
dicionário de substituições) e `GERACAO_TRUNCADA` (se a geração bateu no teto de
chamadas).

**Segurança:** as funções `corrigir_*` do limpador foram escritas pelo LLM. Elas passaram
por um portão de segurança na geração, mas o limpador entregue roda **sem** esse portão.
Revise o arquivo antes de usá-lo em produção.

### Medir um limpador contra o gabarito (benchmarks)

```powershell
.venv\Scripts\python medir.py --limpador saida\<pasta>\limpador_<...>.py --sujo tests/fixtures/beers_dirty_300.csv --limpo tests/fixtures/beers_clean_300.csv --guia dados/guia/beers
```

O `medir.py` executa o próprio limpador e compara com o CSV limpo. As linhas do guia
ficam **fora** da medição. A precisão que ele imprime segue a fórmula da POC 1, que
**não conta alterações em colunas sem erro**: por isso o `beers` aparece com 100% de
precisão no `medir.py` e 98,6% quando essas alterações são contadas.

Para sortear um guia de benchmark a partir do CSV limpo (só para experimentos; numa base
real o gabarito não existe):

```powershell
.venv\Scripts\python preparar_guia.py --dataset <nome> --sujo <sujo.csv> --limpo <limpo.csv> --linhas 20 --pares 2
```

O guia vai para `dados/guia/<nome>/`, com semente fixa.

**Benchmarks prontos:** `benchmark/` traz cinco datasets da literatura (`beers`,
`environment`, `flights`, `hospital` e `rayyan`, com 300 linhas cada), cada um com o
`sujo.csv`, o guia e o `limpo.csv`, e os comandos para gerar e medir. Veja
`benchmark/LEIA-ME.md`.

---

## 3. O orquestrador

### 3.1 O SeaweedFS (o *data lake*)

1. Baixe o SeaweedFS para Windows em
   <https://github.com/seaweedfs/seaweedfs/releases> e extraia o `weed.exe`.
2. Ponha a pasta do `weed.exe` no PATH, **ou** defina a variável `WEED` com o caminho
   dele.
3. Da raiz do repositório, num terminal que **fica aberto**:

   ```powershell
   .\subir_seaweed.cmd
   ```

   O S3 sobe em `127.0.0.1:8333`, acessível só desta máquina. Os dados ficam em
   `var\seaweed`, dentro do projeto. Para usar outra pasta, defina `SEAWEED_DADOS`.

Os arquivos do lago podem ser vistos no navegador em
<http://127.0.0.1:8888/buckets/limpeza/>, mas não os altere por lá: o banco de controle
do orquestrador não fica sabendo.

### 3.2 Abrir a interface

Noutro terminal, da raiz do repositório:

```powershell
.venv\Scripts\streamlit run orquestrador\app.py
```

A interface abre em <http://127.0.0.1:8501>, acessível só desta máquina. Se o SeaweedFS
não estiver no ar, ela mostra "Bucket indisponível".

### 3.3 O fluxo

1. **Ingestão:** envie um CSV e escolha o domínio (Meio Ambiente, Saúde, Educação...).
   O sistema verifica se o **esquema** (mesmo domínio e mesmo conjunto de colunas) já é
   conhecido e grava o original no lago, com o hash.
2. **Esquema novo:** dê um nome ao conjunto de dados.
3. **Amostra-guia:** o sistema sorteia linhas do seu dataset (20 por padrão, no mínimo
   10). Corrija os valores errados no formulário, ou baixe o template, corrija e envie.
   "Sortear de novo" troca uma linha que você não saiba corrigir. Opcionalmente, aponte
   erros em outras linhas. **O guia é a verdade:** nenhuma regra pode contradizê-lo.
4. **Parâmetros:** gerar sobre uma amostra (padrão de 300 linhas) ou sobre a tabela
   inteira. A tela mostra o provedor e o aviso de custo **antes** do botão.
5. **Geração:** o painel acompanha as etapas (detecção, geração de regras, geração de
   código), com cronômetro e contagem de chamadas.
6. **Resultado:** o relatório de geração (regras aprovadas e reprovadas, com o motivo em
   linguagem simples) e o relatório de limpeza (células alteradas por regra, exemplos de
   antes e depois).
7. **Decisão:**
   - **aprovar** grava o dataset corrigido e o relatório no lago;
   - **aperfeiçoar** permite rejeitar regras aprovadas, aprovar regras reprovadas (nunca
     as que contradizem o guia) e dar instruções ao agente. A versão nova **reaproveita as
     respostas já gravadas** e só chama a API para o que mudou.

Num **esquema conhecido**, o sistema aplica o último limpador aprovado e oferece aprovar
o resultado ou gerar uma versão nova, que herda as regras aprovadas e o guia da primeira
ingestão.

**Datasets para experimentar:** `simulacao/` traz o `beers` e o `environment` (300
linhas cada), com o guia já corrigido nas linhas que o app sorteia. Veja
`simulacao/LEIA-ME.md`.

### 3.4 Onde ficam os dados do orquestrador

| O quê | Onde | Vai para o git? |
|---|---|---|
| banco de controle (esquemas, versões, processos, dados) | `var/controle.sqlite` | **não** |
| pastas de trabalho dos processos | `var/trabalho/` | **não** |
| *data lake* (originais, guias, limpadores, corrigidos) | `var/seaweed/` ou `SEAWEED_DADOS` | **não** |

O SQLite **não acompanha o repositório**: é o estado de **uma** instalação, e só faz
sentido junto do lago e das pastas de trabalho da mesma máquina. Ele é **criado
automaticamente**, vazio, na primeira vez que a interface abre. Os caminhos podem ser
trocados no `.env` com `SQLITE`, `TRABALHO`, `S3_ENDPOINT` e `S3_BUCKET`.

---

## 4. Resultados medidos

Com `gpt-6-luna`, em tabelas de 300 linhas, com as linhas do guia fora da medição:

| Dataset | Guia | Precisão | Recall | F1 |
|---|---|---|---|---|
| beers | 20 linhas + 10 pares | 98,6% | 98,4% | 98,5% |
| beers | sem guia | 82,7% | 9,7% | 17,3% |
| environment | 20 linhas | 95,2% | 74,1% | 83,3% |
| environment | sem guia | 50,0% | 16,0% | 24,3% |

O guia é o que mais pesa no resultado. Detalhes e limitações em `docs/CONTINUACAO.md`.

**Limites conhecidos:** testado só em tabelas de até 300 linhas e 11 colunas, em inglês.
Nenhuma regra move um valor de uma coluna para outra. O dicionário residual só cobre
valores já vistos na geração.

---

## 5. Para quem vai desenvolver

| Documento | Conteúdo |
|---|---|
| `CLAUDE.md` | as regras do projeto e a arquitetura dos dois componentes |
| `docs/CONTINUACAO.md` | o estado do projeto e os resultados |
| `docs/DECISOES.md` | as decisões de desenho, com âncoras |
| `docs/REGRAS_DO_LIMPADOR.md` | o limpador explicado em linguagem de usuário |
| `docs/superpowers/specs/` | as especificações do gerador e do orquestrador |
