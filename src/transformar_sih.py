"""Script de transformação da camada Bronze para Prata: SIH/SUS.

Lê o CSV bruto mais recente do SIH/SUS, remove linhas de total e rodapés do TabNet,
converte os valores de internação para tipo inteiro e grava em Parquet.
"""

from datetime import datetime
import json
from pathlib import Path
import pandas as pd

import limpeza

BRONZE_SIH = Path("dados/bronze/sih_sus")
PRATA_DIR = Path("dados/prata")


def carregar_dados() -> tuple[pd.DataFrame, Path]:
    """Carrega o CSV mais recente do SIH/SUS na Bronze."""
    caminho_csv = limpeza.obter_arquivo_mais_recente(BRONZE_SIH, "internacoes_*.csv")
    print(f"[SIH/SUS] Lendo arquivo Bronze: {caminho_csv.name}")

    try:
        df = pd.read_csv(caminho_csv, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(caminho_csv, encoding="latin1")

    return df, caminho_csv


def tratar_sih(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica limpeza e padronização aos dados do SIH/SUS."""
    df = limpeza.tirar_espacos(df)

    # Filtra linhas de cabeçalho/rodapé do TabNet
    colunas = df.columns.tolist()
    col_periodo = colunas[0]
    df = df[df[col_periodo].notna()].copy()
    df = df[~df[col_periodo].astype(str).str.contains("Total|Fonte|Notas", case=False)].copy()

    # Converter colunas numéricas de internação para inteiro
    for col in colunas[1:]:
        if any(termo in col.lower() for termo in ["internacoes", "qtd", "quantidade", "valor", "total"]):
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace("-", "0", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int64")

    return df


def salvar_prata(df: pd.DataFrame) -> Path:
    """Salva os dados no formato Parquet na Prata."""
    PRATA_DIR.mkdir(parents=True, exist_ok=True)
    destino = PRATA_DIR / "sih_sus.parquet"
    df.to_parquet(destino, index=False)
    print(f"[SIH/SUS] Dados salvos em Parquet: {destino} ({len(df)} linhas)")
    return destino


def registrar_proveniencia(origem: Path, destino: Path, linhas_antes: int, linhas_depois: int) -> None:
    """Registra o histórico de transformação na Prata."""
    info = {
        "origem": origem.name,
        "arquivo_prata": destino.name,
        "linhas_antes": linhas_antes,
        "linhas_depois": linhas_depois,
        "decisoes": [
            "Remocao de espacos em branco",
            "Filtragem de linhas de total e rodapés do TabNet",
            "Conversão de internações para int64",
            "Exportação para formato Parquet",
        ],
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }

    caminho_prov = PRATA_DIR / "proveniencia.jsonl"
    with caminho_prov.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")

    print(f"[SIH/SUS] Proveniência registrada em: {caminho_prov}")


def main() -> None:
    """Executa o pipeline da Prata para o SIH/SUS."""
    df_raw, caminho_origem = carregar_dados()
    linhas_antes = len(df_raw)

    df_clean = tratar_sih(df_raw)
    destino = salvar_prata(df_clean)

    registrar_proveniencia(caminho_origem, destino, linhas_antes, len(df_clean))


if __name__ == "__main__":
    main()