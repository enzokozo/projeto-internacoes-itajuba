"""Script de transformação da camada Bronze para Prata: SIH/SUS.

Lê o CSV bruto mais recente do SIH/SUS (separador ';'), mantém apenas as linhas
mensais, remove totais anuais, total geral e rodapés do TabNet, converte o período
para data, converte as contagens de internação para inteiro e grava em Parquet.
"""

from datetime import datetime
import json
from pathlib import Path
import pandas as pd

import limpeza

BRONZE_SIH = Path("dados/bronze/sih_sus")
PRATA_DIR = Path("dados/prata")

# O TabNet escreve os meses por extenso; as chaves já estão sem acento e em minúsculo
MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}


def carregar_dados() -> tuple[pd.DataFrame, Path]:
    """Carrega o CSV mais recente do SIH/SUS na Bronze (separador ';')."""
    caminho_csv = limpeza.obter_arquivo_mais_recente(BRONZE_SIH, "internacoes_*.csv")
    print(f"[SIH/SUS] Lendo arquivo Bronze: {caminho_csv.name}")

    try:
        df = pd.read_csv(caminho_csv, sep=";", encoding="utf-8", dtype=str)
    except UnicodeDecodeError:
        df = pd.read_csv(caminho_csv, sep=";", encoding="latin1", dtype=str)

    return df, caminho_csv


def converter_periodo(serie: pd.Series) -> pd.Series:
    """Converte textos como '..Janeiro/2010' para o primeiro dia do mês (datetime)."""
    partes = serie.str.lstrip(".").str.split("/", expand=True)
    mes = limpeza.chave_texto(partes[0]).map(MESES)
    ano = pd.to_numeric(partes[1], errors="coerce")

    if mes.isna().any() or ano.isna().any():
        invalidos = serie[mes.isna() | ano.isna()].tolist()
        raise ValueError(f"Períodos fora do padrão 'Mês/Ano': {invalidos}")

    return pd.to_datetime(
        pd.DataFrame({"year": ano.astype(int), "month": mes.astype(int), "day": 1})
    )


def tratar_sih(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica limpeza e padronização aos dados do SIH/SUS."""
    df = limpeza.tirar_espacos(df)

    colunas = df.columns.tolist()
    col_periodo = colunas[0]
    colunas_valores = colunas[1:]

    # Mantém apenas as linhas mensais (o TabNet as marca com '..' na frente).
    # Isso descarta, de uma vez, os totais anuais ('2010'), o 'Total' geral e os rodapés.
    df = df[df[col_periodo].str.startswith("..")].copy()

    # Período: texto -> data (primeiro dia do mês)
    df[col_periodo] = converter_periodo(df[col_periodo])
    df = df.rename(columns={col_periodo: "PERIODO"})

    # No TabNet, '-' significa zero ocorrências (não é dado faltante).
    # Valores inesperados geram erro em vez de virar zero em silêncio.
    for col in colunas_valores:
        df[col] = (
            df[col]
            .str.replace(".", "", regex=False)
            .str.replace("-", "0", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="raise").astype("int64")

    # Validação: a soma das faixas etárias deve ser igual à coluna Total em todos os meses.
    faixas = [c for c in colunas_valores if c.lower() != "total"]
    if "Total" in colunas_valores:
        divergentes = df[df[faixas].sum(axis=1) != df["Total"]]
        if not divergentes.empty:
            raise ValueError(
                f"Soma das faixas etárias difere do Total em {len(divergentes)} mês(es): "
                f"{divergentes['PERIODO'].dt.strftime('%Y-%m').tolist()}"
            )

    return df.reset_index(drop=True)


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
            "Leitura do CSV com separador ';'",
            "Remocao de espacos em branco",
            "Mantidas apenas as linhas mensais; removidos totais anuais, Total geral e rodapés do TabNet",
            "Período convertido de texto ('..Janeiro/2010') para data (primeiro dia do mês)",
            "Hífen '-' do TabNet interpretado como zero e contagens convertidas para int64",
            "Validado que a soma das faixas etárias é igual ao Total em todos os meses",
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
