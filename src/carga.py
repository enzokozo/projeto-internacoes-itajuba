"""
Carga: Prata (Parquet) -> banco DuckDB, e conferencia da camada Ouro.

O QUE ESTE SCRIPT FAZ
=====================
1. Abre (ou cria) o banco dados/ouro/projeto.duckdb.
2. Copia as tabelas da Prata para o esquema prata, como estao.
3. (aula 10) A Ouro NAO e mais construida aqui: quem cria as tabelas
   e o dbt, na etapa modelagem (pasta ecox14/). As funcoes antigas
   construir_* ficam no arquivo, comentadas no main, para comparar.
4. (aula 11) As conferencias da Ouro viraram testes do dbt
   (ecox14/models/schema.yml e ecox14/tests/), rodados com dbt test.
   Aqui sobra registrar_ouro(), que escreve no log o tamanho de cada
   tabela e os meses que ficaram fora, e grava uma linha em
   dados/ouro/proveniencia.jsonl: com qual Prata, qual codigo e qual
   dbt a Ouro foi construida, e se passou nos testes. Ver o passo 7.

O MODELO (esquema estrela)
==========================
    dim_mes            uma linha por mes (120 meses, 2010-01 a 2019-12)
    dim_faixa_etaria   uma linha por faixa etaria do TabNet (12 faixas)

    fato_internacoes   uma linha por mes e faixa etaria
    fato_clima_mensal  uma linha por mes

    vw_clima_internacoes_mensal
                       view: uma linha por mes, clima e internacoes lado
                       a lado. E a tabela que responde a pergunta norteadora.

As duas fatos usam a MESMA dim_mes. E isso que permite colocar clima e
internacoes lado a lado sem repetir valor nenhum.

O QUE PODE SER SOMADO
=====================
    fato_internacoes.internacoes   pode ser somada entre faixas e entre meses.
    fato_clima_mensal.*            sao medias e maximos do mes: NAO se somam.
                                   (a excecao e precipitacao_mm, que e soma do mes)

Como executar, a partir da raiz do projeto:
    python src/pipeline.py carga      carga + dbt run + dbt test
    python src/carga.py               so a carga da Prata (sem Ouro)
"""

import json
import logging
import subprocess
from datetime import datetime

import duckdb

from config import (OURO, PRATA, PRATA_CLIMA_INTERNACOES, PRATA_NASA,
                    PRATA_SIH, RAIZ)

log = logging.getLogger(__name__)

BANCO = OURO / "projeto.duckdb"
PROVENIENCIA_OURO = OURO / "proveniencia.jsonl"
RESULTADOS_DBT = RAIZ / "ecox14" / "target" / "run_results.json"

# Arquivos da Prata que os modelos dbt realmente leem (os source() dos
# .sql em ecox14/models/). A nasa_power esta no sources.yml, mas nenhum
# modelo a usa: o clima chega a Ouro pela clima_internacoes.
ORIGENS_OURO = [PRATA_SIH.name, PRATA_CLIMA_INTERNACOES.name]

# Tabelas da Prata que entram no banco como estao.
# Todas sao obrigatorias: sem qualquer uma delas a Ouro nao fecha.
TABELAS_PRATA = {
    "sih_sus": PRATA_SIH,
    "nasa_power": PRATA_NASA,
    "clima_internacoes": PRATA_CLIMA_INTERNACOES,
}


def um_valor(con, sql):
    return con.execute(sql).fetchone()[0]


def contar(con, tabela):
    return um_valor(con, f"SELECT COUNT(*) FROM {tabela}")


# ------------------------------------------------------------ passo 2
def conectar():
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    log.info("banco: %s", BANCO)
    return duckdb.connect(str(BANCO))


def criar_esquemas(con):
    con.execute("CREATE SCHEMA IF NOT EXISTS prata")
    con.execute("CREATE SCHEMA IF NOT EXISTS ouro")
    log.info("esquemas prata e ouro prontos")


