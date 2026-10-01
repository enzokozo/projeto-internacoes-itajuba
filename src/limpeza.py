"""Módulo de funções genéricas de limpeza de dados.

Funções de higienização de texto, tratamento de espaços e
padronização aplicáveis a qualquer fonte de dados do projeto.
"""

from pathlib import Path
import pandas as pd


def tirar_espacos(df: pd.DataFrame) -> pd.DataFrame:
    """Remove espaços nas extremidades dos nomes das colunas e células de texto."""
    df.columns = df.columns.str.strip()

    for coluna in df.select_dtypes(include=["object", "string"]):
        df[coluna] = df[coluna].astype(str).str.strip()

    return df


def chave_texto(serie: pd.Series) -> pd.Series:
    """Padroniza uma série de texto para comparação e junção.

    Converte para minúsculas, remove espaços nas extremidades e elimina acentos.
    """
    s = serie.astype(str).str.strip().str.lower()
    s = s.str.normalize("NFKD")
    s = s.str.encode("ascii", errors="ignore")
    return s.str.decode("utf-8")


def aplicar_mapa(serie: pd.Series, mapa: dict) -> pd.Series:
    """Substitui variantes de texto pelos valores canonicos do dicionario."""
    return serie.replace(mapa)


def obter_arquivo_mais_recente(pasta: Path, padrao: str) -> Path:
    """Localiza o arquivo mais recente em uma pasta ordenando pelo nome."""
    arquivos = sorted(pasta.glob(padrao))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo encontrado em {pasta} com o padrao '{padrao}'.")
    return arquivos[-1]