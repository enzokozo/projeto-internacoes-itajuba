# Impacto da Amplitude Térmica e Temperaturas Médias nas Internações por Doenças Respiratórias em Itajubá, MG

## Identificação
- **Aluno:** Enzo Kozonoe
- **Matrícula:** 2022010384

## Pergunta Norteadora
A amplitude térmica extrema (a diferença acentuada entre os dias mais quentes e as noites mais frias de um mesmo mês) tem um impacto mais forte no aumento das internações do que a queda na temperatura média isolada?

## Fontes de Dados
| Fonte | Formato | Acesso | Chave de Ligação | Período | Link |
|---|---|---|---|---|---|
| SIH/SUS (TabNet / DataSUS) | CSV | Baixado | Mês/Ano | nov/2009 a dez/2019 (mensal) | http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nimg.def |
| NASA POWER | CSV | Baixado | Data (diária), agregada para Mês/Ano | 01/01/2010 a 31/12/2019 (diário) | https://power.larc.nasa.gov/ |

**Observações:**
- O SIH/SUS já vem filtrado para Itajubá/MG e traz as internações por mês e faixa etária.
- O NASA POWER foi consultado para a coordenada de Itajubá (latitude -22,4266 e longitude -45,4587). O valor é a média de uma grade de 0,5° × 0,625° (cerca de 50 × 60 km) em torno desse ponto, e não uma medição feita na cidade.
- O período em comum entre as fontes é de janeiro/2010 a dezembro/2019 (120 meses). Os dois meses de 2009 do SIH ficam fora do cruzamento.

## Estrutura do Repositório
O projeto segue a arquitetura em camadas (Bronze → Prata → Ouro).

```
projeto-internacoes-itajuba/
├── dados/
│   ├── sih_sus_raw.csv          # CSV baixado do TabNet (entrada)
│   ├── nasa_raw.csv             # CSV baixado do NASA POWER (entrada)
│   ├── bronze/
│   │   ├── sih_sus/             # cópia fiel do original, com data no nome + proveniencia.jsonl
│   │   └── nasa_power/          # cópia fiel do original, com data no nome + proveniencia.jsonl
│   ├── prata/
│   │   ├── sih_sus.parquet      # internações mensais tratadas
│   │   ├── nasa_power.parquet   # clima diário tratado
│   │   ├── clima_internacoes.parquet  # clima diário + internações do mês (enriquecimento)
│   │   └── proveniencia.jsonl   # decisões de cada transformação
│   └── ouro/                    # camada Ouro (ainda não implementada)
├── relatorios/                  # relatórios de qualidade (HTML) gerados pelo explorar.py
├── src/
│   ├── pipeline.py              # ponto de entrada: roda as etapas em ordem e permite retomar do meio
│   ├── config.py                # caminhos, parâmetros das fontes e configuração do log
│   ├── ingerir_sih.py           # ingestão do SIH/SUS (origem → Bronze)
│   ├── ingerir_nasa.py          # ingestão do NASA POWER (origem → Bronze)
│   ├── transformar_sih.py       # SIH/SUS: Bronze → Prata
│   ├── transformar_nasa.py      # NASA POWER: Bronze → Prata
│   ├── enriquecer.py            # junção NASA + SIH/SUS na Prata
│   ├── limpeza.py               # funções genéricas de limpeza (uma tabela por vez)
│   ├── juncao.py                # funções genéricas de junção (relação entre duas tabelas)
│   └── explorar.py              # opcional, fora do pipeline: relatórios de qualidade da Bronze
├── pipeline.log                 # registro das execuções (gerado, fora do Git)
├── requirements.txt
└── README.md
```

## Como Executar
Antes, coloque `sih_sus_raw.csv` e `nasa_raw.csv` na pasta `dados/`. Depois, a partir da raiz do repositório:

```
pip install -r requirements.txt

python src/pipeline.py                  # roda todas as etapas
python src/pipeline.py enriquecimento   # retoma a partir de uma etapa
python src/explorar.py                  # opcional: relatórios de qualidade da Bronze
```

Etapas, em ordem: `ingestao`, `transformacao`, `enriquecimento`, `carga` e `modelagem` (as duas últimas ainda não implementadas). O andamento aparece na tela e fica registrado em `pipeline.log`.

## Defeitos Conhecidos das Fontes (Diagnóstico Bronze)

### SIH/SUS (Internações)
- CSV com separador `;` (e não vírgula).
- Linhas que não são dados: total anual (ex.: `2010`), `Total` geral e uma linha de rodapé (`&`).
- Coluna de tempo em texto, com prefixo de pontos (ex.: `..Janeiro/2010`).
- Valores zero escritos como `-`, o que faz as colunas de contagem serem lidas como texto.

### NASA POWER (Meteorologia)
- Cabeçalho descritivo da NASA nas primeiras linhas antes dos dados reais (termina em `-END HEADER-`).
- Data dividida em colunas separadas (`YEAR` para Ano e `DOY` para Dia do Ano, ou `YEAR`, `MO`, `DY`).
- Valores ausentes codificados originalmente como `-999`. Nesta extração não há nenhum caso, mas o tratamento permanece no código.