# ------------------------------------------------------------ passo 3
def carregar_prata(con):
    faltando = [str(c) for c in TABELAS_PRATA.values() if not c.exists()]
    if faltando:
        # Erro claro agora, em vez de "tabela nao existe" la na frente.
        raise FileNotFoundError(
            f"arquivos da Prata nao encontrados: {faltando}. "
            "Rode antes: python src/pipeline.py transformacao"
        )

    for tabela, caminho in TABELAS_PRATA.items():
        con.execute(f"""
            CREATE OR REPLACE TABLE prata.{tabela} AS
            SELECT * FROM read_parquet('{caminho.as_posix()}')
        """)
        log.info("prata.%s: %s linhas", tabela, contar(con, f"prata.{tabela}"))


# ------------------------------------------------------------ passo 4
def construir_dimensoes(con):
    # dim_mes: os meses que existem nas DUAS fontes.
    # O enriquecimento ja resolveu isso: no clima_internacoes, Total so
    # fica nulo no dia que nao achou mes no SIH/SUS. E o mesmo papel que
    # a coluna id tem no exemplo da aula.
    con.execute("""
        CREATE OR REPLACE TABLE ouro.dim_mes AS
        SELECT DISTINCT
            CAST(MES AS DATE) AS mes,
            year(MES)         AS ano,
            month(MES)        AS mes_num,
            CASE
                WHEN month(MES) IN (12, 1, 2) THEN 'verao'
                WHEN month(MES) IN (3, 4, 5)  THEN 'outono'
                WHEN month(MES) IN (6, 7, 8)  THEN 'inverno'
                ELSE 'primavera'
            END               AS estacao
        FROM prata.clima_internacoes
        WHERE Total IS NOT NULL
        ORDER BY mes
    """)
    log.info("ouro.dim_mes: %s linhas", contar(con, "ouro.dim_mes"))

    # dim_faixa_etaria: escrita a mao, porque a ordem e o grupo nao
    # existem na fonte. Se um nome aqui nao bater com o cabecalho do
    # TabNet, a conferencia de orfaos acusa.
    con.execute("""
        CREATE OR REPLACE TABLE ouro.dim_faixa_etaria AS
        SELECT * FROM (VALUES
            ( 1, 'Menor 1 ano',    'crianca'),
            ( 2, '1 a 4 anos',     'crianca'),
            ( 3, '5 a 9 anos',     'crianca'),
            ( 4, '10 a 14 anos',   'adolescente'),
            ( 5, '15 a 19 anos',   'adolescente'),
            ( 6, '20 a 29 anos',   'adulto'),
            ( 7, '30 a 39 anos',   'adulto'),
            ( 8, '40 a 49 anos',   'adulto'),
            ( 9, '50 a 59 anos',   'adulto'),
            (10, '60 a 69 anos',   'idoso'),
            (11, '70 a 79 anos',   'idoso'),
            (12, '80 anos e mais', 'idoso')
        ) AS t(ordem, faixa, grupo)
    """)
    log.info("ouro.dim_faixa_etaria: %s linhas",
             contar(con, "ouro.dim_faixa_etaria"))


