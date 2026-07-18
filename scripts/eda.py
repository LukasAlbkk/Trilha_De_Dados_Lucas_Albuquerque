"""
sprint 2

1. Extrai estatisticas descritivas do conjunto de dados tratado (Sprint 1).
2. Calcula a matriz de correlacao entre as variaveis numericas.
3. Identifica outliers (metodo IQR) em Valor_Unitario, Quantidade e Faturamento.

Le direto do banco relacional (database/ecommerce.db) e salva os
resultados em reports/.
"""

import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "ecommerce.db"
REPORTS_DIR = BASE_DIR / "reports"

NUMERIC_COLS = ["Valor_Unitario", "Quantidade", "Faturamento"]
CATEGORICAL_COLS = ["Categoria_Produto", "Metodo_Pagamento", "Status_Pedido", "Estado"]


def load_vendas(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT v.*, p.Nome_Produto, p.Categoria_Produto
        FROM vendas v
        JOIN produtos p ON v.ID_Produto = p.ID_Produto
        """,
        conn,
        parse_dates=["Data_Venda"],
    )


def estatisticas_descritivas(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    numericas = df[NUMERIC_COLS].describe().round(2)
    categoricas = df[CATEGORICAL_COLS].describe()
    return numericas, categoricas


def matriz_correlacao(df: pd.DataFrame) -> pd.DataFrame:
    return df[NUMERIC_COLS].corr().round(3)


def detectar_outliers_iqr(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    q1, q3 = df[coluna].quantile([0.25, 0.75])
    iqr = q3 - q1
    limite_inferior = q1 - 1.5 * iqr
    limite_superior = q3 + 1.5 * iqr
    return df[(df[coluna] < limite_inferior) | (df[coluna] > limite_superior)]


def plot_correlacao(corr: pd.DataFrame, destino: Path):
    # import local: mantem o backend "Agg" isolado do modo script, sem
    # interferir num backend interativo (ex.: %matplotlib inline em notebook)
    # caso este modulo seja apenas importado para reuso das funcoes de dados.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    plt.figure(figsize=(5, 4))
    sns.heatmap(corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1)
    plt.title("Correlacao entre variaveis numericas")
    plt.tight_layout()
    plt.savefig(destino, dpi=150)
    plt.close()


def plot_boxplots(df: pd.DataFrame, destino: Path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    fig, axes = plt.subplots(1, len(NUMERIC_COLS), figsize=(12, 4))
    for ax, col in zip(axes, NUMERIC_COLS):
        sns.boxplot(y=df[col], ax=ax)
        ax.set_title(col)
    plt.tight_layout()
    plt.savefig(destino, dpi=150)
    plt.close()


def main():
    REPORTS_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        df = load_vendas(conn)
    finally:
        conn.close()

    numericas, categoricas = estatisticas_descritivas(df)
    corr = matriz_correlacao(df)

    plot_correlacao(corr, REPORTS_DIR / "correlacao_heatmap.png")
    plot_boxplots(df, REPORTS_DIR / "outliers_boxplot.png")

    resumo, detalhe = [], []
    for col in NUMERIC_COLS:
        outliers = detectar_outliers_iqr(df, col)
        resumo.append(
            {
                "coluna": col,
                "qtd_outliers": len(outliers),
                "pct_outliers": round(100 * len(outliers) / len(df), 2),
            }
        )
        detalhe.append(outliers.assign(coluna_outlier=col))

    resumo_outliers = pd.DataFrame(resumo)
    outliers_detalhe = pd.concat(detalhe).drop_duplicates(subset=["ID_Transacao", "coluna_outlier"])

    numericas.to_csv(REPORTS_DIR / "estatisticas_numericas.csv")
    categoricas.to_csv(REPORTS_DIR / "estatisticas_categoricas.csv")
    corr.to_csv(REPORTS_DIR / "correlacao.csv")
    resumo_outliers.to_csv(REPORTS_DIR / "outliers_resumo.csv", index=False)
    outliers_detalhe.to_csv(REPORTS_DIR / "outliers_detalhe.csv", index=False)

    print("=== EDA concluida ===")
    print("\nEstatisticas numericas:")
    print(numericas)
    print("\nCorrelacao:")
    print(corr)
    print("\nOutliers (IQR):")
    print(resumo_outliers.to_string(index=False))
    print(f"\nRelatorios salvos em: {REPORTS_DIR}")


if __name__ == "__main__":
    main()
