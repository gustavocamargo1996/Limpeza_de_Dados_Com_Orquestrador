# Especificação — Orquestrador do Framework de Limpeza de Dados

## Objetivo

O objetivo desta especificação é construir um orquestrador que utilize o gerador de código de limpeza de dados já desenvolvido como componente central.

Esse orquestrador será uma prova de conceito (PoC) do framework proposto na qualificação do mestrado.

## 1. Funcionalidades do orquestrador

O orquestrador deverá disponibilizar uma interface simplificada para interação com o usuário e acompanhamento das etapas de processamento.

### 1.1. Ingestão do dataset

A interface deverá permitir que o usuário realize o upload do dataset que deseja limpar.

Durante a ingestão, o sistema deverá solicitar o domínio ao qual o dataset pertence. Exemplos de domínios:

- Meio Ambiente
- Segurança
- Transporte
- Demografia
- Economia
- Saúde
- Educação
- Outros

### 1.2. Painel de acompanhamento do processamento

A interface deverá apresentar um painel de controle para acompanhamento das etapas do processamento, conforme descrito a seguir.

**1.2.a. Identificação do esquema**

O sistema deverá verificar se o esquema do dataset é conhecido e se já existe um código limpador gerado para ele.

**1.2.b. Armazenamento do dado original**

O dataset original deverá ser importado para o data lake (bucket S3).

- **Esquema conhecido:** armazenar a nova extração no diretório correspondente, registrando sua data e hash.
- **Esquema desconhecido:** solicitar ao usuário um nome para o novo conjunto de dados e criar o diretório correspondente ao novo esquema.

**1.2.c. Proposição de limpador para um novo esquema**

Caso o esquema seja novo, o sistema deverá iniciar a etapa de proposição de um limpador.

Para isso, deverá solicitar ao usuário uma **amostra-guia**, ou seja, uma pequena amostra de registros considerados corretos, sem erros de tipagem ou conteúdo.

A interface deverá oferecer duas alternativas para o preenchimento dessa amostra:

1. Disponibilizar um template para download, preenchimento e posterior upload.
2. Disponibilizar um formulário na própria interface, apresentando as colunas do dataset e uma quantidade mínima de linhas (por exemplo, cinco) para preenchimento pelo usuário.

**1.2.d. Acompanhamento da geração do limpador**

Após a inserção dos dados necessários, o sistema deverá iniciar o processamento do gerador de código de limpeza.

Durante a execução, a interface deverá indicar a etapa atual do processamento:

- Detecção
- Geração de regras
- Geração de código

Também deverá apresentar um indicador visual de carregamento e o tempo de processamento.

**1.2.e. Armazenamento e versionamento do limpador**

Após a geração do código, o limpador deverá ser salvo e versionado em um subdiretório específico do esquema, destinado ao armazenamento das versões de limpadores geradas para aquele conjunto de dados.

**1.2.f. Relatórios de geração e limpeza**

O orquestrador deverá disponibilizar dois relatórios ao usuário:

**Relatório de geração do limpador**

Deverá apresentar, de forma amigável e compreensível, as regras propostas durante a geração do código, incluindo:

- Regras geradas e aprovadas.
- Regras não aprovadas.
- Justificativa para a não aprovação de cada regra rejeitada.

**Relatório de limpeza**

Deverá apresentar as regras validadas e os resultados de sua aplicação ao dataset, incluindo:

- Identificação de cada regra validada.
- Quantidade de células impactadas por cada regra.
- Pequena amostra das células modificadas, apresentando seus valores antes e depois da correção.

O relatório de limpeza poderá compartilhar informações com o relatório de geração do limpador.

**1.2.g. Aprovação ou aperfeiçoamento do limpador**

Após a apresentação dos relatórios, o sistema deverá perguntar ao usuário se deseja aprovar ou aperfeiçoar o limpador gerado.

- **Aprovação:** o dataset limpo deverá ser armazenado no subdiretório de dados corrigidos do bucket, encerrando o processo.
- **Aperfeiçoamento:** o usuário poderá solicitar a aprovação de uma regra anteriormente rejeitada ou a rejeição de uma regra anteriormente aprovada.

As instruções de aperfeiçoamento deverão realimentar o especificador, iniciando um novo ciclo de especificação, geração de regras e validação.

**Restrição importante:** o sistema não deverá aceitar instruções do usuário que contradigam as verdades estabelecidas pelo esquema e pela amostra-guia. Ou seja, o usuário não poderá contradizer as restrições que ele próprio estabeleceu no início do processo.

**1.2.h. Processamento de esquemas já conhecidos**

As etapas 1.2.c a 1.2.g representam o ciclo de criação de um novo limpador.

Quando o esquema já for conhecido, o sistema deverá:

1. Recuperar a versão mais recente do limpador disponível no diretório correspondente ao esquema.
2. Tentar realizar a limpeza do novo dataset utilizando essa versão.
3. Gerar e apresentar o relatório de limpeza.
4. Perguntar ao usuário se deseja aprovar o resultado ou gerar uma nova versão do limpador.

Caso o usuário opte por gerar uma nova versão, o processo deverá considerar:

- As regras já aprovadas nas versões anteriores.
- A amostra-guia disponibilizada na primeira ingestão daquele esquema.
- A nova amostra de dados recebida.

A partir dessas informações, deverá ser iniciado um novo ciclo de geração e validação do limpador.

