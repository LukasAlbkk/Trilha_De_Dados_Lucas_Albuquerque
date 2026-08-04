# InsightFlow - Desafio Data Analytics

Ciclo completo de analise de dados (end-to-end) sobre um dataset simulado de
e-commerce: ingestao e tratamento (ETL), analise exploratoria com SQL,
dashboard interativo e um modelo preditivo simples de faturamento.


## Perguntas de negocio

- Qual o perfil de consumo e segmentacao dos clientes (RFM)?
- Quais produtos ou categorias possuem maior faturamento e potencial de lucro?
- E possivel prever o faturamento para o proximo mes?

## Como executar

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Ordem de execucao (cada etapa gera os artefatos usados pela seguinte):

```bash
# Sprint 1 - gera o CSV bruto simulado e roda o ETL (cria database/ecommerce.db)
python scripts/generate_data.py
python scripts/etl.py

# Sprint 2 - estatisticas descritivas, correlacao, outliers e consultas SQL
python scripts/eda.py
python scripts/run_sql_queries.py

# Sprint 3 - dashboard interativo
streamlit run dashboard/app.py

# Sprint 4 - modelo preditivo de faturamento
python scripts/modelo_preditivo.py
```

Os notebooks (`notebooks/`) reproduzem as Sprints 2 e 4 de forma interativa,
com graficos e comentarios de leitura; podem ser abertos com
`jupyter notebook` ou reexecutados via
`jupyter nbconvert --to notebook --execute --inplace <arquivo>.ipynb`.

O `database/ecommerce.db` e o `data/raw/ecom_data.csv` ja estao versionados
no repositorio, entao os passos de execucao acima sao opcionais para apenas
explorar os resultados prontos.

## Metodologia por sprint

### Sprint 1 - Ingestao e ETL (`scripts/generate_data.py`, `scripts/etl.py`)

- Geracao de um dataset simulado de e-commerce com 6.120 linhas e sujeira
  proposital (nulos, duplicados, formatos inconsistentes de data/moeda/texto).
- Tratamento: remocao de duplicados, imputacao/descarte de nulos conforme
  criticidade, padronizacao de datas (3 formatos) e moeda
  (`R$ 1.234,56` / `1234.56`), parsing de localidade
  (`Cidade/UF/Brasil` / `CIDADE - UF`).
- Modelagem relacional (`clientes`, `produtos`, `vendas`) carregada em
  SQLite (`database/ecommerce.db`), com indices em `ID_Cliente`,
  `ID_Produto` e `Data_Venda`.
- Resultado: 5.874 linhas tratadas (~4% removidas por nulos criticos e
  duplicados).

### Sprint 2 - EDA e SQL (`scripts/eda.py`, `scripts/run_sql_queries.py`, `sql/consultas_sprint2.sql`, `notebooks/02_eda_sql.ipynb`)

- Estatisticas descritivas (numericas e categoricas).
- Deteccao de outliers pelo metodo IQR e matriz de correlacao entre
  `Valor_Unitario`, `Quantidade` e `Faturamento`.
- 7 consultas SQL com Joins, `GROUP BY` e Window Functions (`RANK`, `LAG`,
  `NTILE`, medias moveis): faturamento por categoria, top clientes,
  faturamento mensal, ticket medio por estado, top produtos por categoria,
  base RFM por cliente e distribuicao de status de pedido.

### Sprint 3 - Dashboard (`dashboard/app.py`)

- Dashboard interativo em Streamlit com KPIs (Faturamento Total, Ticket
  Medio, Total de Pedidos, Clientes Unicos, Churn Rate, Taxa de Retencao),
  serie temporal de faturamento (granularidade diaria/semanal/mensal) e
  filtros dinamicos (periodo, categoria, estado, status do pedido, metodo de
  pagamento).

### Sprint 4 - Storytelling e Modelo Preditivo (`scripts/modelo_preditivo.py`, `notebooks/03_storytelling_modelo_preditivo.ipynb`)

- Modelo de regressao linear sobre o faturamento diario, com split
  cronologico (30 dias de holdout), avaliado contra um baseline de media
  historica (MAE, RMSE, MAPE, R²), usado para estimar o faturamento do
  proximo mes.
- Notebook de storytelling consolidando os achados das 4 sprints em uma
  narrativa unica, com recomendacoes de negocio.

## Principais resultados

- **ETL**: 6.120 linhas brutas -> 5.874 tratadas; 1.192 clientes e 25
  produtos unicos identificados.
- **Receita bem distribuida**: nenhuma categoria, estado ou cliente
  concentra risco de faturamento (o maior cliente responde por <0,3% da
  receita total).
- **Ponto de atencao**: ~40% dos pedidos sao cancelados ou devolvidos - a
  maior oportunidade de melhoria identificada no projeto.
- **Modelo preditivo**: com os dados simulados (sem sazonalidade real
  embutida), a regressao linear fica proxima de um baseline de media
  historica (R² ~ 0) — resultado honesto que evidencia a ausencia de padrao
  sazonal capturavel nesta base, mas com o pipeline de avaliacao pronto para
  reuso sobre dados reais.

Detalhes completos, graficos e leitura de cada resultado estao nos notebooks
em `notebooks/` e nos CSVs/PNGs gerados em `reports/`.

## Estrutura do repositorio

```
├── data/
│   ├── raw/ecom_data.csv              # dataset simulado bruto (Sprint 1)
│   └── processed/ecom_data_tratado.csv # dataset tratado (Sprint 1)
├── database/ecommerce.db              # banco relacional SQLite
├── scripts/
│   ├── generate_data.py               # geracao do dataset simulado
│   ├── etl.py                         # ETL (Sprint 1)
│   ├── eda.py                         # estatisticas, correlacao, outliers (Sprint 2)
│   ├── run_sql_queries.py             # executa sql/consultas_sprint2.sql (Sprint 2)
│   └── modelo_preditivo.py            # regressao linear (Sprint 4)
├── sql/consultas_sprint2.sql          # consultas SQL (Joins, Window Functions, Group By)
├── notebooks/
│   ├── 02_eda_sql.ipynb               # EDA + SQL interativo (Sprint 2)
│   └── 03_storytelling_modelo_preditivo.ipynb  # storytelling + modelo (Sprint 4)
├── dashboard/app.py                   # dashboard Streamlit (Sprint 3)
├── reports/                           # saidas geradas pelos scripts (CSVs, PNGs)
├── requirements.txt
└── Desafio Dados PD (1).pdf           # enunciado do desafio
```

## Tecnologias

Python, Pandas, NumPy, SQLite, Matplotlib/Seaborn, Plotly, Streamlit,
scikit-learn, Jupyter.