# ------------------------------------------------------------ passo 5
def construir_fatos(con):
    # fato_internacoes: o SIH/SUS vem LARGO (uma coluna por faixa).
    # UNPIVOT o deixa LONGO (uma linha por mes e faixa). A coluna Total
    # fica de fora: ela e a soma das faixas e pode ser recalculada.
    con.execute("""
        CREATE OR REPLACE TABLE ouro.fato_internacoes AS
        WITH longo AS (
            UNPIVOT prata.sih_sus
            ON COLUMNS(* EXCLUDE (PERIODO, Total))
            INTO NAME faixa VALUE internacoes
        )
        SELECT
            CAST(PERIODO AS DATE) AS mes,
            faixa,
            internacoes
        FROM longo
        WHERE CAST(PERIODO AS DATE) IN (SELECT mes FROM ouro.dim_mes)
    """)
    log.info("ouro.fato_internacoes: %s linhas",
             contar(con, "ouro.fato_internacoes"))

    # Os meses do SIH/SUS sem clima (nov e dez/2009) ficam fora da fato.
    # Nao somem em silencio: vao para o log.
    meses_fora, internacoes_fora = con.execute("""
        SELECT COUNT(*), COALESCE(SUM(Total), 0)
        FROM prata.sih_sus
        WHERE CAST(PERIODO AS DATE) NOT IN (SELECT mes FROM ouro.dim_mes)
    """).fetchone()
    if meses_fora:
        log.warning("%s meses do SIH/SUS ficaram fora da fato (%s internacoes): "
                    "sem clima correspondente", meses_fora, internacoes_fora)

    # fato_clima_mensal: aqui o GROUP BY muda o grao de dia para mes.
    # E o resumo que o README deixou pendente para a Ouro.
    con.execute("""
        CREATE OR REPLACE TABLE ouro.fato_clima_mensal AS
        SELECT
            CAST(MES AS DATE)                   AS mes,
            ROUND(AVG(T2M), 2)                  AS temperatura_media,
            ROUND(MIN(T2M_MIN), 2)              AS temperatura_minima,
            ROUND(MAX(T2M_MAX), 2)              AS temperatura_maxima,
            ROUND(AVG(AMPLITUDE_TERMICA), 2)    AS amplitude_media,
            ROUND(MAX(AMPLITUDE_TERMICA), 2)    AS amplitude_maxima,
            ROUND(AVG(RH2M), 2)                 AS umidade_media,
            ROUND(SUM(PRECTOTCORR), 2)          AS precipitacao_mm,
            COUNT(*)                            AS dias
        FROM prata.clima_internacoes
        WHERE Total IS NOT NULL
        GROUP BY CAST(MES AS DATE)
    """)
    log.info("ouro.fato_clima_mensal: %s linhas",
             contar(con, "ouro.fato_clima_mensal"))


# ------------------------------------------------------------ passo 6
def construir_view(con):
    # A tabela que a analise usa: uma linha por mes. Nao guarda dado,
    # refaz os joins a cada consulta, entao nunca fica desatualizada.
    con.execute("""
        CREATE OR REPLACE VIEW ouro.vw_clima_internacoes_mensal AS
        WITH internacoes_mes AS (
            SELECT
                f.mes,
                SUM(f.internacoes)                                  AS internacoes_total,
                SUM(f.internacoes) FILTER (WHERE d.grupo = 'crianca')     AS internacoes_criancas,
                SUM(f.internacoes) FILTER (WHERE d.grupo = 'adolescente') AS internacoes_adolescentes,
                SUM(f.internacoes) FILTER (WHERE d.grupo = 'adulto')      AS internacoes_adultos,
                SUM(f.internacoes) FILTER (WHERE d.grupo = 'idoso')       AS internacoes_idosos
            FROM ouro.fato_internacoes f
            JOIN ouro.dim_faixa_etaria d USING (faixa)
            GROUP BY f.mes
        )
        SELECT
            m.mes, m.ano, m.mes_num, m.estacao,
            c.temperatura_media, c.temperatura_minima, c.temperatura_maxima,
            c.amplitude_media, c.amplitude_maxima,
            c.umidade_media, c.precipitacao_mm,
            i.internacoes_total, i.internacoes_criancas,
            i.internacoes_adolescentes, i.internacoes_adultos,
            i.internacoes_idosos
        FROM ouro.dim_mes m
        JOIN ouro.fato_clima_mensal c USING (mes)
        JOIN internacoes_mes i USING (mes)
        ORDER BY m.mes
    """)
    log.info("ouro.vw_clima_internacoes_mensal: criada")


# ------------------------------------------------------------ passo 7
# Aula 11: as conferencias que moravam aqui viraram testes do dbt.
# Cada uma passou a ser uma regra escrita que o dbt cobra sozinho e
# que PARA o pipeline quando falha, em vez de um numero no log.
#
#   conferencia antiga (carga.py)                 teste novo (ecox14/)
#   --------------------------------------------  -----------------------------------------
#   dim_mes com mes repetido                      schema.yml: unique em dim_mes.mes
#   dim_faixa_etaria com faixa repetida           schema.yml: unique em dim_faixa_etaria.faixa
#   fato_internacoes com par mes-faixa repetido   tests/grao_fato_internacoes.sql
#   fato_clima_mensal com mes repetido            schema.yml: unique em fato_clima_mensal.mes
#   fato_internacoes sem mes na dimensao          schema.yml: relationships -> dim_mes
#   fato_internacoes sem faixa na dimensao        schema.yml: relationships -> dim_faixa_etaria
#   fato_clima_mensal sem mes na dimensao         schema.yml: relationships -> dim_mes
#   linhas faltando na fato_internacoes           tests/fato_internacoes_completa.sql
#   diferenca entre a fato e o Total do SIH/SUS   tests/soma_bate_total_sih.sql (agora mes a mes)
#
# O que sobra aqui e so registro: quantas linhas cada tabela tem, o
# aviso dos meses que ficaram de fora e a proveniencia da Ouro. Isso
# nao e regra, e informacao.

