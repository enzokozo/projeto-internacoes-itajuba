"""Script de ingestao da fonte secundaria: NASA POWER.

Processa o CSV meteorológico descarregado do NASA POWER,
copia-o para a camada Bronze com a data no nome e regista a proveniencia.
"""

from datetime import date, datetime
import json
from pathlib import Path
import shutil

# Definição dos caminhos de origem e destino
CAMINHO_ORIGEM = Path("dados/nasa_raw.csv")  # Caminho do CSV descarregado
BRONZE_NASA = Path("dados/bronze/nasa_power")
FONTE_URL = "https://power.larc.nasa.gov/"


def copiar_para_bronze(origem: Path) -> Path:
    """Copia o ficheiro de dados brutos para a camada Bronze sem alterar o conteúdo."""
    if not origem.exists():
        raise FileNotFoundError(
            f"Ficheiro de origem nao encontrado em: {origem}. "
            "Por favor, coloque o ficheiro nasa_raw.csv na pasta dados/."
        )

    # Garante a criação da pasta de destino
    BRONZE_NASA.mkdir(parents=True, exist_ok=True)

    # Formata a data atual no padrao AAAAMMDD
    hoje = date.today().strftime("%Y%m%d")
    destino = BRONZE_NASA / f"temperaturas_nasa_{hoje}.csv"

    # Copia mantendo o conteúdo intacto
    shutil.copy(origem, destino)
    print(f"[NASA POWER] Ficheiro copiado para: {destino}")
    return destino


def registrar_proveniencia(origem: Path, destino: Path) -> None:
    """Regista informacoes de rastreabilidade no proveniencia.jsonl."""
    info = {
        "fonte": "NASA POWER (Prediction Of Worldwide Energy Resources)",
        "url_origem": FONTE_URL,
        "ficheiro_origem": origem.name,
        "ficheiro_bronze": destino.name,
        "extraido_em": datetime.now().isoformat(),
        "descricao": "Dados meteorológicos diários de temperatura, umidade e precipitação para Itajubá/MG",
    }

    caminho_prov = BRONZE_NASA / "proveniencia.jsonl"

    # Acrescenta nova linha de registo (modo 'a') para preservar o histórico
    with caminho_prov.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")

    print(f"[NASA POWER] Proveniencia registrada em: {caminho_prov}")


def main() -> None:
    """Função principal do fluxo de ingestão do NASA POWER."""
    destino = copiar_para_bronze(CAMINHO_ORIGEM)
    registrar_proveniencia(CAMINHO_ORIGEM, destino)


if __name__ == "__main__":
    main()