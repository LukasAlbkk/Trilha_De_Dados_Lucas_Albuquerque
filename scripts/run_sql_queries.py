"""
sprint 2

Executa as consultas definidas em sql/consultas_sprint2.sql contra o banco
database/ecommerce.db e exporta cada resultado para reports/sql/.
"""

import re
import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "ecommerce.db"
SQL_PATH = BASE_DIR / "sql" / "consultas_sprint2.sql"
OUTPUT_DIR = BASE_DIR / "reports" / "sql"

MARKER = re.compile(r"^-- @nome:\s*(.+)$", re.MULTILINE)


def carregar_consultas() -> dict[str, str]:
    texto = SQL_PATH.read_text(encoding="utf-8")
    partes = MARKER.split(texto)[1:]  # descarta o cabecalho antes do 1o marcador
    return {
        partes[i].strip(): partes[i + 1].strip().rstrip(";")
        for i in range(0, len(partes), 2)
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    consultas = carregar_consultas()

    conn = sqlite3.connect(DB_PATH)
    try:
        for nome, query in consultas.items():
            df = pd.read_sql(query, conn)
            destino = OUTPUT_DIR / f"{nome}.csv"
            df.to_csv(destino, index=False)
            print(f"--- {nome} ({len(df)} linhas) ---")
            print(df.head(5).to_string(index=False))
            print(f"salvo em {destino}\n")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
