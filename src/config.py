"""
Configuracao central do projeto.

O QUE ENTRA AQUI
================
    caminhos de pasta e arquivo
    parametros que voce ajusta e reexecuta (local, periodo)
    a ordem das camadas

O QUE NAO ENTRA
===============
    logica de transformacao
    qualquer coisa que mude a cada execucao
    segredo: senha, token, chave de API

Segredo nunca vem para ca, porque este arquivo vai para o GitHub.
Token e senha ficam em variavel de ambiente ou em arquivo
ignorado.

O TESTE
=======
Se alguem for rodar o seu projeto em outra maquina, ou com outra
cidade, quais linhas essa pessoa precisa editar? Essas linhas
pertencem a este arquivo.
"""

import logging
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent

DADOS = RAIZ / "dados"
BRONZE = DADOS / "bronze"
PRATA = DADOS / "prata"
OURO = DADOS / "ouro"
RELATORIOS = RAIZ / "relatorios"

# Entradas: CSVs baixados manualmente do TabNet e do NASA POWER.
ORIGEM_SIH = DADOS / "sih_sus_raw.csv"
ORIGEM_NASA = DADOS / "nasa_raw.csv"

# Bronze: uma pasta por fonte.
BRONZE_SIH = BRONZE / "sih_sus"
BRONZE_NASA = BRONZE / "nasa_power"

# Prata: uma tabela por arquivo.
PRATA_SIH = PRATA / "sih_sus.parquet"
PRATA_NASA = PRATA / "nasa_power.parquet"
PRATA_CLIMA_INTERNACOES = PRATA / "clima_internacoes.parquet"

# ---------------------------------------------------------- parametros
MUNICIPIO = "Itajuba/MG"

URL_SIH = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nimg.def"
URL_NASA = "https://power.larc.nasa.gov/"

# Coordenada usada na consulta ao NASA POWER.
LATITUDE = -22.4266
LONGITUDE = -45.4587

# Periodo em comum entre as duas fontes.
PERIODO_INICIO = "2010-01"
PERIODO_FIM = "2019-12"

# ------------------------------------------------------------- logging
ARQUIVO_LOG = RAIZ / "pipeline.log"


def configurar_log(nivel=logging.INFO):

    logging.basicConfig(
        level=nivel,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(ARQUIVO_LOG, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def criar_pastas():
    for pasta in (BRONZE_SIH, BRONZE_NASA, PRATA, OURO, RELATORIOS):
        pasta.mkdir(parents=True, exist_ok=True)
