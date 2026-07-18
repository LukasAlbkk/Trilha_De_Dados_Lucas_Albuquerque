-- Sprint 2 - Consultas SQL sobre database/ecommerce.db
-- Cada bloco e identificado por um marcador "-- @nome: <slug>" usado pelo
-- script scripts/run_sql_queries.py para executar e exportar o resultado.

-- @nome: faturamento_por_categoria
-- Faturamento total, ticket medio e ranking por categoria de produto.
SELECT
    p.Categoria_Produto,
    COUNT(*) AS qtd_vendas,
    ROUND(SUM(v.Faturamento), 2) AS faturamento_total,
    ROUND(AVG(v.Faturamento), 2) AS ticket_medio,
    RANK() OVER (ORDER BY SUM(v.Faturamento) DESC) AS ranking_faturamento
FROM vendas v
JOIN produtos p ON v.ID_Produto = p.ID_Produto
GROUP BY p.Categoria_Produto
ORDER BY faturamento_total DESC;

-- @nome: top_clientes
-- Top 10 clientes por faturamento, com participacao percentual no total.
WITH faturamento_cliente AS (
    SELECT
        ID_Cliente,
        ROUND(SUM(Faturamento), 2) AS faturamento_total,
        COUNT(*) AS qtd_pedidos
    FROM vendas
    GROUP BY ID_Cliente
)
SELECT
    ID_Cliente,
    faturamento_total,
    qtd_pedidos,
    ROUND(100.0 * faturamento_total / SUM(faturamento_total) OVER (), 2) AS pct_do_faturamento_total,
    RANK() OVER (ORDER BY faturamento_total DESC) AS ranking
FROM faturamento_cliente
ORDER BY faturamento_total DESC
LIMIT 10;

-- @nome: faturamento_mensal
-- Faturamento mes a mes, variacao percentual e media movel de 3 meses.
WITH faturamento_mensal AS (
    SELECT
        strftime('%Y-%m', Data_Venda) AS mes,
        ROUND(SUM(Faturamento), 2) AS faturamento
    FROM vendas
    GROUP BY mes
)
SELECT
    mes,
    faturamento,
    ROUND(faturamento - LAG(faturamento) OVER (ORDER BY mes), 2) AS variacao_absoluta,
    ROUND(
        100.0 * (faturamento - LAG(faturamento) OVER (ORDER BY mes))
        / LAG(faturamento) OVER (ORDER BY mes), 2
    ) AS variacao_pct,
    ROUND(AVG(faturamento) OVER (
        ORDER BY mes ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS media_movel_3m
FROM faturamento_mensal
ORDER BY mes;

-- @nome: ticket_medio_por_estado
-- Faturamento, clientes unicos e ticket medio por estado.
SELECT
    Estado,
    COUNT(DISTINCT ID_Cliente) AS clientes_unicos,
    COUNT(*) AS qtd_vendas,
    ROUND(SUM(Faturamento), 2) AS faturamento_total,
    ROUND(AVG(Faturamento), 2) AS ticket_medio
FROM vendas
GROUP BY Estado
ORDER BY faturamento_total DESC;

-- @nome: top_produtos_por_categoria
-- Os 3 produtos de maior faturamento dentro de cada categoria.
WITH vendas_produto AS (
    SELECT
        p.Categoria_Produto,
        p.Nome_Produto,
        SUM(v.Quantidade) AS qtd_total,
        ROUND(SUM(v.Faturamento), 2) AS faturamento_total,
        RANK() OVER (
            PARTITION BY p.Categoria_Produto ORDER BY SUM(v.Faturamento) DESC
        ) AS ranking_categoria
    FROM vendas v
    JOIN produtos p ON v.ID_Produto = p.ID_Produto
    GROUP BY p.Categoria_Produto, p.Nome_Produto
)
SELECT *
FROM vendas_produto
WHERE ranking_categoria <= 3
ORDER BY Categoria_Produto, ranking_categoria;

-- @nome: rfm_clientes
-- Base de Recencia, Frequencia e Valor (RFM) por cliente, com quartil de valor.
WITH base AS (
    SELECT
        ID_Cliente,
        MAX(Data_Venda) AS ultima_compra,
        COUNT(*) AS frequencia,
        ROUND(SUM(Faturamento), 2) AS valor_total
    FROM vendas
    GROUP BY ID_Cliente
)
SELECT
    ID_Cliente,
    ultima_compra,
    frequencia,
    valor_total,
    CAST(
        julianday((SELECT MAX(Data_Venda) FROM vendas)) - julianday(ultima_compra)
        AS INTEGER
    ) AS recencia_dias,
    NTILE(4) OVER (ORDER BY valor_total DESC) AS quartil_valor
FROM base
ORDER BY valor_total DESC;

-- @nome: distribuicao_status_pedido
-- Distribuicao percentual das vendas por status do pedido.
SELECT
    Status_Pedido,
    COUNT(*) AS qtd,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM vendas), 2) AS pct
FROM vendas
GROUP BY Status_Pedido
ORDER BY qtd DESC;
