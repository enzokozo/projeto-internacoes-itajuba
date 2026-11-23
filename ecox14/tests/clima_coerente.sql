-- O resumo mensal do clima faz sentido fisico?
-- O codigo pode estar certo e a fonte mandar um -999 que escapou, ou
-- um mes com dias faltando. Cada condicao abaixo e um defeito; a
-- coluna "problema" diz qual foi encontrado.
-- Passa quando devolve ZERO linhas.

select mes, 'minima maior que a media' as problema
from {{ ref('fato_clima_mensal') }}
where temperatura_minima > temperatura_media

union all
select mes, 'media maior que a maxima'
from {{ ref('fato_clima_mensal') }}
where temperatura_media > temperatura_maxima

union all
select mes, 'amplitude media maior que a maxima'
from {{ ref('fato_clima_mensal') }}
where amplitude_media > amplitude_maxima

union all
select mes, 'amplitude negativa'
from {{ ref('fato_clima_mensal') }}
where amplitude_media < 0

union all
select mes, 'umidade fora de 0 a 100'
from {{ ref('fato_clima_mensal') }}
where umidade_media not between 0 and 100

union all
select mes, 'precipitacao negativa'
from {{ ref('fato_clima_mensal') }}
where precipitacao_mm < 0

union all
-- mes com menos dias que o calendario: faltou dado da NASA
select mes, 'dias incompletos: ' || cast(dias as varchar)
from {{ ref('fato_clima_mensal') }}
where dias <> day(last_day(mes))
