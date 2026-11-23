-- Contagem de internacao nao pode ser negativa.
-- Se aparecer, o "-" do TabNet foi convertido errado na Prata (por
-- exemplo, virou sinal em vez de zero).
-- Passa quando devolve ZERO linhas.

select mes, faixa, internacoes
from {{ ref('fato_internacoes') }}
where internacoes < 0
