-- dim_faixa_etaria: escrita a mao, porque a ordem e o grupo nao existem
-- na fonte. Nao le nenhuma tabela, entao nao usa source nem ref.
-- Se um nome aqui nao bater com o cabecalho do TabNet, a conferencia
-- de orfaos do carga.py acusa.

select *
from (values
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
) as t(ordem, faixa, grupo)