## Decisões de Tratamento e Atributos Derivados (Camada Prata)

### SIH/SUS (Internações)
- **Filtragem:** Mantidas apenas as linhas mensais (as que começam com `..`), o que remove os totais anuais, o `Total` geral e o rodapé. Resultado: 122 meses.
- **Período:** Convertido de texto para data (primeiro dia do mês), na coluna `PERIODO`.
- **Valores zero:** O `-` do TabNet representa zero ocorrências (não é dado faltante) e foi convertido para `0`. São 76 das 1.464 células mensais (cerca de 5%), concentradas nas faixas de 10 a 19 anos.
- **Tipagem:** Colunas de contagem (faixas etárias e `Total`) convertidas para `int64`. Valores inesperados interrompem o script, em vez de virarem zero em silêncio.
- **Validação:** A soma das faixas etárias é igual à coluna `Total` em todos os 122 meses. A soma dos meses também coincide com os totais anuais e com o total geral do TabNet (13.644 internações).
- **Formato de Saída:** Dados salvos em formato Parquet (`dados/prata/sih_sus.parquet`).

### NASA POWER (Meteorologia)
- **Cabeçalho:** Linhas descritivas ignoradas até o marcador `-END HEADER-`.
- **Valores Ausentes:** O código `-999` da NASA é substituído por `NaN`.
- **Data:** `YEAR` e `DOY` convertidos para uma coluna de data (`DATA`). Resultado: 3.652 dias consecutivos, sem lacunas e sem datas repetidas.
- **Atributo Derivado (`AMPLITUDE_TERMICA`):** Calculado como a diferença diária entre temperatura máxima e mínima ($T2M\_MAX - T2M\_MIN$), essencial para responder à pergunta norteadora. O script confere que ela nunca é negativa. Nos dados atuais varia de 3,4 °C a 22,9 °C, com média de 12,3 °C.
- **Formato de Saída:** Dados salvos em formato Parquet (`dados/prata/nasa_power.parquet`).

## Junção (Enriquecimento na Camada Prata)
Clima diário juntado às internações mensais por `MES = PERIODO`, com `how="left"` e `validate="many_to_one"`. O script `src/enriquecer.py` usa as funções de `src/juncao.py` (`conferir_chaves`, `juntar` e `validar`) e salva o resultado em `dados/prata/clima_internacoes.parquet`.

- **Chave:** `MES` foi criada na NASA a partir de `DATA` (primeiro dia do mês), no mesmo formato de `PERIODO` do SIH/SUS. Os nomes são diferentes, mas o conteúdo é o mesmo.
- **Grão:** NASA = 1 linha por dia; SIH/SUS = 1 linha por mês; resultado = 1 linha por dia. As colunas de internações se repetem em cada dia do mês. **Não somar essas colunas diretamente no resultado:** a soma de `Total` daria 414.277 em vez de 13.599. O resumo por mês fica para a camada Ouro (etapa de modelagem).

### Conferência das chaves (antes da junção, em meses)
- Só na NASA: 0
- Só no SIH/SUS: 2 (2009-11 e 2009-12)
- Nos dois: 120

### Contagem
- Linhas na NASA (esquerda): 3.652
- Linhas no resultado: 3.652
- Dias sem par no SIH/SUS: 0

### Quem não casou
- **2 meses do SIH/SUS (nov/2009 e dez/2009, com 5 e 40 internações, total de 45)** não têm clima correspondente, porque a série da NASA começa em 01/01/2010. Esses meses vieram na extração do TabNet mesmo com o filtro de 2010 a 2019. É um caso de universos diferentes: não há o que consertar. Como o SIH/SUS está à direita na junção `left`, esses meses ficam fora do resultado. Eles estão registrados aqui e no `proveniencia.jsonl` para não sumirem sem aviso.

### Atributo que só existe depois da junção (pendente)
Nenhum atributo foi criado nesta etapa. No grão diário, qualquer conta que misture o clima do dia com as internações do mês inventaria um valor por dia. Por exemplo, dividir o total do mês pelos dias supõe que as internações se distribuem igualmente, o que tornaria igual a internação de um dia de amplitude de 7 °C e de um dia de 20 °C. Como a pergunta norteadora é mensal, atributos que combinem as duas fontes serão criados na Ouro, depois do resumo por mês.

## Rastreabilidade
Cada etapa registra o que fez em arquivos `proveniencia.jsonl` (modo de acréscimo, que preserva o histórico):
- **Bronze:** fonte, URL, arquivo de origem e data de extração.
- **Prata:** arquivo de origem, número de linhas antes e depois e a lista de decisões de tratamento.

## Próximos Passos (Camada Ouro)
A camada Ouro ainda não foi implementada. Está prevista:
- Agregar o clima diário por mês (por exemplo, média da temperatura e amplitude média e máxima do mês).
- Partir da tabela enriquecida `clima_internacoes.parquet` (120 meses, de 2010 a 2019), já com clima e internações lado a lado.
- Decidir se a análise usa o total de internações ou as faixas etárias.
- Comparar o efeito da amplitude térmica com o da temperatura média sobre as internações.
