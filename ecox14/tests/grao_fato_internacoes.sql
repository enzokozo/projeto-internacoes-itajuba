-- Grao da fato_internacoes: uma linha por mes e faixa etaria.
-- Era a conferencia "fato_internacoes com par mes-faixa repetido" do
-- carga.py. Nao existe teste pronto para chave composta, por isso
-- este arquivo.
-- Passa quando devolve ZERO linhas.

select mes, faixa, count(*) as linhas
from {{ ref('fato_internacoes') }}
group by mes, faixa
having count(*) > 1