def avisar_meses_fora(con):
    # Os meses do SIH/SUS sem clima (nov e dez/2009) ficam fora da Ouro
    # por decisao de projeto. Nao e erro, entao nao e teste; mas tambem
    # nao some em silencio: vai para o log e para a proveniencia.
    meses_fora, internacoes_fora = con.execute("""
        SELECT COUNT(*), COALESCE(SUM(Total), 0)
        FROM prata.sih_sus
        WHERE CAST(PERIODO AS DATE) NOT IN (SELECT mes FROM ouro.dim_mes)
    """).fetchone()
    if meses_fora:
        log.warning("%s meses do SIH/SUS ficaram fora da fato (%s internacoes): "
                    "sem clima correspondente", meses_fora, internacoes_fora)
    return {"meses": int(meses_fora), "internacoes": int(internacoes_fora)}


TABELAS_OURO = [
    "dim_mes",
    "dim_faixa_etaria",
    "fato_internacoes",
    "fato_clima_mensal",
    "vw_clima_internacoes_mensal",
]


def contar_ouro(con):
    # O dbt nao mostra contagem de linhas; o log e a proveniencia vem daqui.
    linhas = {}
    for tabela in TABELAS_OURO:
        linhas[tabela] = contar(con, f"ouro.{tabela}")
        log.info("ouro.%s: %s linhas", tabela, linhas[tabela])
    return linhas


def medir_ouro():
    """Conta as linhas da Ouro, o total de internacoes e os meses fora.

    Abre a propria conexao, em modo so leitura, porque o dbt ja
    terminou e soltou o arquivo.
    """
    con = duckdb.connect(str(BANCO), read_only=True)
    try:
        linhas = contar_ouro(con)
        fora = avisar_meses_fora(con)
        total = um_valor(con, "SELECT SUM(internacoes) FROM ouro.fato_internacoes")
        log.info("internacoes na Ouro: %s", total)
    finally:
        con.close()
    return linhas, int(total or 0), fora


# ---------------------------------------------------------- proveniencia
#
# Cada construcao da Ouro grava UMA linha em dados/ouro/proveniencia.jsonl,
# como a Bronze e a Prata ja fazem. A linha responde: com qual Prata, com
# qual codigo e com qual dbt este banco foi construido, e se passou nos
# testes. Assim a cadeia fecha:
#
#   Ouro -> Prata (proveniencia da prata) -> Bronze -> fonte
#
# Se alguem tomar uma decisao com um numero do painel, da para
# reconstruir como ele foi calculado.

def ultima_da_prata(arquivo_prata):
    """O registro mais recente de um arquivo na proveniencia da Prata."""
    caminho = PRATA / "proveniencia.jsonl"
    if not caminho.exists():
        return None
    ultimo = None
    with caminho.open(encoding="utf-8") as f:
        for linha in f:
            if not linha.strip():
                continue
            registro = json.loads(linha)
            if registro.get("arquivo_prata") == arquivo_prata:
                ultimo = registro
    if ultimo is None:
        return None
    # Transformacao tem "origem"; o enriquecimento tem esquerda e direita.
    origem = ultimo.get("origem") or [
        ultimo.get("origem_esquerda"), ultimo.get("origem_direita")
    ]
    return {
        "arquivo_prata": arquivo_prata,
        "origem": origem,
        "transformado_em": ultimo.get("transformado_em"),
    }


