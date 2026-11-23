-- fato_clima_mensal: uma linha por mes (120).
-- O GROUP BY muda o grao de dia para mes. Temperatura, amplitude e
-- umidade sao medias, minimos e maximos do mes e NAO se somam entre
-- meses; a precipitacao e a soma do mes.

select
    cast(MES as date)                   as mes,
    round(avg(T2M), 2)                  as temperatura_media,
    round(min(T2M_MIN), 2)              as temperatura_minima,
    round(max(T2M_MAX), 2)              as temperatura_maxima,
    round(avg(AMPLITUDE_TERMICA), 2)    as amplitude_media,
    round(max(AMPLITUDE_TERMICA), 2)    as amplitude_maxima,
    round(avg(RH2M), 2)                 as umidade_media,
    round(sum(PRECTOTCORR), 2)          as precipitacao_mm,
    count(*)                            as dias
from {{ source('prata', 'clima_internacoes') }}
where Total is not null
group by cast(MES as date)
