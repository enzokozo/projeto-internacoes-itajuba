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
│   └── ouro/
│       └── projeto.duckdb       # banco DuckDB: esquemas prata e ouro (gerado, fora do Git)
├── ecox14/                      # projeto dbt: constrói a camada Ouro (etapa modelagem)
│   ├── dbt_project.yml          # nome do projeto, pastas e materialização padrão (tabela)
│   ├── profiles.yml             # conexão com dados/ouro/projeto.duckdb (caminho relativo)
│   └── models/
│       ├── sources.yml          # tabelas da Prata que o dbt lê, mas não cria
│       ├── dim_mes.sql
│       ├── dim_faixa_etaria.sql
│       ├── fato_internacoes.sql
│       ├── fato_clima_mensal.sql
│       └── vw_clima_internacoes_mensal.sql
├── relatorios/                  # relatórios de qualidade (HTML) gerados pelo explorar.py
├── src/
│   ├── pipeline.py              # ponto de entrada: roda as etapas em ordem e permite retomar do meio
│   ├── config.py                # caminhos, parâmetros das fontes e configuração do log
│   ├── ingerir_sih.py           # ingestão do SIH/SUS (origem → Bronze)
│   ├── ingerir_nasa.py          # ingestão do NASA POWER (origem → Bronze)
│   ├── transformar_sih.py       # SIH/SUS: Bronze → Prata
│   ├── transformar_nasa.py      # NASA POWER: Bronze → Prata
│   ├── enriquecer.py            # junção NASA + SIH/SUS na Prata
│   ├── carga.py                 # Prata → DuckDB e conferências da camada Ouro
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
python src/pipeline.py carga            # refaz o banco, a camada Ouro (dbt) e as conferências
python src/pipeline.py modelagem        # só refaz a camada Ouro (dbt) e as conferências
python src/explorar.py                  # opcional: relatórios de qualidade da Bronze
```

Etapas, em ordem: `ingestao`, `transformacao`, `enriquecimento`, `carga` e `modelagem`. A etapa `modelagem` chama o `dbt run` dentro de `ecox14/` e, em seguida, as conferências do `carga.py`. O andamento aparece na tela e fica registrado em `pipeline.log`.

O banco `dados/ouro/projeto.duckdb` é gerado pelas etapas `carga` (esquema `prata`) e `modelagem` (esquema `ouro`) e não vai para o Git. Apagá-lo e rodar `python src/pipeline.py carga` recria tudo do zero.

Para usar o dbt sozinho, rode de dentro da pasta `ecox14/` (é lá que está o `profiles.yml`):

```
cd ecox14
dbt debug                          # confere a conexão com o banco
dbt run                            # cria as 5 tabelas/views da Ouro
dbt run --select dim_mes+          # só a dim_mes e o que depende dela
```

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
- **Grão:** NASA = 1 linha por dia; SIH/SUS = 1 linha por mês; resultado = 1 linha por dia. As colunas de internações se repetem em cada dia do mês. **Não somar essas colunas diretamente no resultado:** a soma de `Total` daria 414.277 em vez de 13.599. O resumo por mês é feito na camada Ouro (ver [Modelagem e Carga](#modelagem-e-carga-camada-ouro)).

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
Nenhum atributo foi criado nesta etapa. No grão diário, qualquer conta que misture o clima do dia com as internações do mês inventaria um valor por dia. Por exemplo, dividir o total do mês pelos dias supõe que as internações se distribuem igualmente, o que tornaria igual a internação de um dia de amplitude de 7 °C e de um dia de 20 °C. Como a pergunta norteadora é mensal, atributos que combinem as duas fontes serão criados na Ouro, a partir da view mensal `ouro.vw_clima_internacoes_mensal`.

## Modelagem e Carga (Camada Ouro)
O script `src/carga.py` (etapa `carga` do pipeline) abre o banco DuckDB `dados/ouro/projeto.duckdb` e copia a Prata para o esquema `prata` sem alterações. A camada deixa de ser uma pasta e passa a ser um esquema.

### Transformação declarativa com dbt (aula 10)
O esquema `ouro` é construído pelo dbt (etapa `modelagem`), no projeto `ecox14/`. Cada tabela é um arquivo `.sql` com um único `SELECT`; o dbt coloca o `CREATE TABLE` em volta e entrega ao DuckDB. São os mesmos `SELECT` que antes ficavam em strings dentro do `carga.py` (as funções `construir_*` continuam lá, comentadas no `main`, para comparação).

- **`source('prata', ...)`** aponta para as tabelas da Prata, que o dbt não cria (declaradas em `models/sources.yml`).
- **`ref('...')`** aponta para outro modelo e cria a dependência. A ordem de execução não é escrita em lugar nenhum: o dbt a deduz das referências.

```
prata.clima_internacoes ─────────► dim_mes ────────────┐
prata.clima_internacoes ─────────► fato_clima_mensal ──┤
prata.sih_sus  +  ref(dim_mes) ──► fato_internacoes ───┼──► vw_clima_internacoes_mensal
(valores escritos à mão) ────────► dim_faixa_etaria ───┘
```

- **Materialização:** as dimensões e fatos são tabelas (padrão do `dbt_project.yml`); `vw_clima_internacoes_mensal` é view, por `{{ config(materialized='view') }}` no topo do arquivo.
- **Conferências depois do dbt:** as consultas da tabela abaixo continuam no `carga.py`, na função `conferir_ouro()`, que o pipeline chama logo depois do `dbt run`. Assim elas conferem a Ouro que acabou de ser criada, e não a da execução anterior.
- **`profiles.yml` dentro do projeto:** com caminho relativo (`../dados/ouro/projeto.duckdb`), para funcionar em qualquer máquina que clonar o repositório. O DuckDB não tem senha, então o arquivo não guarda segredo.

### Esquema estrela

```
              dim_faixa_etaria
                     ▲
                     │ faixa
              fato_internacoes
                     │ mes
                     ▼
                  dim_mes
                     ▲
                     │ mes
             fato_clima_mensal
