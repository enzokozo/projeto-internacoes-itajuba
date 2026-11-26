# Clima e internações respiratórias em Itajubá, MG

Pipeline de dados construído ao longo da disciplina ECOX14, Tópicos Especiais em Programação I (Engenharia de Dados na Prática), da UNIFEI. Cada pasta corresponde a uma etapa vista em aula: ingestão, tratamento, carga, modelagem e apresentação.

O pipeline lê dados públicos de saúde e de clima, organiza em três camadas (Bronze, Prata e Ouro) e entrega um modelo dimensional consultado por um painel.

Pergunta norteadora: **A amplitude térmica extrema (a diferença acentuada entre os dias mais quentes e as noites mais frias de um mesmo mês) tem um impacto mais forte no aumento das internações por doenças respiratórias do que a queda na temperatura média isolada?**

As internações vêm do SIH/SUS (TabNet/DataSUS) e o clima, do NASA POWER, as duas para Itajubá/MG, de 2010 a 2019.

- **Aluno:** Enzo Kozonoe
- **Matrícula:** 2022010384

---

## Como rodar, do zero

Os comandos abaixo partem da **raiz do repositório**.

### 1. Ambiente virtual e dependências

```bash
git clone https://github.com/enzokozo/projeto-internacoes-itajuba
cd projeto-internacoes-itajuba
python -m venv .venv
```

Ative o ambiente:

```powershell
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

```bash
# Linux
source .venv/bin/activate
```

Se o PowerShell recusar o script de ativação, rode antes `Set-ExecutionPolicy -Scope Process RemoteSigned`.

Instale as dependências:

```bash
pip install -r requirements.txt
```

O ambiente precisa estar ativado durante toda a execução. A etapa de modelagem chama o comando `dbt` pelo nome, e ele só é encontrado com o ambiente ativo.

### 2. Perfil do dbt

Não há nada a configurar. O dbt procura a conexão com o banco num arquivo `profiles.yml`, e o projeto já traz esse arquivo pronto, em `ecox14/profiles.yml`.

O dbt lê primeiro o `profiles.yml` da pasta de onde é executado. Por isso o arquivo do projeto vale mesmo que você já tenha um `~/.dbt/profiles.yml`. O caminho do banco é relativo (`../dados/ouro/projeto.duckdb`), e funciona em qualquer máquina.

### 3. Arquivos de entrada

As duas fontes não têm API usada pelo projeto: os CSVs são baixados à mão nos sites e colocados na pasta `dados/`, com estes nomes:

| Arquivo | Onde baixar | Consulta |
|---|---|---|
| `dados/sih_sus_raw.csv` | [TabNet: Morbidade Hospitalar do SUS, por local de internação, Minas Gerais](http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nimg.def) | ver a tabela abaixo |
| `dados/nasa_raw.csv` | [NASA POWER](https://power.larc.nasa.gov/) | dado diário, latitude -22,4266 e longitude -45,4587, de 01/01/2010 a 31/12/2019, variáveis `T2M`, `T2M_MAX`, `T2M_MIN`, `RH2M` e `PRECTOTCORR` |

Opções usadas no formulário do TabNet:

| Campo | Opção |
|---|---|
| Linha | Ano/mês atendimento |
| Coluna | Faixa Etária 1 |
| Conteúdo | Internações |
| Períodos disponíveis | de nov/2009 a dez/2019 |
| Seleções disponíveis, Município | Itajubá |
| Seleções disponíveis, Capítulo CID-10 | X. Doenças do aparelho respiratório |
| Formato | Colunas separadas por ";" |

Num clone novo não é preciso baixar nada: os dois arquivos já estão no repositório.

As duas fontes são abertas e não pedem chave nem senha. Não há credencial neste projeto.

### 4. Execução

```bash
python src/pipeline.py              # todas as etapas
python src/pipeline.py carga        # a partir de uma etapa
```

Num clone novo, o primeiro comando constrói tudo: Bronze, Prata, banco, camada Ouro e testes.

As etapas, em ordem, são `ingestao`, `transformacao`, `enriquecimento`, `carga` e `modelagem`. Um nome inválido faz o pipeline listar as etapas válidas e sair.

A etapa `modelagem` roda `dbt run`, em seguida `dbt test`, e grava a proveniência da Ouro. Se algum teste falhar, o pipeline para ali (ver [Testes](#testes)).

O log vai para o terminal e para `pipeline.log`, na raiz. Ele serve para acompanhar a execução e não é versionado. O registro do que cada camada produziu fica nos arquivos `proveniencia.jsonl`.

O `src/explorar.py`, que gera relatórios HTML de qualidade da Bronze, fica fora do pipeline por ser opcional e lento:

```bash
python src/explorar.py
```

### 5. Testes, documentação e painel

```bash
cd ecox14
dbt test                 # os testes já rodam no pipeline; aqui, para rodar sozinho
dbt docs generate
dbt docs serve           # abre a documentação no navegador; Ctrl+C para parar
cd ..
streamlit run dashboard/painel.py
```

---

## Estrutura do projeto

```text
.
├── src/                    pipeline em Python
│   ├── pipeline.py         ponto de entrada: roda as etapas em ordem
│   ├── config.py           caminhos, parâmetros e configuração do log
│   ├── ingerir_sih.py      Bronze: copia o CSV do SIH/SUS com a data no nome
│   ├── ingerir_nasa.py     Bronze: copia o CSV do NASA POWER com a data no nome
│   ├── transformar_sih.py  Prata: sih_sus.parquet
│   ├── transformar_nasa.py Prata: nasa_power.parquet
│   ├── enriquecer.py       Prata: junta o clima diário às internações do mês
│   ├── carga.py            copia a Prata para o DuckDB e registra a proveniência da Ouro
│   ├── limpeza.py          funções de limpeza de uma tabela
│   ├── juncao.py           funções de junção entre duas tabelas
│   └── explorar.py         perfil HTML das fontes, fora do pipeline
├── ecox14/                 projeto dbt: a camada Ouro
│   ├── dbt_project.yml
│   ├── profiles.yml        conexão do dbt com o DuckDB
│   ├── models/             dim_mes, dim_faixa_etaria, fato_internacoes,
│   │   │                   fato_clima_mensal, vw_clima_internacoes_mensal
│   │   ├── sources.yml     tabelas da Prata que o dbt lê
│   │   └── schema.yml      documentação e testes das colunas
│   └── tests/              testes singulares: grão, completude, somas e coerência
├── dashboard/              painel Streamlit
│   ├── painel.py           tela
│   └── consultas.py        SQL do painel, uma função por pergunta
├── dados/
│   ├── sih_sus_raw.csv     entrada, baixada do TabNet
│   ├── nasa_raw.csv        entrada, baixada do NASA POWER
│   ├── bronze/             cópias datadas das entradas, versionadas
│   ├── prata/              gerado pelo pipeline; só proveniencia.jsonl é versionado
│   └── ouro/               gerado pelo pipeline; só proveniencia.jsonl é versionado
├── relatorios/             gerado por explorar.py, não versionado
├── pipeline.log            log do pipeline, não versionado
└── requirements.txt
```

Os arquivos `.gitkeep` mantêm as pastas de `dados/` visíveis no repositório mesmo vazias.

Todos os caminhos e parâmetros do pipeline ficam em `src/config.py`. Os caminhos são calculados a partir do próprio arquivo, então os scripts funcionam qualquer que seja a pasta de onde são chamados.

**Por que `dashboard/` fica fora de `src/`.** O que está em `src/` produz dado: lê fontes, escreve arquivos, escreve no banco. O painel só consome a camada Ouro, abre o banco em modo somente leitura e é executado por outro programa, o `streamlit`. Ele não importa nada de `src/`: `consultas.py` calcula a raiz do projeto por conta própria. Separar as pastas deixa claro que o painel é um cliente do pipeline, e não uma etapa dele.

---

## As camadas

| Camada | Onde mora | Formato | Quem escreve |
|---|---|---|---|
| Bronze | `dados/bronze/<fonte>/` | CSV com a data da extração no nome | `ingerir_*.py` |
| Prata | `dados/prata/` | Parquet | `transformar_*.py`, `enriquecer.py` |
| Ouro | `dados/ouro/projeto.duckdb`, esquema `ouro` | tabelas e uma view no DuckDB | dbt |

A Prata e a Ouro não são versionadas: o código as reconstrói a partir da Bronze. A Bronze é versionada (ver [Decisões de projeto](#decisões-de-projeto)). Os arquivos `proveniencia.jsonl` das três camadas também são versionados, assim como os `.gitkeep`.

### Bronze

Guarda o dado como a fonte entregou. Cada execução da ingestão gera um arquivo novo, com a data no nome: `internacoes_20261123.csv` e `temperaturas_nasa_20261123.csv`. Rodar duas vezes no mesmo dia sobrescreve a cópia daquele dia, com aviso no log.

**A regra é a imutabilidade.** Nenhum script altera o conteúdo de um arquivo da Bronze. As etapas seguintes sempre leem o arquivo mais recente de cada fonte.

Cada pasta de fonte tem um `proveniencia.jsonl`, com uma linha por extração: fonte, URL, arquivo gravado e momento da cópia.

### Prata

Guarda o dado limpo, tipado e com a granularidade conferida. Uma tabela por fonte, mais uma tabela enriquecida. **A regra é que toda decisão de tratamento fica registrada** em `dados/prata/proveniencia.jsonl`, com linhas antes e depois.

| Arquivo | O que o tratamento faz |
|---|---|
| `sih_sus.parquet` | Mantém só as linhas mensais (as que começam com `..`), o que remove os totais anuais, o `Total` geral e o rodapé: ficam 122 meses. Converte o período de texto (`..Janeiro/2010`) para data, na coluna `PERIODO`. Converte o `-` do TabNet em `0`: são 76 das 1.464 células mensais, concentradas de 10 a 19 anos. Tipa as contagens como inteiro; um valor inesperado interrompe o script, em vez de virar zero. Confere que a soma das faixas é igual ao `Total` nos 122 meses. |
| `nasa_power.parquet` | Ignora o cabeçalho descritivo até `-END HEADER-`. Troca o código `-999` por ausente (nesta extração não há nenhum). Monta a coluna `DATA` a partir de `YEAR` e `DOY`: são 3.652 dias consecutivos, sem lacuna nem repetição. Calcula `AMPLITUDE_TERMICA` (`T2M_MAX - T2M_MIN`), que vai de 3,4 °C a 22,9 °C, com média de 12,3 °C, e confere que nunca é negativa. |
| `clima_internacoes.parquet` | Cria a chave `MES` (primeiro dia do mês de `DATA`) e junta o clima diário às internações do mês por `MES = PERIODO`, mantendo todas as linhas do clima (`left`, `many_to_one`). O resultado tem uma linha por dia, com as internações do mês repetidas em cada dia. |

**Não some as internações em `clima_internacoes`.** Cada mês aparece cerca de 30 vezes: a soma de `Total` daria 414.277, em vez de 13.599. O resumo por mês é feito na Ouro.

**Nenhum atributo novo depois da junção, de propósito.** A tabela enriquecida está no grão do dia, e as internações, no grão do mês. Qualquer conta que misture os dois, como internações por grau de amplitude do dia, inventaria um valor diário que a fonte não tem. A comparação certa é mês com mês, e ela é feita na Ouro, depois que o `group by` leva o clima para o grão do mês.

Conferência das chaves antes da junção, em meses: 120 nos dois lados, 0 só no clima e 2 só no SIH/SUS (nov/2009 e dez/2009, com 45 internações). A série da NASA começa em 01/01/2010, então esses dois meses ficam fora do resultado. Estão registrados no `proveniencia.jsonl` para não sumirem sem aviso.

### Ouro

Guarda o modelo dimensional que responde à pergunta norteadora. Mora em `dados/ouro/projeto.duckdb`, no esquema `ouro`.

O mesmo arquivo tem um esquema `prata`, com uma cópia de cada Parquet da Prata. Quem cria essa cópia é `carga.py`. O dbt lê a partir dela.

**A regra é que a Ouro só contém SQL versionado e testado.** Toda transformação desta camada está em `ecox14/models/`, e os testes, em `ecox14/models/schema.yml` e `ecox14/tests/`.

A cada construção, a etapa `modelagem` grava uma linha em `dados/ouro/proveniencia.jsonl`, logo depois do `dbt test`. A linha registra:

- qual versão da Prata foi lida, apontando para o registro de `sih_sus.parquet` e de `clima_internacoes.parquet` em `dados/prata/proveniencia.jsonl`;
- a execução do `dbt run`: versão do dbt, `invocation_id` e status de cada modelo;
- a execução do `dbt test`: quantos testes passaram e o nome dos que não passaram, e o campo `aprovada_nos_testes`;
- o commit do código e se havia alteração não commitada em `src/` ou `ecox14/`;
- as linhas de cada modelo, o total de internações e os meses que ficaram fora.

Assim a cadeia fecha: Ouro aponta para a Prata, que aponta para a Bronze, que aponta para a fonte.

Os dois comandos do dbt são lidos de `ecox14/target/run_results.json`, que é sobrescrito a cada comando. Por isso o resultado do `dbt run` é lido antes de o `dbt test` rodar. Se o arquivo tiver vindo de outro comando, o campo fica nulo e o log avisa. A hora do dbt (`concluido_em`) está em UTC; a do pipeline (`construido_em`) está no horário local.

Uma Ouro reprovada nos testes também é registrada, com `aprovada_nos_testes: false`. Só depois do registro o pipeline para. Se o `dbt run` falhar, não há Ouro nova e nada é registrado.

As linhas de cada modelo, o total de internações e o aviso dos meses que ficaram fora também aparecem no `pipeline.log`.

---

## As fontes

| Fonte | Origem | Uma linha é | Formato na Bronze | Acesso | Link |
|---|---|---|---|---|---|
| Internações | SIH/SUS, via TabNet/DataSUS | um mês, com uma coluna por faixa etária e o `Total` | CSV separado por `;`, cópia do arquivo baixado | download manual, público | [tabnet.datasus.gov.br](http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nimg.def) |
| Clima | NASA POWER, dado diário | um dia | CSV com cabeçalho descritivo, cópia do arquivo baixado | download manual, público | [power.larc.nasa.gov](https://power.larc.nasa.gov/) |

O SIH/SUS cobre nov/2009 a dez/2019 e já vem filtrado para Itajubá/MG. O NASA POWER cobre 01/01/2010 a 31/12/2019. O período em comum é de jan/2010 a dez/2019, 120 meses.

O valor do NASA POWER é a média de uma grade de 0,5° × 0,625° (cerca de 50 × 60 km) em torno da coordenada de Itajubá, e não uma medição feita na cidade.

Defeitos encontrados nas fontes:

- **SIH/SUS.** Separador `;`, e não vírgula. Linhas que não são dado: total anual (`2010`), `Total` geral e uma linha de rodapé (`&`). Período em texto, com prefixo de pontos (`..Janeiro/2010`). Zero escrito como `-`, o que faz as colunas de contagem serem lidas como texto. A extração trouxe nov/2009 e dez/2009 mesmo com o filtro de 2010 a 2019.
- **NASA POWER.** Cabeçalho descritivo antes dos dados, até `-END HEADER-`. Data dividida em `YEAR` e `DOY` (dia do ano). Ausente codificado como `-999`.

---

## O modelo da camada Ouro

Um esquema estrela com duas fatos e duas dimensões. O dbt materializa as dimensões e as fatos como **tabelas** e a view de consulta como **view**, no esquema `ouro`.

| Modelo | Tipo | Grão | Colunas | Linhas |
|---|---|---|---|---|
| `dim_mes` | dimensão | um mês com dado nas duas fontes | `mes`, `ano`, `mes_num`, `estacao` | 120 |
| `dim_faixa_etaria` | dimensão | uma faixa etária do TabNet | `ordem`, `faixa`, `grupo` | 12 |
| `fato_internacoes` | fato | uma faixa etária em um mês | `mes`, `faixa`, `internacoes` | 1.440 |
| `fato_clima_mensal` | fato | um mês de clima | `mes`, `temperatura_media`, `temperatura_minima`, `temperatura_maxima`, `amplitude_media`, `amplitude_maxima`, `umidade_media`, `precipitacao_mm`, `dias` | 120 |
| `vw_clima_internacoes_mensal` | view de consulta | um mês | colunas de `dim_mes` e de `fato_clima_mensal`, mais `internacoes_total` e as internações por grupo | 120 |

```text
dim_faixa_etaria (1) ──────< (N) fato_internacoes (N) >────── (1) dim_mes
     faixa                         mes, faixa                       mes
                                                                     │
                                                                    (1)
                                                                     │
                                                            fato_clima_mensal
                                                                    mes
