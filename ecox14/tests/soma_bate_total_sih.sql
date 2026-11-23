-- A soma das faixas na Ouro bate com o Total que o TabNet entregou?
-- Era a conferencia "diferenca entre a fato e o Total do SIH/SUS" do
-- carga.py. Antes ela comparava o total geral; agora compara mes a
-- mes, entao um erro de +5 num mes e -5 em outro nao se cancela.
-- Passa quando devolve ZERO linhas.

with ouro as (
    select mes, sum(internacoes) as soma_faixas
    from {{ ref('fato_internacoes') }}
    group by mes
),

prata as (
    select cast(PERIODO as date) as mes, Total as total_tabnet
    from {{ source('prata', 'sih_sus') }}
)

select o.mes, o.soma_faixas, p.total_tabnet
from ouro o
left join prata p using (mes)
where p.total_tabnet is null
   or o.soma_faixas <> p.total_tabnet
