"""
Sprint 1 

1. Le o CSV bruto (data/raw/ecom_data.csv).
2. Trata nulos, duplicados e inconsistencias.
3. Padroniza formatos de data e moeda.
4. Modela em tabelas relacionais (clientes, produtos, vendas) e carrega
   em um banco SQLite (database/ecommerce.db).
"""

import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_PATH = BASE_DIR / "data" / "raw" / "ecom_data.csv"
PROCESSED_PATH = BASE_DIR / "data" / "processed" / "ecom_data_tratado.csv"
DB_PATH = BASE_DIR / "database" / "ecommerce.db"

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y"]


def parse_data_venda(valor: str):
    for fmt in DATE_FORMATS:
        try:
            return pd.to_datetime(valor, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.NaT


def parse_valor_unitario(valor: str) -> float:
    """Converte 'R$ 1.234,56' ou '1234.56' para float 1234.56."""
    if pd.isna(valor):
        return np.nan
    texto = str(valor).strip()
    if texto.startswith("R$"):
        texto = texto.replace("R$", "").strip()
        texto = texto.replace(".", "").replace(",", ".")
    return float(texto)


def parse_localidade(valor: str):
    """Extrai (cidade, estado, pais) de formatos 'Cidade/UF/Brasil' ou 'CIDADE - UF'."""
    if pd.isna(valor):
        return pd.Series([np.nan, np.nan, np.nan])
    texto = str(valor).strip()
    if "/" in texto:
        partes = texto.split("/")
        cidade, estado = partes[0], partes[1]
        pais = partes[2] if len(partes) > 2 else "Brasil"
    elif "-" in texto:
        partes = [p.strip() for p in texto.split("-")]
        cidade, estado = partes[0], partes[1]
        pais = "Brasil"
    else:
        cidade, estado, pais = texto, np.nan, "Brasil"
    return pd.Series([cidade.strip().title(), estado.strip().upper(), pais.strip().title()])


def extract(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. Duplicados: remove linhas 100% repetidas e, entre transacoes com
    # mesmo ID_Transacao, mantem a primeira ocorrencia.
    df = df.drop_duplicates()
    df = df.drop_duplicates(subset="ID_Transacao", keep="first")

    # 2. Nulos em colunas criticas (sem ID_Cliente nao da pra atribuir a
    # venda a um cliente) -> descarta. Quantidade nula -> imputa mediana.
    df = df.dropna(subset=["ID_Cliente", "ID_Transacao"])
    df["Quantidade"] = df["Quantidade"].fillna(df["Quantidade"].median())
    df["Quantidade"] = df["Quantidade"].astype(int)
    df["Metodo_Pagamento"] = df["Metodo_Pagamento"].fillna("Nao Informado")

    # 3. Padronizacao de formatos
    df["Data_Venda"] = df["Data_Venda"].apply(parse_data_venda)
    df["Valor_Unitario"] = df["Valor_Unitario"].apply(parse_valor_unitario)
    df["Categoria_Produto"] = df["Categoria_Produto"].str.strip().str.title()
    df["Metodo_Pagamento"] = df["Metodo_Pagamento"].str.strip().str.title()
    df["Status_Pedido"] = df["Status_Pedido"].str.strip().str.title()
    df["Nome_Produto"] = df["Nome_Produto"].str.strip()

    localidade = df["Localidade_Venda"].apply(parse_localidade)
    localidade.columns = ["Cidade", "Estado", "Pais"]
    df = pd.concat([df.drop(columns=["Localidade_Venda"]), localidade], axis=1)

    # linhas onde a data nao pode ser interpretada sao descartadas
    df = df.dropna(subset=["Data_Venda"])

    df["Faturamento"] = (df["Valor_Unitario"] * df["Quantidade"]).round(2)

    return df.reset_index(drop=True)


def build_relational_tables(df: pd.DataFrame):
    clientes = (
        df[["ID_Cliente"]]
        .drop_duplicates()
        .sort_values("ID_Cliente")
        .reset_index(drop=True)
    )

    produtos = (
        df[["Nome_Produto", "Categoria_Produto"]]
        .drop_duplicates()
        .sort_values(["Categoria_Produto", "Nome_Produto"])
        .reset_index(drop=True)
    )
    produtos.insert(0, "ID_Produto", [f"PRD{i:04d}" for i in range(1, len(produtos) + 1)])

    vendas = df.merge(produtos, on=["Nome_Produto", "Categoria_Produto"], how="left")
    vendas = vendas[[
        "ID_Transacao", "ID_Cliente", "ID_Produto", "Data_Venda", "Valor_Unitario",
        "Quantidade", "Faturamento", "Cidade", "Estado", "Pais",
        "Metodo_Pagamento", "Status_Pedido",
    ]]

    return clientes, produtos, vendas


def load(clientes: pd.DataFrame, produtos: pd.DataFrame, vendas: pd.DataFrame, df_tratado: pd.DataFrame):
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_tratado.to_csv(PROCESSED_PATH, index=False)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        clientes.to_sql("clientes", conn, if_exists="replace", index=False)
        produtos.to_sql("produtos", conn, if_exists="replace", index=False)
        vendas.to_sql("vendas", conn, if_exists="replace", index=False)

        cur = conn.cursor()
        cur.execute("CREATE INDEX IF NOT EXISTS idx_vendas_cliente ON vendas(ID_Cliente)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_vendas_produto ON vendas(ID_Produto)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_vendas_data ON vendas(Data_Venda)")
        conn.commit()
    finally:
        conn.close()


def main():
    df_raw = extract(RAW_PATH)
    linhas_brutas = len(df_raw)

    df_tratado = transform(df_raw)
    clientes, produtos, vendas = build_relational_tables(df_tratado)

    load(clientes, produtos, vendas, df_tratado)

    print("=== ETL concluido ===")
    print(f"Linhas brutas:        {linhas_brutas}")
    print(f"Linhas apos limpeza:  {len(df_tratado)}")
    print(f"Clientes unicos:      {len(clientes)}")
    print(f"Produtos unicos:      {len(produtos)}")
    print(f"Registros de venda:   {len(vendas)}")
    print(f"CSV tratado salvo em: {PROCESSED_PATH}")
    print(f"Banco SQLite salvo em: {DB_PATH}")


if __name__ == "__main__":
    main()
