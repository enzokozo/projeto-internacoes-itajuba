"""Script de exploração automatizada dos dados da camada Bronze.

Localiza os arquivos CSV mais recentes das pastas da camada Bronze,
gera relatórios HTML detalhados usando fg-data-profiling e salva na pasta relatorios/.

Nao faz parte do pipeline.py: e opcional e lento. Rode a parte:
    python src/explorar.py
"""

import logging
from pathlib import Path
import sys

import pandas as pd
from data_profiling import ProfileReport

import config
from config import BRONZE_SIH, BRONZE_NASA, RELATORIOS
from limpeza import obter_arquivo_mais_recente

log = logging.getLogger(__name__)


def gerar_relatorio(
    caminho_csv: Path,
    prefixo: str,
    separador: str = ",",
    marcador_fim_cabecalho: str | None = None,
) -> Path:
    """Lê o arquivo CSV, gera o relatorio de perfilamento em HTML e salva no disco."""
    # Garante a criacao do diretorio de relatorios
    RELATORIOS.mkdir(exist_ok=True)

    log.info("carregando dados de: %s", caminho_csv.name)
    linhas_ignoradas = 0
    if marcador_fim_cabecalho is not None:
        with caminho_csv.open(encoding="utf-8-sig") as arquivo:
            for numero_linha, linha in enumerate(arquivo):
                if linha.strip() == marcador_fim_cabecalho:
                    linhas_ignoradas = numero_linha + 1
                    break
            else:
                raise ValueError(
                    f"Marcador {marcador_fim_cabecalho!r} nao encontrado em {caminho_csv}"
                )
        log.debug("%d linhas de cabecalho ignoradas", linhas_ignoradas)

    df = pd.read_csv(caminho_csv, sep=separador, skiprows=linhas_ignoradas)

    # Inicializa e constrói o relatorio
    perfil = ProfileReport(
        df,
        title=f"Relatorio de Qualidade - {prefixo} ({caminho_csv.name})",
    )

    saida = RELATORIOS / f"perfil_{prefixo}_{caminho_csv.stem}.html"
    perfil.to_file(saida)
    log.info("relatorio gerado: %s", saida.name)
    return saida


def main() -> int:
    """Função principal que executa o perfilamento de todas as fontes da Bronze.

    Os dois relatorios sao independentes: se um falhar, o outro ainda e
    gerado. Mas a falha fica registrada com o rastro completo, e o script
    termina com codigo de erro, em vez de fingir que deu tudo certo.
    """
    falhas = 0

    # Fonte Primária: SIH/SUS
    try:
        csv_sih = obter_arquivo_mais_recente(BRONZE_SIH, "internacoes_*.csv")
        gerar_relatorio(csv_sih, "sih_sus", separador=";")
    except Exception:
        log.exception("erro ao perfilar SIH/SUS")
        falhas += 1

    # Fonte Secundária: NASA POWER
    try:
        csv_nasa = obter_arquivo_mais_recente(BRONZE_NASA, "temperaturas_nasa_*.csv")
        gerar_relatorio(
            csv_nasa,
            "nasa_power",
            marcador_fim_cabecalho="-END HEADER-",
        )
    except Exception:
        log.exception("erro ao perfilar NASA POWER")
        falhas += 1

    if falhas:
        log.error("%d de 2 relatorios falharam", falhas)
    return falhas


if __name__ == "__main__":
    config.configurar_log()
    sys.exit(1 if main() else 0)