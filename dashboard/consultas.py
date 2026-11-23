"""
Onde o SQL do painel fica.

POR QUE ESTE ARQUIVO EXISTE
===========================
SQL que CRIA tabela mora no dbt (ecox14/), versionado e testado.
SQL que so LE para mostrar mora aqui. E a tela (painel.py) nao tem
SQL nenhum.

A pergunta que separa os dois lugares: se alguem pedir esse mesmo
numero por e-mail, sem abrir o painel, a consulta existe em algum
lugar reaproveitavel? Com este modulo, sim:

    import consultas
    consultas.resumo(2010, 2019, "idoso")

Cada pergunta que o painel faz vira uma funcao com nome.

VALOR DA TELA ENTRA COMO PARAMETRO
==================================
Todo valor que vem de um filtro entra pelo "?" e pela lista de
parametros, nunca colado no texto do SQL com f-string. Assim o banco
nunca interpreta o valor como comando (injecao de SQL).
"""
from pathlib import Path

import duckdb
import streamlit as st

# Mesma ideia do config.py: o caminho vem deste arquivo, e nao da pasta
# de onde voce rodou o comando.
#   __file__        dashboard/consultas.py
#   .parent         dashboard/
#   .parent.parent  a raiz do projeto
RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "dados" / "ouro" / "projeto.duckdb"

# Valor do filtro de grupo etario que significa "todas as faixas".
# Precisa ser igual ao 'todos' escrito em _INTERNACOES_DO_GRUPO.
TODOS = "todos"


def banco_existe():
    """Para o painel avisar em vez de estourar erro de conexao."""
    return BANCO.exists()


# O cache evita refazer a consulta a cada clique na tela.
# ttl=600: o resultado vale por 10 minutos. Sem isso, depois de rodar
# o pipeline de novo, o painel continuaria mostrando o dado antigo ate
# ser reiniciado.
# E a unica coisa daqui que depende do streamlit: sem o decorador, o
# modulo funciona igual em qualquer script Python.
@st.cache_data(ttl=600)
def _consultar(sql, parametros=None):
    """Roda uma consulta e devolve um DataFrame.

    read_only=True porque o painel so le. Sem isso ele trava o arquivo
    e o pipeline (dbt run) nao consegue escrever no banco.
    """
    con = duckdb.connect(str(BANCO), read_only=True)
    try:
        return con.execute(sql, parametros or []).df()
    finally:
        con.close()


# ----------------------------------------------------------- filtros

def anos():
    """Anos disponiveis na Ouro, do mais antigo para o mais recente."""
    return _consultar("""
        select distinct ano
        from ouro.dim_mes
        order by ano
    """)


def grupos_etarios():
    """Grupos etarios na ordem da idade (crianca, ..., idoso)."""
    return _consultar("""
        select grupo
        from ouro.dim_faixa_etaria
        group by grupo
        order by min(ordem)
    """)


# ---------------------------------------------------------- perguntas
#
# As tres perguntas abaixo usam o mesmo recorte: periodo (ano_ini a
# ano_fim) e grupo etario. O recorte por grupo e feito na fato, e nao
# escolhendo uma coluna da view, porque nome de coluna NAO pode ser
# parametro: so valor pode. Filtrando a fato pelo grupo, tudo continua
# entrando pelo "?".
#
#   where ? = 'todos' or d.grupo = ?
#
# O mesmo valor entra duas vezes: se for 'todos', a primeira condicao
# ja e verdadeira e nenhuma faixa e descartada.
#
# O f-string abaixo so encaixa este trecho FIXO de SQL, escrito aqui
# mesmo. Nenhum valor que vem da tela passa por ele.

_INTERNACOES_DO_GRUPO = """
    internacoes as (
        select f.mes, sum(f.internacoes) as internacoes
        from ouro.fato_internacoes f
        join ouro.dim_faixa_etaria d using (faixa)
        where ? = 'todos' or d.grupo = ?
        group by f.mes
    )
"""


def _parametros(ano_ini, ano_fim, grupo):
    # A ordem tem que ser a mesma dos "?" no SQL: primeiro os dois do
    # bloco de internacoes, depois os dois do periodo.
    return [grupo, grupo, int(ano_ini), int(ano_fim)]


def serie_mensal(ano_ini, ano_fim, grupo):
    """Clima e internacoes do grupo, mes a mes, no periodo.

    E a tabela de base do painel: os graficos de linha, os de dispersao
    e a tabela detalhada saem daqui.
    """
    return _consultar(
        f"""
        with {_INTERNACOES_DO_GRUPO}
        select
            v.mes, v.ano, v.mes_num, v.estacao,
            i.internacoes,
            v.temperatura_media, v.temperatura_minima, v.temperatura_maxima,
            v.amplitude_media, v.amplitude_maxima,
            v.umidade_media, v.precipitacao_mm
        from ouro.vw_clima_internacoes_mensal v
        join internacoes i using (mes)
        where v.ano between ? and ?
        order by v.mes
        """,
        _parametros(ano_ini, ano_fim, grupo),
    )


def resumo(ano_ini, ano_fim, grupo):
    """Numeros de cabecalho, para os cartoes do topo.

    As correlacoes sao calculadas pelo banco (corr), e nao no Python:
    a conta e uma pergunta sobre o dado, entao mora aqui.

    Correlacao de Pearson, de -1 a 1. Quanto mais longe de zero, mais
    as duas series andam juntas. Para a temperatura media, espera-se
    sinal NEGATIVO (mais frio, mais internacao); para a amplitude,
    POSITIVO. A pergunta norteadora compara a FORCA das duas, isto e,
    o valor absoluto.
    """
    return _consultar(
        f"""
        with {_INTERNACOES_DO_GRUPO}
        select
            count(*)                                   as meses,
            sum(i.internacoes)                         as internacoes,
            avg(i.internacoes)                         as media_mensal,
            corr(v.amplitude_media,   i.internacoes)   as corr_amplitude,
            corr(v.temperatura_media, i.internacoes)   as corr_temperatura
        from ouro.vw_clima_internacoes_mensal v
        join internacoes i using (mes)
        where v.ano between ? and ?
        """,
        _parametros(ano_ini, ano_fim, grupo),
    )


def media_por_estacao(ano_ini, ano_fim, grupo):
    """Media mensal de internacoes, temperatura e amplitude por estacao.

    Ordenada pelo calendario: verao (que contem janeiro) primeiro.
    """
    return _consultar(
        f"""
        with {_INTERNACOES_DO_GRUPO}
        select
            v.estacao,
            round(avg(i.internacoes), 1)        as internacoes_media,
            round(avg(v.temperatura_media), 1)  as temperatura_media,
            round(avg(v.amplitude_media), 1)    as amplitude_media
        from ouro.vw_clima_internacoes_mensal v
        join internacoes i using (mes)
        where v.ano between ? and ?
        group by v.estacao
        order by min(v.mes_num)
        """,
        _parametros(ano_ini, ano_fim, grupo),
    )
