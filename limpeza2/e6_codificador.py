"""Etapa 6: agente codificador -> escreve os artefatos de saida."""
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
    cliente = provedor.cliente()
    teto = sum(n["status"] == "teto" for n in cliente.registro)
    caminho = destino / f"limpador_{destino.name}.py"
    texto = _limpador(deteccoes, reparos, residual, entrada, cliente.chamadas, teto, destino.name)
    # newline="" grava o motor com os bytes que ele tem no disco.
    caminho.write_text(texto, encoding="utf-8", newline="")
    (destino / f"raciocinio_{destino.name}.md").write_text(
        _raciocinio(todas, reparos, residual, entrada, cliente, teto, destino.name), encoding="utf-8")
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


def _limpador(deteccoes, reparos, residual, entrada, chamadas, teto, nome):
    """O texto do limpador: cabecalho, motor lido do disco, literais e funcoes renomeadas."""
    motor = MOTOR.read_text(encoding="utf-8", newline="")
    funcoes = [(r.parametros["funcao"], r.codigo) for r in reparos if r.estrategia == "normalizar"]
    return "\n".join([
        _cabecalho(entrada, chamadas, nome),
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


def _cabecalho(entrada, chamadas, nome):
    """A docstring do limpador: origem, modelo, braco, aviso do portao e as memorias congeladas."""
    braco = ("sem guia" if entrada.guia_linhas.empty else
             f"guia de {len(entrada.guia_linhas)} linhas e {len(entrada.guia_pares)} pares")
    return (f'"""Limpador gerado pela POC 2 de limpeza de dados: {nome}.\n\n'
            f"Modelo {config.MODELO} ({config.PROVEDOR}), {chamadas} chamadas; {braco}.\n\n"
            "AVISO: este arquivo roda SEM o portao AST que validou as funcoes corrigir_* na geracao.\n"
            "Revise antes de usar em producao.\n\n"
            "Memoria congelada: RESIDUAL e o dominio de vizinho_no_dominio valem para valores\n"
            'ja vistos na tabela de geracao; nao cobrem valor inedito.\n"""')


def _raciocinio(todas, reparos, residual, entrada, cliente, teto, nome):
    """O Markdown com cada regra proposta, aprovada ou nao, e o porque."""
    reparo_de = {id(r.candidata): r for r in reparos}
    nao_ok = [n for n in cliente.registro if n["status"] != "ok"]
    linhas = [f"# Raciocinio do limpador {nome}", "",
              f"- modelo: {config.MODELO} ({config.PROVEDOR}), raciocinio {config.ESFORCO_RACIOCINIO}",
              f"- supervisao: {len(entrada.guia_linhas) * len(entrada.sujo.columns)} celulas do guia + {len(entrada.guia_pares)} pares",
              f"- chamadas: {cliente.chamadas}; tokens: {sum(n['tokens'] for n in cliente.registro)}",
              f"- unidades sem regra pelo teto de chamadas: {teto}"]
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
