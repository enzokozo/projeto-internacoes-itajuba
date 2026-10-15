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
│   └── prata/
│       ├── sih_sus.parquet      # internações mensais tratadas
│       ├── nasa_power.parquet   # clima diário tratado
│       └── proveniencia.jsonl   # decisões de cada transformação
├── src/
│   ├── ingerir_sih.py           # ingestão do SIH/SUS (origem → Bronze)
│   ├── ingerir_nasa.py          # ingestão do NASA POWER (origem → Bronze)
│   ├── explorar.py              # relatórios de qualidade (HTML) da Bronze, salvos em relatorios/
│   ├── limpeza.py               # funções genéricas de limpeza
│   ├── transformar_sih.py       # SIH/SUS: Bronze → Prata
│   └── transformar_nasa.py      # NASA POWER: Bronze → Prata
├── requirements.txt
└── README.md
```

## Como Executar
Execute a partir da raiz do repositório:

```
pip install -r requirements.txt

python src/ingerir_sih.py
python src/ingerir_nasa.py
python src/explorar.py          # opcional: gera os relatórios de qualidade
python src/transformar_sih.py
python src/transformar_nasa.py
```

Antes da ingestão, coloque `sih_sus_raw.csv` e `nasa_raw.csv` na pasta `dados/`.

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

## Rastreabilidade
Cada etapa registra o que fez em arquivos `proveniencia.jsonl` (modo de acréscimo, que preserva o histórico):
- **Bronze:** fonte, URL, arquivo de origem e data de extração.
- **Prata:** arquivo de origem, número de linhas antes e depois e a lista de decisões de tratamento.

## Próximos Passos (Camada Ouro)
A camada Ouro ainda não foi implementada. Está prevista:
- Agregar o clima diário por mês (por exemplo, média da temperatura e amplitude média e máxima do mês).
- Cruzar com as internações por `Mês/Ano` (120 meses, de 2010 a 2019).
- Decidir se a análise usa o total de internações ou as faixas etárias.
- Comparar o efeito da amplitude térmica com o da temperatura média sobre as internações.
