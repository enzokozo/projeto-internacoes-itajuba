-- A view junta dim_mes, fato_clima_mensal e as internacoes com JOIN
-- (inner). Se um mes faltar em qualquer lado, ele some da view sem
-- aviso nenhum. Este teste devolve os meses da dimensao que nao
-- chegaram na view.
-- Passa quando devolve ZERO linhas.

select m.mes
from {{ ref('dim_mes') }} m
left join {{ ref('vw_clima_internacoes_mensal') }} v using (mes)
where v.mes is null
