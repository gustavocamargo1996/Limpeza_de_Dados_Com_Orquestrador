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
