-- Todo mes da dim_mes tem as 12 faixas na fato_internacoes?
-- Era a conferencia "linhas faltando na fato_internacoes" do carga.py,
-- agora mais util: em vez de um numero, devolve QUAIS meses estao
-- incompletos e quantas faixas cada um tem.
-- Passa quando devolve ZERO linhas.

with faixas_por_mes as (
    select m.mes, count(f.faixa) as faixas
    from {{ ref('dim_mes') }} m
    left join {{ ref('fato_internacoes') }} f using (mes)
    group by m.mes
)

select mes, faixas
from faixas_por_mes
where faixas <> (select count(*) from {{ ref('dim_faixa_etaria') }})
