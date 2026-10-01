"""Script de exploração automatizada dos dados da camada Bronze.

Localiza os arquivos CSV mais recentes das pastas da camada Bronze,
gera relatórios HTML detalhados usando fg-data-profiling e salva na pasta relatorios/.
"""

from pathlib import Path
import pandas as pd
from data_profiling import ProfileReport

# Caminhos base
BRONZE_SIH = Path("dados/bronze/sih_sus")
BRONZE_NASA = Path("dados/bronze/nasa_power")
RELATORIOS = Path("relatorios")


def obter_arquivo_mais_recente(pasta: Path, padrao: str) -> Path:
    """Retorna o caminho do arquivo mais recente dentro da pasta informada."""
    arquivos = sorted(pasta.glob(padrao))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo encontrado em {pasta} com padrao {padrao}")
    return arquivos[-1]


def gerar_relatorio(
    caminho_csv: Path,
    prefixo: str,
    separador: str = ",",
    marcador_fim_cabecalho: str | None = None,
) -> Path:
    """Lê o arquivo CSV, gera o relatorio de perfilamento em HTML e salva no disco."""
    # Garante a criacao do diretorio de relatorios
    RELATORIOS.mkdir(exist_ok=True)

    print(f"Carregando dados de: {caminho_csv.name}...")
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

    df = pd.read_csv(caminho_csv, sep=separador, skiprows=linhas_ignoradas)

    # Inicializa e constrói o relatorio
    perfil = ProfileReport(
        df,
        title=f"Relatorio de Qualidade - {prefixo} ({caminho_csv.name})",
    )

    saida = RELATORIOS / f"perfil_{prefixo}_{caminho_csv.stem}.html"
    perfil.to_file(saida)
    print(f"Relatorio gerado com sucesso em: {saida}")
    return saida


def main() -> None:
    """Função principal que executa o perfilamento de todas as fontes da Bronze."""
    # 1. Fonte Primária: SIH/SUS
    try:
        csv_sih = obter_arquivo_mais_recente(BRONZE_SIH, "internacoes_*.csv")
        gerar_relatorio(csv_sih, "sih_sus", separador=";")
    except Exception as e:
        print(f"Erro ao perfilar SIH/SUS: {e}")

    # 2. Fonte Secundária: NASA POWER
    try:
        csv_nasa = obter_arquivo_mais_recente(BRONZE_NASA, "temperaturas_nasa_*.csv")
        gerar_relatorio(
            csv_nasa,
            "nasa_power",
            marcador_fim_cabecalho="-END HEADER-",
        )
    except Exception as e:
        print(f"Erro ao perfilar NASA POWER: {e}")


if __name__ == "__main__":
    main()