def resultado_dbt(comando):
    """Le o run_results.json do ultimo comando dbt.

    O dbt SOBRESCREVE esse arquivo a cada comando. Como o pipeline roda
    dbt run e logo depois dbt test, esta funcao precisa ser chamada
    entre os dois para o run, e depois do test para o test.
    Devolve None se o arquivo veio de outro comando.
    """
    if not RESULTADOS_DBT.exists():
        return None
    resultados = json.loads(RESULTADOS_DBT.read_text(encoding="utf-8"))
    veio_de = resultados.get("args", {}).get("which")
    if veio_de != comando:
        log.warning("run_results.json veio de 'dbt %s', e nao de 'dbt %s'",
                    veio_de, comando)
        return None

    meta = resultados["metadata"]
    # unique_id: "model.ecox14.dim_mes" ou
    # "test.ecox14.unique_dim_mes_mes.1a2b3c4d" (teste generico tem um
    # codigo no fim). O terceiro pedaco e sempre o nome.
    situacoes = [
        (r["unique_id"].split(".")[2], r["status"])
        for r in resultados.get("results", [])
    ]
    info = {
        "versao": meta.get("dbt_version"),
        "invocation_id": meta.get("invocation_id"),
        "concluido_em": meta.get("generated_at"),
    }
    if comando == "run":
        info["modelos"] = dict(situacoes)
    else:
        # 30 nomes de teste nao cabem bem numa linha; guarda a contagem
        # por situacao e o nome so dos que nao passaram. A contagem vem
        # da lista, e nao de um dicionario por nome, para dois testes
        # de nome parecido nao virarem um so.
        contagem = {}
        for _, situacao in situacoes:
            contagem[situacao] = contagem.get(situacao, 0) + 1
        info["testes"] = contagem
        info["nao_passaram"] = sorted(
            nome for nome, s in situacoes if s != "pass")
    return info


def versao_do_codigo():
    """Commit atual e se ha alteracao nao commitada no codigo da Ouro."""
    def git(*argumentos):
        return subprocess.run(
            ["git", *argumentos], cwd=RAIZ,
            capture_output=True, text=True, check=True,
        ).stdout.strip()

    try:
        return {
            "commit": git("rev-parse", "--short", "HEAD"),
            "alteracoes_nao_commitadas": bool(
                git("status", "--porcelain", "--", "src", "ecox14")
            ),
        }
    except (OSError, subprocess.CalledProcessError):
        # Sem git instalado, ou fora de um repositorio: registra nulo.
        return None


def registrar_ouro(dbt_run, dbt_test):
    """Grava uma linha em dados/ouro/proveniencia.jsonl.

    Roda mesmo quando os testes falham: uma Ouro reprovada tambem
    precisa ficar registrada. Quem para o pipeline e o pipeline.py,
    depois deste registro.
    """
    linhas, total, fora = medir_ouro()
    aprovada = bool(dbt_test) and not dbt_test["nao_passaram"]
    info = {
        "camada": "ouro",
        "banco": BANCO.name,
        "origens_prata": [ultima_da_prata(a) for a in ORIGENS_OURO],
        "dbt_run": dbt_run,
        "dbt_test": dbt_test,
        "aprovada_nos_testes": aprovada,
        "codigo": versao_do_codigo(),
        "linhas": linhas,
        "internacoes": total,
        "fora_da_ouro": fora,
        "construido_em": datetime.now().isoformat(timespec="seconds"),
    }
    OURO.mkdir(parents=True, exist_ok=True)
    with PROVENIENCIA_OURO.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")
    log.info("proveniencia: %s", PROVENIENCIA_OURO)
    return info


def main():
    con = conectar()
    try:
        criar_esquemas(con)
        carregar_prata(con)
        # Aula 10: agora e o dbt (pasta ecox14/, etapa modelagem).
        # Comentado, nao apagado, para comparar as duas formas.
        # construir_dimensoes(con)
        # construir_fatos(con)
        # construir_view(con)
        # conferir(con)   -> aula 11: virou dbt test (ver passo 7)
    finally:
        # Fechar aqui e obrigatorio: o dbt abre o mesmo arquivo em
        # seguida, e o DuckDB nao deixa dois programas escreverem nele.
        con.close()
    log.info("carga concluida")


if __name__ == "__main__":
    import config

    config.configurar_log()
    main()
