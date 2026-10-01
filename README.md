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