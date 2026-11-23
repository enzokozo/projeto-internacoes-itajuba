"""
Carga: Prata (Parquet) -> banco DuckDB, e construcao da camada Ouro.

O QUE ESTE SCRIPT FAZ
=====================
1. Abre (ou cria) o banco dados/ouro/projeto.duckdb.
2. Copia as tabelas da Prata para o esquema prata, como estao.
3. Constroi o esquema estrela no esquema ouro, em SQL.
4. Confere o modelo e PARA o pipeline se algo nao bater.

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
    python src/carga.py
ou, pelo pipeline:
    python src/pipeline.py carga
"""

import logging

import duckdb

from config import OURO, PRATA_CLIMA_INTERNACOES, PRATA_NASA, PRATA_SIH

log = logging.getLogger(__name__)

BANCO = OURO / "projeto.duckdb"

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
# Cada conferencia e uma consulta que precisa devolver 0.
CONFERENCIAS = {
    # o grao se confirma?
    "dim_mes com mes repetido": """
        SELECT COUNT(*) FROM (
            SELECT mes FROM ouro.dim_mes GROUP BY mes HAVING COUNT(*) > 1)
    """,
    "dim_faixa_etaria com faixa repetida": """
        SELECT COUNT(*) FROM (
            SELECT faixa FROM ouro.dim_faixa_etaria
            GROUP BY faixa HAVING COUNT(*) > 1)
    """,
    "fato_internacoes com par mes-faixa repetido": """
        SELECT COUNT(*) FROM (
            SELECT mes, faixa FROM ouro.fato_internacoes
            GROUP BY mes, faixa HAVING COUNT(*) > 1)
    """,
    "fato_clima_mensal com mes repetido": """
        SELECT COUNT(*) FROM (
            SELECT mes FROM ouro.fato_clima_mensal
            GROUP BY mes HAVING COUNT(*) > 1)
    """,
    # sobrou fato sem dimensao?
    "fato_internacoes sem mes na dimensao": """
        SELECT COUNT(*) FROM ouro.fato_internacoes f
        LEFT JOIN ouro.dim_mes d USING (mes) WHERE d.mes IS NULL
    """,
    "fato_internacoes sem faixa na dimensao": """
        SELECT COUNT(*) FROM ouro.fato_internacoes f
        LEFT JOIN ouro.dim_faixa_etaria d USING (faixa) WHERE d.faixa IS NULL
    """,
    "fato_clima_mensal sem mes na dimensao": """
        SELECT COUNT(*) FROM ouro.fato_clima_mensal f
        LEFT JOIN ouro.dim_mes d USING (mes) WHERE d.mes IS NULL
    """,
    # todo mes tem as 12 faixas?
    "linhas faltando na fato_internacoes": """
        SELECT (SELECT COUNT(*) FROM ouro.dim_mes)
             * (SELECT COUNT(*) FROM ouro.dim_faixa_etaria)
             - (SELECT COUNT(*) FROM ouro.fato_internacoes)
    """,
    # a soma bate com o Total que o TabNet entregou?
    "diferenca entre a fato e o Total do SIH/SUS": """
        SELECT
            (SELECT SUM(Total) FROM prata.sih_sus
             WHERE CAST(PERIODO AS DATE) IN (SELECT mes FROM ouro.dim_mes))
          - (SELECT SUM(internacoes) FROM ouro.fato_internacoes)
    """,
}


def conferir(con):
    problemas = []
    for nome, sql in CONFERENCIAS.items():
        valor = um_valor(con, sql)
        log.info("%-45s: %s (esperado 0)", nome, valor)
        if valor:
            problemas.append(f"{nome}: {valor}")

    total = um_valor(con, "SELECT SUM(internacoes) FROM ouro.fato_internacoes")
    log.info("internacoes na Ouro: %s", total)

    if problemas:
        raise ValueError("modelo inconsistente: " + "; ".join(problemas))


def main():
    con = conectar()
    try:
        criar_esquemas(con)
        carregar_prata(con)
        construir_dimensoes(con)
        construir_fatos(con)
        construir_view(con)
        conferir(con)
    finally:
        con.close()
    log.info("carga concluida")


if __name__ == "__main__":
    import config

    config.configurar_log()
    main()