```

**`dim_mes`** é o calendário do projeto. Vem de `prata.clima_internacoes`, com `where Total is not null`: o enriquecimento já resolveu quais meses existem nas duas fontes, e esse trabalho não é refeito. A estação é definida pelo mês: verão de dezembro a fevereiro, outono de março a maio, inverno de junho a agosto e primavera de setembro a novembro.

**`dim_faixa_etaria`** é escrita à mão, porque a ordem e o grupo não existem na fonte: `crianca` até 9 anos, `adolescente` de 10 a 19, `adulto` de 20 a 59 e `idoso` a partir de 60. O nome de cada faixa precisa ser igual ao cabeçalho do TabNet; se não for, o teste `relationships` da fato acusa.

**`fato_internacoes`** vem de `prata.sih_sus`. O TabNet entrega uma coluna por faixa; o `UNPIVOT` deixa uma linha por mês e faixa, e a análise pode usar o total, uma faixa ou um grupo sem mudar o modelo. A coluna `Total` não entra, porque é recalculável, e o teste `soma_bate_total_sih` prova que bate. O `ref('dim_mes')` deixa de fora nov/2009 e dez/2009.

**`fato_clima_mensal`** vem de `prata.clima_internacoes`. O `group by` muda o grão de dia para mês: temperatura, amplitude e umidade são médias, mínimos ou máximos do mês, e a precipitação é a soma do mês.

**`vw_clima_internacoes_mensal`** junta as quatro tabelas por `mes`. É a tabela que responde à pergunta norteadora e a que o painel consulta.

**O que pode ser somado.** `fato_internacoes.internacoes` pode ser somada entre faixas e entre meses. As colunas de `fato_clima_mensal` **não se somam** entre meses; a exceção é `precipitacao_mm`.

**Quem ficou fora.** Os 2 meses do SIH/SUS sem clima (nov/2009 e dez/2009, 45 internações). Por isso a Ouro tem **13.599** internações, e não as 13.644 do TabNet.

---

## Testes

Os testes estão no dbt. Rodam sozinhos no fim da etapa `modelagem` e também podem ser rodados com `dbt test`, de dentro de `ecox14/`. Um teste é uma consulta que procura defeitos: **passa quando devolve zero linhas**.

| Teste | Onde | O que garante |
|---|---|---|
| `unique` e `not_null` em `dim_mes.mes` | `schema.yml` | cada mês aparece uma vez no calendário |
| `not_null` em `ano`, `mes_num` e `estacao` | `schema.yml` | todo mês tem ano, número e estação |
| `accepted_values` em `dim_mes.mes_num` | `schema.yml` | o número do mês vai de 1 a 12 |
| `accepted_values` em `dim_mes.estacao` | `schema.yml` | só existem as quatro estações |
| `unique` e `not_null` em `dim_faixa_etaria.ordem` e `.faixa` | `schema.yml` | cada faixa aparece uma vez, com posição própria |
| `not_null` e `accepted_values` em `dim_faixa_etaria.grupo` | `schema.yml` | só existem os quatro grupos |
| `not_null` em `fato_internacoes.mes`, `.faixa` e `.internacoes` | `schema.yml` | toda contagem tem mês, faixa e valor |
| `relationships` de `fato_internacoes.mes` para `dim_mes.mes` | `schema.yml` | nenhuma contagem aponta para um mês inexistente |
| `relationships` de `fato_internacoes.faixa` para `dim_faixa_etaria.faixa` | `schema.yml` | nenhuma contagem aponta para uma faixa inexistente |
| `unique`, `not_null` e `relationships` em `fato_clima_mensal.mes` | `schema.yml` | um resumo de clima por mês, sempre de um mês do calendário |
| `not_null` em `fato_clima_mensal.amplitude_media` | `schema.yml` | a variável da pergunta nunca fica vazia |
| `unique` e `not_null` em `vw_clima_internacoes_mensal.mes` | `schema.yml` | a view tem um mês por linha |
| `grao_fato_internacoes` | `tests/grao_fato_internacoes.sql` | não há dois registros para o mesmo par mês e faixa |
| `fato_internacoes_completa` | `tests/fato_internacoes_completa.sql` | todo mês tem as 12 faixas |
| `soma_bate_total_sih` | `tests/soma_bate_total_sih.sql` | a soma das faixas na Ouro é igual ao `Total` do TabNet, mês a mês |
| `internacoes_nao_negativas` | `tests/internacoes_nao_negativas.sql` | nenhuma contagem é negativa |
| `clima_coerente` | `tests/clima_coerente.sql` | mínima ≤ média ≤ máxima, amplitude média ≤ máxima, umidade de 0 a 100, chuva não negativa, mês com todos os dias |
| `vw_sem_mes_perdido` | `tests/vw_sem_mes_perdido.sql` | nenhum mês do calendário some da view por causa dos `join` |

São 30 testes: 24 declarados no `schema.yml` e 6 singulares. Na execução de 23/11/2026, os 30 passaram (`PASS=30`). O resultado de cada execução fica em `dados/ouro/proveniencia.jsonl`.

`vw_clima_internacoes_mensal` só tem teste de chave e o `vw_sem_mes_perdido`. A nota no topo de `schema.yml` explica por quê.

Se um teste falhar, o dbt informa quantas linhas encontrou. Para ver quais são, de dentro de `ecox14/`:

```bash
dbt test --select soma_bate_total_sih --store-failures
```

O dbt grava as linhas numa tabela do esquema `ouro_dbt_test__audit`, que pode ser consultada no banco.

Até a aula de modelagem, essas regras eram conferências em Python no `carga.py`, que só escreviam o resultado no log. Elas viraram os testes acima. O `carga.py` ficou com a cópia da Prata para o banco e com o registro da proveniência da Ouro, que guarda as linhas de cada modelo e os meses que ficaram fora.

As transformações da Bronze e da Prata têm validações dentro dos próprios scripts (soma das faixas igual ao `Total`, amplitude não negativa, datas válidas), que interrompem a execução quando falham. Não há testes automatizados separados para o código Python.

---

## A documentação

A descrição de cada tabela e coluna da Ouro está em `ecox14/models/schema.yml`, ao lado dos testes. A das tabelas da Prata está em `sources.yml`.

```bash
cd ecox14
dbt docs generate
dbt docs serve
```

O dbt gera um site com o grafo dos modelos e a descrição de cada coluna. Como a descrição fica no mesmo arquivo que o teste, ela é escrita uma vez só e muda junto com o modelo.

Para ver as linhas, e não só a estrutura, use a interface do DuckDB. Baixe o programa de linha de comando em [duckdb.org](https://duckdb.org), coloque o `duckdb.exe` na raiz do projeto (ele está no `.gitignore`) e rode:

```powershell
.\duckdb.exe -ui dados/ouro/projeto.duckdb
```

A interface abre em `localhost:4213`. Feche o painel e não rode o pipeline ao mesmo tempo: o DuckDB trava o arquivo.

---

## O painel

```bash
streamlit run dashboard/painel.py
```

Rode a partir da raiz, com o ambiente ativado e o pipeline já executado. Sem o banco, o painel mostra um aviso e para.

O que ele mostra:

- **Filtros**, na barra lateral: período (ano inicial e final) e grupo etário.
- **Quatro cartões**: internações no período, média por mês e a correlação das internações com a amplitude térmica média e com a temperatura média. Abaixo deles, uma frase diz qual das duas correlações é mais forte no recorte escolhido.
- **Gráficos de linha** com as internações e o clima, mês a mês.
- **Dois gráficos de dispersão**, um ponto por mês, colorido pela estação: amplitude × internações e temperatura média × internações.
- **Tabela por estação**, com a média de internações, temperatura e amplitude.
- **Tabela de detalhe**, mês a mês, com a fonte no rodapé.

Toda consulta está em `dashboard/consultas.py`, com filtros passados como parâmetro, nunca concatenados ao texto do SQL. As médias, somas e correlações são calculadas pelo banco. O filtro de grupo etário é aplicado na `fato_internacoes`, e não escolhendo uma coluna da view, porque nome de coluna não pode ser parâmetro.

As consultas ficam em cache por 10 minutos. Depois de rodar o pipeline de novo, espere esse tempo ou reinicie o painel para ver os dados novos.

---

## Resultado

**Resposta à pergunta norteadora: não.** As internações acompanham a temperatura média do mês, e quase nada a amplitude térmica. Mais frio, mais internação; uma amplitude maior não traz mais internação.

Correlação de Pearson entre as internações do mês e o clima do mesmo mês, nos 120 meses de 2010 a 2019. É a conta que o painel faz, com o período completo:

| Recorte | Temperatura média | Amplitude térmica média |
|---|---|---|
| Todas as idades | **−0,51** | 0,12 |
| Crianças | −0,53 | −0,04 |
| Adolescentes | −0,17 | 0,08 |
| Adultos | −0,27 | 0,14 |
| Idosos | −0,42 | 0,20 |

A pergunta compara a força das duas relações, isto é, o valor absoluto. A temperatura média vence em todos os grupos etários. A amplitude nunca passa de 0,20.

Média mensal por estação do ano:

| Estação | Internações por mês | Temperatura média (°C) | Amplitude média (°C) |
|---|---|---|---|
| Verão | 88,4 | 21,5 | 11,0 |
| Outono | 126,8 | 18,5 | 10,7 |
| Inverno | 138,7 | 15,2 | 13,3 |
| Primavera | 99,3 | 19,6 | 14,1 |

A tabela reforça a resposta. A primavera tem a maior amplitude média do ano e uma das menores médias de internação. O inverno, o mais frio, tem a maior.

Esse resultado tem os limites descritos abaixo, sobretudo o primeiro: a estação do ano move a temperatura e também outras causas de internação.

---

## Decisões de projeto

**DuckDB, e não um banco com servidor.** O banco inteiro é um arquivo, `projeto.duckdb`. Não há serviço para instalar, usuário para criar ou porta para abrir. O DuckDB lê Parquet diretamente (`read_parquet` em `carga.py`) e tem adaptador para o dbt.

**Parquet na Prata, CSV na Bronze.** A Bronze guarda o que a fonte entregou, no formato mais próximo do original. A Prata já está tipada, e o Parquet guarda o tipo de cada coluna junto com o dado.

**Bronze com data no nome, e versionada.** Uma extração nova não apaga a anterior. As duas fontes são baixadas à mão em sites com formulário, então o código não consegue buscá-las de novo sozinho. Por isso a Bronze vai para o Git: é a única forma de outra pessoa reconstruir a Prata e a Ouro a partir do mesmo dado.

**Duas fatos, e não uma.** Clima e internações são medições diferentes, em grãos diferentes. Juntá-las numa tabela só, no grão diário, foi o que fez a soma de `Total` dar 414.277 na Prata. Na Ouro, cada uma tem sua fato, e as duas compartilham a `dim_mes`.

**Faixas etárias em linhas.** Com o `UNPIVOT`, a mesma fato serve para o total, para uma faixa ou para um grupo.

**Tabelas para dimensões e fatos, view para a consulta.** A materialização padrão no `dbt_project.yml` é tabela: o resultado fica gravado e só muda quando o pipeline roda. A `vw_clima_internacoes_mensal` é view, por `{{ config(materialized='view') }}` no topo do arquivo: recalcula a junção a cada consulta e não sobra tabela derivada para manter sincronizada.

**Testes no pipeline, e não só no terminal.** A etapa `modelagem` roda `dbt test` depois do `dbt run`. Se um teste falha, o pipeline para, e a Ouro com defeito não passa adiante sem que ninguém perceba. Antes de parar, a proveniência registra a Ouro como reprovada: uma construção que falhou também é história do dado.

**O SQL do painel não fica no arquivo da tela.** O SQL que transforma dados foi para o dbt, versionado e testado. Sobra o SQL que só lê para mostrar. Ele fica em `consultas.py`, uma função por pergunta, para que a mesma consulta sirva fora do painel. `painel.py` só cuida de tela e formatação.

**O perfil do dbt fica no repositório.** Com o `profiles.yml` dentro de `ecox14/` e caminho relativo, o projeto roda num clone novo sem configuração. Não há segredo nele: o DuckDB é um arquivo local, sem usuário nem senha.

**Junção pela esquerda.** `juncao.py` usa `how="left"` e declara a relação esperada (`many_to_one`). O que não casa aparece na contagem, em vez de sumir.

**Dado agregado, e não microdado.** O SIH/SUS tem microdados por internação, mas o projeto usa só contagens por mês e faixa etária, sem nada que identifique um paciente. Dado de saúde é dado pessoal sensível na LGPD; com o agregado, a pergunta é respondida sem coletar mais do que precisa.

---

## Limitações

- **Clima regional.** O NASA POWER é a média de uma grade de cerca de 50 × 60 km, e não a temperatura medida em Itajubá.
- **Correlação não é causa.** Amplitude e temperatura variam juntas com a estação do ano, e a estação também afeta as internações por outros caminhos: vírus sazonais, umidade, ambientes fechados. O painel compara correlações simples, sem separar esse efeito.
- **Sem defasagem.** O clima de um mês é comparado com as internações do mesmo mês. Um efeito que apareça no mês seguinte não é medido.
- **Local de internação.** A consulta ao TabNet é por local de internação. Pessoas de cidades vizinhas internadas em Itajubá entram na contagem, e moradores de Itajubá internados em outra cidade ficam de fora. O clima de Itajubá pode não ser o clima de quem foi internado.
- **Contagens pequenas.** Algumas faixas têm 0, 1 ou 2 internações num mês. Correlações por grupo etário, sobretudo de adolescentes, oscilam muito com poucos casos.
- **Dois meses fora.** Nov/2009 e dez/2009 (45 internações) não entram na Ouro por falta de clima.