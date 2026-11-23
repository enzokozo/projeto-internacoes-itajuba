-- fato_internacoes: uma linha por mes e faixa etaria (120 x 12 = 1.440).
-- O SIH/SUS vem LARGO (uma coluna por faixa); o UNPIVOT o deixa LONGO.
-- A coluna Total fica de fora: e a soma das faixas e pode ser recalculada.
--
-- O ref('dim_mes') faz duas coisas: filtra os meses sem clima
-- (nov e dez/2009) e avisa o dbt que esta fato depende da dim_mes,
-- entao a dim_mes roda antes.

with longo as (
    unpivot {{ source('prata', 'sih_sus') }}
    on columns(* exclude (PERIODO, Total))
    into name faixa value internacoes
)

select
    cast(PERIODO as date) as mes,
    faixa,
    internacoes
from longo
where cast(PERIODO as date) in (select mes from {{ ref('dim_mes') }})
