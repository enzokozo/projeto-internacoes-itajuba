"""
Ponto de entrada do pipeline.

ISTO NAO E ORQUESTRACAO
=======================
Orquestrador de verdade (Airflow, Prefect, Dagster) agenda
sozinho, entende dependencia em grafo, tenta de novo quando
falha, avisa alguem, roda etapas em paralelo e reprocessa periodo
passado.

Este arquivo nao faz nada disso. Ele e um ponto de entrada: roda
as etapas na ordem certa, registra o que aconteceu e para quando
quebra. Sao poucas linhas de Python puro, sem biblioteca
nenhuma, e e suficiente para o projeto da disciplina.

Saber exatamente o que falta aqui e o que permite decidir, mais
tarde, se vale a pena adotar um orquestrador.

COMO EXECUTAR, a partir da raiz do projeto
==========================================
    python src/pipeline.py                  roda tudo
    python src/pipeline.py enriquecimento   retoma do meio
    python src/pipeline.py modelagem        so refaz a Ouro (dbt run) e testa (dbt test)

O painel (dashboard/) fica fora do pipeline: ele so le a Ouro.
    streamlit run dashboard/painel.py

Antes, coloque sih_sus_raw.csv e nasa_raw.csv na pasta dados/.

A retomada existe por um motivo pratico: quando o erro esta na
ultima etapa, voce nao quer refazer a primeira (e criar mais uma
copia datada na Bronze sem necessidade).

O explorar.py (relatorios de qualidade) fica fora de proposito:
e opcional e lento. Rode a parte quando precisar:
    python src/explorar.py
"""

import logging
import sys
import time

import config



def etapa_ingestao():
    import ingerir_sih
    import ingerir_nasa

    ingerir_sih.main()
    ingerir_nasa.main()


def etapa_transformacao():
    import transformar_sih
    import transformar_nasa

    transformar_sih.main()
    transformar_nasa.main()


def etapa_enriquecimento():
    import enriquecer

    enriquecer.main()

def etapa_carga():
    import carga

    carga.main()


def etapa_modelagem():
    # Aula 10: a Ouro e construida pelo dbt, a partir dos SELECT em
    # ecox14/models/. O dbt descobre sozinho a ordem pelos ref().
    import shutil
    import subprocess

    import carga

    if shutil.which("dbt") is None:
        raise RuntimeError(
            "comando dbt nao encontrado. Ative o ambiente virtual e rode: "
            "pip install dbt-core dbt-duckdb"
        )

    pasta_dbt = config.RAIZ / "ecox14"

    # check=True: se o dbt run falhar, o Python levanta erro e o
    # pipeline para. Sem ele, o log diria "concluido" com a Ouro quebrada.
    subprocess.run(["dbt", "run"], cwd=pasta_dbt, check=True)

    # Ler o resultado do run AGORA: o dbt test logo abaixo sobrescreve
    # o run_results.json que a proveniencia usa.
    dbt_run = carga.resultado_dbt("run")

    # Aula 11: as conferencias viraram testes (ecox14/models/schema.yml
    # e ecox14/tests/). Aqui SEM check=True, de proposito: primeiro a
    # proveniencia registra o resultado, aprovado ou nao; depois o
    # pipeline para se algum teste falhou.
    # Para ver as linhas que falharam:
    #   cd ecox14
    #   dbt test --select NOME_DO_TESTE --store-failures
    testes = subprocess.run(["dbt", "test"], cwd=pasta_dbt)
    dbt_test = carga.resultado_dbt("test")

    # Uma linha em dados/ouro/proveniencia.jsonl, como Bronze e Prata.
    carga.registrar_ouro(dbt_run, dbt_test)

    if testes.returncode != 0:
        raise RuntimeError(
            "dbt test falhou; a Ouro foi registrada como reprovada em "
            "dados/ouro/proveniencia.jsonl. Veja acima quais testes falharam."
        )


ETAPAS = [
    ("ingestao", etapa_ingestao),
    ("transformacao", etapa_transformacao),
    ("enriquecimento", etapa_enriquecimento),
    ("carga", etapa_carga),
    ("modelagem", etapa_modelagem),   # aula 10: era None
]

log = logging.getLogger(__name__)


def executar(nome, funcao):

    log.info("etapa %s: inicio", nome)
    comeco = time.perf_counter()
    try:
        funcao()
    except Exception:
        log.exception("etapa %s falhou", nome)
        raise
    duracao = time.perf_counter() - comeco
    log.info("etapa %s: fim em %.0fs", nome, duracao)


def main(a_partir_de=None):
    config.configurar_log()
    config.criar_pastas()

    nomes = [nome for nome, _ in ETAPAS]
    if a_partir_de and a_partir_de not in nomes:
        log.error("etapa desconhecida: %s", a_partir_de)
        log.error("etapas validas: %s", ", ".join(nomes))
        return 1

    comecou = a_partir_de is None
    for nome, funcao in ETAPAS:
        if nome == a_partir_de:
            comecou = True
        if not comecou:
            log.info("etapa %s: pulada", nome)
            continue
        if funcao is None:
            log.warning("etapa %s: ainda nao implementada", nome)
            continue
        executar(nome, funcao)

    log.info("pipeline concluido")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
