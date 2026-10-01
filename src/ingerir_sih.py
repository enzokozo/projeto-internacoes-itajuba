"""Script de ingestao da fonte primaria: SIH/SUS (TabNet / DataSUS).

Localiza o CSV descarregado, copia-o para a camada Bronze
com a data de extração no nome e regista a proveniencia.
"""

from datetime import date, datetime
import json
from pathlib import Path
import shutil

# Definição dos caminhos de origem e destino
CAMINHO_ORIGEM = Path("dados/sih_sus_raw.csv")  # Caminho do CSV descarregado
BRONZE_SIH = Path("dados/bronze/sih_sus")
FONTE_URL = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nimg.def"


def copiar_para_bronze(origem: Path) -> Path:
    """Copia o ficheiro de dados brutos para a pasta Bronze com a data no nome."""
    if not origem.exists():
        raise FileNotFoundError(
            f"Ficheiro de origem nao encontrado em: {origem}. "
            "Por favor, coloque o ficheiro CSV descarregado do TabNet nesse caminho."
        )

    # Garante a criação da pasta de destino
    BRONZE_SIH.mkdir(parents=True, exist_ok=True)

    # Formata a data atual no padrao AAAAMMDD
    hoje = date.today().strftime("%Y%m%d")
    destino = BRONZE_SIH / f"internacoes_{hoje}.csv"

    # Copia o ficheiro sem alterar o seu conteúdo
    shutil.copy(origem, destino)
    print(f"[SIH/SUS] Ficheiro copiado para: {destino}")
    return destino


def registrar_proveniencia(origem: Path, destino: Path) -> None:
    """Regista as informações de rastreabilidade no ficheiro proveniencia.jsonl."""
    info = {
        "fonte": "SIH/SUS (TabNet - DataSUS)",
        "url_origem": FONTE_URL,
        "ficheiro_origem": origem.name,
        "ficheiro_bronze": destino.name,
        "extraido_em": datetime.now().isoformat(),
        "descricao": "Internações por doenças respiratórias em Itajubá/MG",
    }

    caminho_prov = BRONZE_SIH / "proveniencia.jsonl"

    # Escreve acrescentando uma nova linha (modo 'a') para preservar histórico
    with caminho_prov.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")

    print(f"[SIH/SUS] Proveniencia registrada em: {caminho_prov}")


def main() -> None:
    """Função principal do fluxo de ingestão do SIH/SUS."""
    destino = copiar_para_bronze(CAMINHO_ORIGEM)
    registrar_proveniencia(CAMINHO_ORIGEM, destino)


if __name__ == "__main__":
    main()