"""
Painel do projeto: clima e internacoes respiratorias em Itajuba/MG.

Este arquivo so tem TELA. Todo SQL esta em consultas.py, e toda
transformacao ja aconteceu no pipeline. O painel le a camada Ouro e
nao escreve nada: e consumidor, por isso fica fora de src/.

Como executar, a partir da raiz do projeto (depois do pipeline):
    streamlit run dashboard/painel.py

Ele abre o navegador sozinho. Para parar, Ctrl+C no terminal.
"""

import math

import streamlit as st

import consultas

st.set_page_config(
    page_title="Clima e internações em Itajubá",
    page_icon="🫁",
    layout="wide",
)

# Nomes que aparecem na tela. Formatacao e assunto de apresentacao,
# por isso mora aqui e nao no modulo de consultas.
ROTULO_GRUPO = {
    consultas.TODOS: "Todas as idades",
    "crianca": "Crianças (0 a 9 anos)",
    "adolescente": "Adolescentes (10 a 19 anos)",
    "adulto": "Adultos (20 a 59 anos)",
    "idoso": "Idosos (60 anos ou mais)",
}
AZUL = "#1B3A5F"
LARANJA = "#D96F2C"


def br(valor, casas=1):
    """Numero no padrao brasileiro, com virgula decimal.

    Trata None e tambem NaN: o DuckDB devolve nulo como NaN no
    DataFrame, e sem esse cuidado a tela mostraria "nan".
    """
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "sem dado"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")


def vazio(valor):
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


# ------------------------------------------------------------ abertura
st.title("Clima e internações respiratórias em Itajubá/MG")
st.caption(
    "Pergunta norteadora: a amplitude térmica do mês está mais ligada às "
    "internações por doenças respiratórias do que a queda da temperatura "
    "média?"
)

if not consultas.banco_existe():
    st.error(
        "Banco não encontrado.\n\n"
        "Rode o pipeline antes:  python src/pipeline.py"
    )
    st.stop()

# ------------------------------------------------------------- filtros
with st.sidebar:
    st.header("Filtros")
    lista_anos = [int(a) for a in consultas.anos()["ano"]]
    ano_ini, ano_fim = st.select_slider(
        "Período",
        options=lista_anos,
        value=(lista_anos[0], lista_anos[-1]),
    )
    grupo = st.selectbox(
        "Grupo etário",
        [consultas.TODOS] + consultas.grupos_etarios()["grupo"].tolist(),
        format_func=lambda g: ROTULO_GRUPO.get(g, g),
    )
    st.divider()
    st.caption(
        "Os filtros entram na consulta como parâmetro, e não como texto "
        "concatenado."
    )

dados = consultas.serie_mensal(ano_ini, ano_fim, grupo)

if dados.empty:
    st.warning("Nenhum registro para esse filtro.")
    st.stop()

recorte = f"{ROTULO_GRUPO.get(grupo, grupo).lower()}, {ano_ini} a {ano_fim}"

# -------------------------------------------------------- cartoes
resumo = consultas.resumo(ano_ini, ano_fim, grupo).iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Internações no período", br(resumo["internacoes"], 0))
c2.metric(
    "Média por mês",
    br(resumo["media_mensal"], 1),
    help=f"Média de {br(resumo['meses'], 0)} meses.",
)
c3.metric(
    "Correlação com a amplitude",
    br(resumo["corr_amplitude"], 2),
    help="Correlação de Pearson (-1 a 1) entre a amplitude térmica média "
         "do mês e as internações do mês. Esperado: positiva.",
)
c4.metric(
    "Correlação com a temperatura média",
    br(resumo["corr_temperatura"], 2),
    help="Correlação de Pearson (-1 a 1) entre a temperatura média do mês "
         "e as internações do mês. Esperado: negativa (mais frio, mais "
         "internação).",
)

# Leitura da comparacao. A conta veio do banco; aqui so se escolhe a
# frase. Compara a FORCA (valor absoluto), porque os sinais esperados
# sao opostos.
r_amp, r_temp = resumo["corr_amplitude"], resumo["corr_temperatura"]
if not (vazio(r_amp) or vazio(r_temp)):
    if abs(r_amp) > abs(r_temp):
        mais_forte = "a **amplitude térmica**"
    else:
        mais_forte = "a **temperatura média**"
    st.info(
        f"Neste recorte ({recorte}), {mais_forte} acompanha mais de perto "
        f"as internações: |r| = {br(abs(r_amp), 2)} para a amplitude e "
        f"{br(abs(r_temp), 2)} para a temperatura média.\n\n"
        "Correlação não é causa: amplitude e temperatura mudam juntas com a "
        "estação do ano, e a estação também afeta as internações por outros "
        "caminhos (vírus sazonais, umidade, ambientes fechados)."
    )

