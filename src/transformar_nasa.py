"""Script de transformação da camada Bronze para Prata: NASA POWER.

Lê o CSV do NASA POWER, converte códigos de ausente (-999) para nulo,
converte a data (YEAR + DOY) para uma coluna de data real
e calcula o Atributo Derivado 'AMPLITUDE_TERMICA' (T2M_MAX - T2M_MIN).
"""

from datetime import datetime
import json
from pathlib import Path
import numpy as np
import pandas as pd

import limpeza

BRONZE_NASA = Path("dados/bronze/nasa_power")
PRATA_DIR = Path("dados/prata")


def carregar_dados() -> tuple[pd.DataFrame, Path]:
    """Carrega o CSV mais recente do NASA POWER na Bronze."""
    caminho_csv = limpeza.obter_arquivo_mais_recente(BRONZE_NASA, "temperaturas_nasa_*.csv")
    print(f"[NASA POWER] Lendo arquivo Bronze: {caminho_csv.name}")

    # Descarta o cabecalho descritivo da NASA até o marcador de encerramento.
    with caminho_csv.open(encoding="utf-8-sig") as arquivo:
        for numero_linha, linha in enumerate(arquivo):
            if linha.strip() == "-END HEADER-":
                linhas_ignoradas = numero_linha + 1
                break
        else:
            raise ValueError(f"Marcador '-END HEADER-' nao encontrado em {caminho_csv}")

    df = pd.read_csv(caminho_csv, skiprows=linhas_ignoradas)
    return df, caminho_csv


def converter_data(df: pd.DataFrame) -> pd.Series:
    """Monta a data a partir de YEAR e DOY (dia do ano) ou, se existirem, YEAR, MO e DY."""
    if {"YEAR", "MO", "DY"}.issubset(df.columns):
        datas = pd.to_datetime(
            pd.DataFrame({"year": df["YEAR"], "month": df["MO"], "day": df["DY"]}),
            errors="coerce",
        )
    elif {"YEAR", "DOY"}.issubset(df.columns):
        inicio_do_ano = pd.to_datetime(df["YEAR"].astype(int).astype(str), format="%Y")
        datas = inicio_do_ano + pd.to_timedelta(df["DOY"].astype(int) - 1, unit="D")
    else:
        raise ValueError("Colunas de data nao encontradas (esperado YEAR+DOY ou YEAR+MO+DY).")

    if datas.isna().any():
        raise ValueError(f"{int(datas.isna().sum())} linha(s) com data invalida.")

    return datas


def tratar_nasa(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica limpeza, converte a data e calcula o atributo derivado."""
    df = limpeza.tirar_espacos(df)

    # Padroniza nomes de colunas em maiúsculo
    df.columns = [c.upper() for c in df.columns]

    # Substitui valor ausente padrao do NASA POWER (-999) por NaN
    df = df.replace(-999, np.nan)
    df = df.replace("-999", np.nan)

    # Data: YEAR + DOY (ou YEAR + MO + DY) -> coluna de data, primeira da tabela
    df.insert(0, "DATA", converter_data(df))
    print("[NASA POWER] Coluna 'DATA' criada.")

    # Atributo Derivado: Amplitude Térmica (T2M_MAX - T2M_MIN)
    if "T2M_MAX" in df.columns and "T2M_MIN" in df.columns:
        df["AMPLITUDE_TERMICA"] = df["T2M_MAX"] - df["T2M_MIN"]
        if (df["AMPLITUDE_TERMICA"] < 0).any():
            raise ValueError("Amplitude termica negativa encontrada (T2M_MAX < T2M_MIN).")
        print("[NASA POWER] Atributo derivado 'AMPLITUDE_TERMICA' calculado.")

    return df


def salvar_prata(df: pd.DataFrame) -> Path:
    """Salva a tabela tratada em formato Parquet."""
    PRATA_DIR.mkdir(parents=True, exist_ok=True)
    destino = PRATA_DIR / "nasa_power.parquet"
    df.to_parquet(destino, index=False)
    print(f"[NASA POWER] Dados salvos em Parquet: {destino} ({len(df)} linhas)")
    return destino


def registrar_proveniencia(origem: Path, destino: Path, linhas_antes: int, linhas_depois: int) -> None:
    """Registra a proveniencia da Prata."""
    info = {
        "origem": origem.name,
        "arquivo_prata": destino.name,
        "linhas_antes": linhas_antes,
        "linhas_depois": linhas_depois,
        "decisoes": [
            "Ignoradas linhas do cabecalho descritivo da NASA ate -END HEADER-",
            "Valores ausentes -999 convertidos para NaN",
            "Data (YEAR + DOY) convertida para a coluna DATA",
            "Criado o atributo derivado AMPLITUDE_TERMICA (T2M_MAX - T2M_MIN)",
            "Validado que a amplitude termica nao e negativa",
            "Exportação para formato Parquet",
        ],
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }

    caminho_prov = PRATA_DIR / "proveniencia.jsonl"
    with caminho_prov.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")

    print(f"[NASA POWER] Proveniência registrada em: {caminho_prov}")


def main() -> None:
    """Executa o pipeline da Prata para o NASA POWER."""
    df_raw, caminho_origem = carregar_dados()
    linhas_antes = len(df_raw)

    df_clean = tratar_nasa(df_raw)
    destino = salvar_prata(df_clean)

    registrar_proveniencia(caminho_origem, destino, linhas_antes, len(df_clean))


if __name__ == "__main__":
    main()