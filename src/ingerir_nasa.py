"""Script de ingestão da fonte secundária: NASA POWER.

Localiza o CSV meteorológico baixado do NASA POWER, copia o arquivo
para a camada Bronze com a data no nome e registra a proveniência.
"""

from datetime import date, datetime
import json
import logging
from pathlib import Path
import shutil

import config
from config import ORIGEM_NASA as CAMINHO_ORIGEM, BRONZE_NASA, URL_NASA as FONTE_URL

log = logging.getLogger(__name__)


def copiar_para_bronze(origem: Path) -> Path:
    """Copia o arquivo de dados brutos para a camada Bronze sem alterar o conteúdo."""
    if not origem.exists():
        raise FileNotFoundError(
            f"Ficheiro de origem nao encontrado em: {origem}. "
            "Por favor, coloque o ficheiro nasa_raw.csv na pasta dados/."
        )

    # Garante que a pasta de destino exista
    BRONZE_NASA.mkdir(parents=True, exist_ok=True)

    # Formata a data atual no padrão AAAAMMDD
    hoje = date.today().strftime("%Y%m%d")
    destino = BRONZE_NASA / f"temperaturas_nasa_{hoje}.csv"

    # Rodar duas vezes no mesmo dia sobrescreve a copia de hoje.
    if destino.exists():
        log.warning("%s ja existia e foi sobrescrito", destino.name)

    # Copia o arquivo sem alterar o conteúdo
    shutil.copy(origem, destino)
    log.info("copiado para a bronze: %s", destino.name)
    return destino


def registrar_proveniencia(origem: Path, destino: Path) -> None:
    """Registra as informações de rastreabilidade no arquivo proveniencia.jsonl."""
    info = {
        "fonte": "NASA POWER (Prediction Of Worldwide Energy Resources)",
        "url_origem": FONTE_URL,
        "ficheiro_origem": origem.name,
        "ficheiro_bronze": destino.name,
        "extraido_em": datetime.now().isoformat(),
        "descricao": "Dados meteorológicos diários de temperatura, umidade e precipitação para Itajubá/MG",
    }

    caminho_prov = BRONZE_NASA / "proveniencia.jsonl"

    # Acrescenta uma nova linha (modo 'a') para preservar o histórico
    with caminho_prov.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")

    log.debug("proveniencia registrada em: %s", caminho_prov)


def main() -> None:
    """Função principal do fluxo de ingestão do NASA POWER."""
    destino = copiar_para_bronze(CAMINHO_ORIGEM)
    registrar_proveniencia(CAMINHO_ORIGEM, destino)


if __name__ == "__main__":
    config.configurar_log()
    main()