st.divider()

# ------------------------------------------------- ao longo do tempo
st.subheader("Mês a mês")
esq, dir_ = st.columns(2)

with esq:
    st.markdown(f"**Internações** ({recorte})")
    st.line_chart(
        dados, x="mes", y="internacoes", color=AZUL, height=280,
        x_label="", y_label="internações no mês",
    )

with dir_:
    st.markdown("**Temperatura média e amplitude térmica** (°C)")
    clima = dados.rename(columns={
        "temperatura_media": "Temperatura média",
        "amplitude_media": "Amplitude média",
    })
    st.line_chart(
        clima, x="mes", y=["Temperatura média", "Amplitude média"],
        color=[AZUL, LARANJA], height=280,
        x_label="", y_label="°C",
    )

st.divider()

# ------------------------------------------- a pergunta norteadora
st.subheader("Cada ponto é um mês")
st.caption(
    "Se a nuvem de pontos sobe da esquerda para a direita, as duas coisas "
    "aumentam juntas. Quanto mais a nuvem parece uma linha, mais forte a "
    "relação."
)
esq, dir_ = st.columns(2)

with esq:
    st.markdown("**Amplitude térmica média × internações**")
    st.scatter_chart(
        dados, x="amplitude_media", y="internacoes", color="estacao",
        height=320, x_label="amplitude média do mês (°C)",
        y_label="internações no mês",
    )

with dir_:
    st.markdown("**Temperatura média × internações**")
    st.scatter_chart(
        dados, x="temperatura_media", y="internacoes", color="estacao",
        height=320, x_label="temperatura média do mês (°C)",
        y_label="internações no mês",
    )

st.divider()

# ------------------------------------------------------- por estacao
st.subheader("Média por estação do ano")
estacoes = consultas.media_por_estacao(ano_ini, ano_fim, grupo)
st.dataframe(
    estacoes,
    hide_index=True,
    column_config={
        "estacao": st.column_config.TextColumn("Estação"),
        "internacoes_media": st.column_config.ProgressColumn(
            "Internações por mês",
            format="%.1f",
            min_value=0,
            max_value=float(estacoes["internacoes_media"].max()),
        ),
        "temperatura_media": st.column_config.NumberColumn(
            "Temperatura média (°C)", format="%.1f"),
        "amplitude_media": st.column_config.NumberColumn(
            "Amplitude média (°C)", format="%.1f"),
    },
)

st.divider()

# ---------------------------------------------------------- tabela
st.subheader("Detalhe mês a mês")
st.dataframe(
    dados,
    hide_index=True,
    column_config={
        "mes": st.column_config.DateColumn("Mês", format="MM/YYYY"),
        "ano": None,       # None esconde a coluna: o mes ja diz o ano
        "mes_num": None,
        "estacao": st.column_config.TextColumn("Estação"),
        "internacoes": st.column_config.NumberColumn("Internações", format="%d"),
        "temperatura_media": st.column_config.NumberColumn("Temp. média (°C)", format="%.1f"),
        "temperatura_minima": st.column_config.NumberColumn("Temp. mínima (°C)", format="%.1f"),
        "temperatura_maxima": st.column_config.NumberColumn("Temp. máxima (°C)", format="%.1f"),
        "amplitude_media": st.column_config.NumberColumn(
            "Amplitude média (°C)", format="%.1f",
            help="Média, no mês, da diferença entre a máxima e a mínima de cada dia.",
        ),
        "amplitude_maxima": st.column_config.NumberColumn("Amplitude máxima (°C)", format="%.1f"),
        "umidade_media": st.column_config.NumberColumn("Umidade (%)", format="%.0f"),
        "precipitacao_mm": st.column_config.NumberColumn("Chuva (mm)", format="%.0f"),
    },
)

# Todo numero apresentado a alguem deveria dizer de onde veio.
st.caption(
    f"Fontes: SIH/SUS (TabNet/DataSUS), internações por doenças "
    f"respiratórias em Itajubá/MG; NASA POWER, clima diário na coordenada "
    f"da cidade (média de uma grade de cerca de 50 × 60 km, não uma "
    f"estação local). {len(dados)} meses nesta seleção. Dados públicos e "
    f"agregados, sem identificação de pacientes. Tratados e modelados pelo "
    f"pipeline do projeto (Bronze → Prata → Ouro, testes no dbt)."
)