## 2. Armazenamento de dados — Data Lake

O projeto deverá utilizar um bucket para armazenar os artefatos produzidos e utilizados pelo sistema, incluindo:

- Datasets originais.
- Datasets corrigidos.
- Códigos limpadores gerados.
- Amostras-guia.
- Relatórios de geração e limpeza.

### 2.1. Organização dos diretórios

Sugestão de estrutura:

```text
<Dominio>/
    <Esquema>/
        Original/
            <Extraido_em>/
        Corrigido/
            <Gerado_em>/
        Limpador/
            <Gerado_em>/
        Amostra_Guia/
            <Importada_em>/
```

A organização deverá seguir as seguintes regras:

| Diretório | Conteúdo |
|---|---|
| Original | Dataset original, organizado pela data de extração. |
| Corrigido | Dataset corrigido e relatório de limpeza. |
| Limpador | Código limpador gerado e relatório de geração. |
| Amostra_Guia | Amostra-guia fornecida pelo usuário. |

### 2.2. Tecnologia

Utilizar **SeaweedFS**, com armazenamento compatível com S3.

Acredito que já exista uma instalação do SeaweedFS neste computador. Verificar essa possibilidade antes de realizar uma nova instalação.

## 3. Banco de dados de controle

O projeto deverá utilizar um banco SQLite para armazenar os metadados de controle dos esquemas, limpadores, etapas, processos e datasets.

### 3.1. Tabela de esquemas disponíveis

Deverá conter os seguintes campos:

- `ID_ESQUEMA`
- `DOMINIO`
- `NOME_ESQUEMA`
- `CAMPOS_ESQUEMA` — conjunto de campos que compõem o esquema.
- `DIRETORIO_BUCKET`
- `DATA_CRIACAO`

### 3.2. Tabela de controle dos limpadores gerados

Deverá conter os seguintes campos:

- `ID_LIMPADOR`
- `DOMINIO`
- `NOME_ESQUEMA`
- `DATA_CRIACAO`
- `STATUS_APROVACAO` — aprovado ou reprovado.

### 3.3. Tabela de domínio das etapas

Deverá armazenar as etapas possíveis do processamento, contendo:

- `ID_ETAPA`
- `NOME_ETAPA`
- `DESCRICAO_ETAPA`

As etapas deverão ser definidas de acordo com o fluxo funcional descrito na Seção 1.

### 3.4. Tabela de controle de processos

Deverá permitir o acompanhamento da execução de cada etapa do processamento, contendo:

- `ID_PROCESSO`
- `ID_ESQUEMA`
- `NOME_ESQUEMA`
- `HASH_DADO`
- `ID_ETAPA`
- `DATA_INICIO_ETAPA`
- `STATUS` — em andamento, concluído com sucesso ou concluído com erro.
- `DATA_HORA_INICIO_PROCESSO`
- `DATA_HORA_CONCLUSAO`
- `TEMPO_PROCESSAMENTO`

### 3.5. Tabela de controle dos dados

Deverá conter os seguintes campos:

- `ID_CONTROLE_DADO`
- `HASH`
- `DOMINIO`
- `NOME_ESQUEMA`
- `DIRETORIO_ORIGINAL`
- `DIRETORIO_CORRIGIDO`
- `LIMPADOR_UTILIZADO`
- `DATA_HORA_INGESTAO`

### 3.6. Tecnologia

Utilizar **SQLite**.

## 4. Orientações para implementação

### 4.1. Tecnologias e estratégias de orquestração

Propor estratégias e tecnologias para implementação do controlador de tarefas e do front-end.

Priorizar soluções simples e de baixa complexidade, considerando que o projeto é uma prova de conceito acadêmica desenvolvida no contexto de um mestrado.

### 4.2. Organização e qualidade do código

Assim como no gerador de limpadores já desenvolvido, manter os módulos organizados por responsabilidade e função.

Evitar verbosidade desnecessária no código e nos comentários, priorizando uma implementação objetiva e de fácil manutenção.

### 4.3. Preservação do gerador de limpadores existente

**É fundamental minimizar as alterações no código do gerador de limpadores já desenvolvido.**

Esse componente consiste em um conjunto de arquivos Python (`.py`) que recebe um dataset e executa, de forma autônoma e sem supervisão, as etapas de detecção, especificação e geração de código de limpeza.

Reconheço que pequenas adaptações poderão ser necessárias, principalmente no especificador, para permitir os ciclos de realimentação previstos nesta especificação.

Entretanto, essas alterações não deverão comprometer o funcionamento original do gerador.

**O gerador de limpadores deverá continuar funcionando de maneira independente, mesmo sem o novo orquestrador.**

O objetivo deste projeto é construir um invólucro que utilize o gerador existente como componente central do framework proposto na qualificação, sem substituir ou descaracterizar seu funcionamento atual.

### 4.4. Separação dos componentes no projeto

A estrutura de diretórios do projeto deverá deixar clara a separação entre:

- **Gerador de limpadores:** código Python já existente, responsável pela detecção, especificação e geração do código de limpeza.
- **Orquestrador:** novo componente responsável pela interface com o usuário, controle do fluxo de processamento, armazenamento, versionamento, relatórios e ciclos de aprovação e aperfeiçoamento.

Essa separação deverá ser preservada tanto na organização dos diretórios quanto nas responsabilidades dos módulos, evitando o acoplamento desnecessário entre os dois componentes.
