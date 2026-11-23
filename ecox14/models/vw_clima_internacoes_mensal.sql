{{ config(materialized='view') }}

-- A tabela que a analise usa: uma linha por mes, clima e internacoes
-- lado a lado. E view: nao guarda dado e refaz os joins a cada consulta.
-- So este modelo depende de outros modelos (todos via ref), por isso
-- o dbt o executa por ultimo.

with internacoes_mes as (
    select
        f.mes,
        sum(f.internacoes)                                        as internacoes_total,
        sum(f.internacoes) filter (where d.grupo = 'crianca')     as internacoes_criancas,
        sum(f.internacoes) filter (where d.grupo = 'adolescente') as internacoes_adolescentes,
        sum(f.internacoes) filter (where d.grupo = 'adulto')      as internacoes_adultos,
        sum(f.internacoes) filter (where d.grupo = 'idoso')       as internacoes_idosos
    from {{ ref('fato_internacoes') }} f
    join {{ ref('dim_faixa_etaria') }} d using (faixa)
    group by f.mes
)

select
    m.mes, m.ano, m.mes_num, m.estacao,
    c.temperatura_media, c.temperatura_minima, c.temperatura_maxima,
    c.amplitude_media, c.amplitude_maxima,
    c.umidade_media, c.precipitacao_mm,
    i.internacoes_total, i.internacoes_criancas,
    i.internacoes_adolescentes, i.internacoes_adultos,
    i.internacoes_idosos
from {{ ref('dim_mes') }} m
join {{ ref('fato_clima_mensal') }} c using (mes)
join internacoes_mes i using (mes)
order by m.mes
