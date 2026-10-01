# Impacto da Amplitude Térmica e Temperaturas Médias nas Internações por Doenças Respiratórias em Itajubá, MG

## Identificação
- **Aluno:** Enzo Kozonoe
- **Matrícula:** 2022010384

## Pergunta Norteadora
A amplitude térmica extrema (a diferença acentuada entre os dias mais quentes e as noites mais frias de um mesmo mês) tem um impacto mais forte no aumento das internações do que a queda na temperatura média isolada?

## Fontes de Dados
| Fonte | Formato | Acesso | Chave de Ligação | Link |
|---|---|---|---|---|
| SIH/SUS (TabNet / DataSUS) | CSV | Baixado | Mês/Ano e Município | http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nimg.def |
| NASA POWER | CSV | Baixado / API | Data (Dia/Mês/Ano) e Coordenadas | https://power.larc.nasa.gov/ |

## Defeitos Conhecidos das Fontes (Diagnóstico Bronze)

### SIH/SUS (Internações)
- Linhas de cabeçalho e rodapé do TabNet presentes no CSV.
- Formato da coluna de tempo em texto (ex: "Jan/2010", "Fev/2010").
- Coluna de número de internações importada como texto devido à formatação regional e valores ausentes.

### NASA POWER (Meteorologia)
- Cabeçalho descritivo da NASA nas primeiras linhas antes dos dados reais.
- Data dividida em colunas separadas (`YEAR` para Ano e `DOY` para Dia do Ano, ou `YEAR`, `MO`, `DY`).
- Valores ausentes codificados originalmente como `-999`.

## Decisões de Tratamento e Atributos Derivados (Camada Prata)

### SIH/SUS (Internações)
- **Filtragem:** Removidas linhas de cabeçalho, notas de rodapé e totais gerados pelo TabNet.
- **Tipagem:** Colunas de contagem de internações convertidas para o tipo numérico `int64`.
- **Formato de Saída:** Dados salvos em formato Parquet (`dados/prata/sih_sus.parquet`).

### NASA POWER (Meteorologia)
- **Valores Ausentes:** O código `-999` da NASA foi substituído por `NaN`.
- **Atributo Derivado (`AMPLITUDE_TERMICA`):** Calculado como a diferença diária entre temperatura máxima e mínima ($T2M\_MAX - T2M\_MIN$), essencial para responder à pergunta norteadora.
- **Formato de Saída:** Dados salvos em formato Parquet (`dados/prata/nasa_power.parquet`).