```

As duas fatos compartilham a mesma `dim_mes`. É isso que permite colocar clima e internações lado a lado, no mesmo grão mensal, sem repetir valor nenhum.

### Grão de cada tabela
| Tabela | Tipo | Uma linha é... | Chave | Linhas |
|---|---|---|---|---|
| `ouro.dim_mes` | dimensão | um mês com dados nas duas fontes | `mes` | 120 |
| `ouro.dim_faixa_etaria` | dimensão | uma faixa etária do TabNet | `faixa` | 12 |
| `ouro.fato_internacoes` | fato | **uma faixa etária em um mês** | `mes` + `faixa` | 1.440 |
| `ouro.fato_clima_mensal` | fato | **um mês de clima em Itajubá** | `mes` | 120 |
| `ouro.vw_clima_internacoes_mensal` | view | um mês, com clima e internações lado a lado | `mes` | 120 |

### Colunas (nomes de negócio)
- **`dim_mes`:** `mes` (data, primeiro dia do mês), `ano`, `mes_num`, `estacao` (verão = dez a fev, outono = mar a mai, inverno = jun a ago, primavera = set a nov).
- **`dim_faixa_etaria`:** `ordem` (1 a 12), `faixa` (nome igual ao do TabNet), `grupo` (`crianca` até 9 anos, `adolescente` de 10 a 19, `adulto` de 20 a 59, `idoso` a partir de 60).
- **`fato_internacoes`:** `mes`, `faixa`, `internacoes`.
- **`fato_clima_mensal`:** `mes`, `temperatura_media`, `temperatura_minima`, `temperatura_maxima`, `amplitude_media`, `amplitude_maxima`, `umidade_media`, `precipitacao_mm`, `dias`.
- **`vw_clima_internacoes_mensal`:** colunas de `dim_mes` e de `fato_clima_mensal`, mais `internacoes_total` e as internações por grupo (`internacoes_criancas`, `internacoes_adolescentes`, `internacoes_adultos`, `internacoes_idosos`).

### Decisões de modelagem
- **Duas fatos, e não uma:** clima e internações são medições diferentes. Juntá-las numa tabela só, no grão diário, foi o que fez a soma de `Total` dar 414.277 na Prata.
- **Faixas etárias em linhas (`UNPIVOT`):** o TabNet entrega uma coluna por faixa. Com uma linha por mês e faixa, a análise pode usar o total, uma faixa ou um grupo sem mudar o modelo. Isso resolve a pendência "total ou faixas etárias?". A coluna `Total` do SIH/SUS não entra na fato porque é recalculável (e a conferência abaixo prova que bate).
- **Meses da `dim_mes`:** vêm de `clima_internacoes.parquet` com `WHERE Total IS NOT NULL`. O enriquecimento já tinha resolvido quais meses existem nas duas fontes, e esse trabalho não é refeito.
- **Clima mensal:** o `GROUP BY` muda o grão de dia para mês. Temperatura, amplitude e umidade são médias (ou mínimo/máximo) do mês; a precipitação é a soma do mês.
- **`dim_faixa_etaria` escrita à mão:** a ordem e o grupo não existem na fonte. Se um nome não bater com o cabeçalho do TabNet, a conferência de órfãos acusa.
- **View, e não tabela:** a `vw_clima_internacoes_mensal` não guarda dado; refaz os joins a cada consulta e por isso nunca fica desatualizada em relação à estrela.

### O que pode ser somado
- `fato_internacoes.internacoes` pode ser somada entre faixas e entre meses.
- As colunas de `fato_clima_mensal` são médias, mínimos e máximos do mês e **não se somam** entre meses. A exceção é `precipitacao_mm`.

### Quem ficou fora
- Os 2 meses do SIH/SUS sem clima (nov/2009 e dez/2009, 45 internações) ficam fora de `fato_internacoes`. A etapa registra isso no log como aviso. Por isso a Ouro tem **13.599** internações, e não as 13.644 do TabNet (13.644 − 45 = 13.599).

### Conferências (última execução)
A etapa `modelagem` interrompe o pipeline se qualquer uma destas consultas não devolver 0 (função `conferir_ouro()` do `carga.py`, executada depois do `dbt run`).

| Conferência | Resultado |
|---|---|
| `dim_mes` com mês repetido | 0 |
| `dim_faixa_etaria` com faixa repetida | 0 |
| `fato_internacoes` com par mês-faixa repetido | 0 |
| `fato_clima_mensal` com mês repetido | 0 |
| `fato_internacoes` sem mês na dimensão | 0 |
| `fato_internacoes` sem faixa na dimensão | 0 |
| `fato_clima_mensal` sem mês na dimensão | 0 |
| Linhas faltando em `fato_internacoes` (120 meses × 12 faixas) | 0 |
| Diferença entre a fato e o `Total` do SIH/SUS nos 120 meses | 0 |

Total de internações na Ouro: **13.599**.

## Rastreabilidade
Cada etapa registra o que fez em arquivos `proveniencia.jsonl` (modo de acréscimo, que preserva o histórico):
- **Bronze:** fonte, URL, arquivo de origem e data de extração.
- **Prata:** arquivo de origem, número de linhas antes e depois e a lista de decisões de tratamento.
- **Ouro:** o `dbt run` mostra na tela cada modelo criado e grava o SQL que enviou ao banco em `ecox14/target/run/`. A etapa `modelagem` registra no `pipeline.log` os meses deixados de fora e o resultado de cada conferência.

## Próximos Passos
- Criar, a partir da view mensal, os atributos que combinam as duas fontes.
- Comparar o efeito da amplitude térmica com o da temperatura média sobre as internações.
