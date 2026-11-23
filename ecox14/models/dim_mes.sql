-- dim_mes: uma linha por mes que existe nas DUAS fontes (120 meses).
-- No clima_internacoes, Total so fica nulo no dia que nao achou mes no
-- SIH/SUS. O enriquecimento ja resolveu isso e aqui nao e refeito.

select distinct
    cast(MES as date) as mes,
    year(MES)         as ano,
    month(MES)        as mes_num,
    case
        when month(MES) in (12, 1, 2) then 'verao'
        when month(MES) in (3, 4, 5)  then 'outono'
        when month(MES) in (6, 7, 8)  then 'inverno'
        else 'primavera'
    end               as estacao
from {{ source('prata', 'clima_internacoes') }}
where Total is not null
order by mes
